#!/usr/bin/env python3
"""
Export a trained hybrid fall-detection model (.joblib) to C code for ESP-IDF.

Supported model structure:
  - bundle from train_hybrid_edge.py:
      {
        "stage2_model": sklearn Pipeline(preprocessor + RandomForestClassifier),
        "feature_cols": [...],
        "gate_feature": str,
        "gate_threshold": float,
        "gate_op": ">=" or "<=",
        "decision_threshold": float,
      }

Output:
  - <prefix>.h
  - <prefix>.c
  - <prefix>_feature_map.json
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Iterable, List

import joblib
import numpy as np


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Export hybrid model to C for ESP-IDF.")
    parser.add_argument(
        "--model",
        required=True,
        help="Path to hybrid_model.joblib exported by train_hybrid_edge.py",
    )
    parser.add_argument("--out-dir", default="espidf_export")
    parser.add_argument(
        "--prefix",
        default="hybrid_model",
        help="Base name for generated C/H files and symbol prefix.",
    )
    return parser.parse_args()


def sanitize_identifier(name: str) -> str:
    out = re.sub(r"[^a-zA-Z0-9_]", "_", name)
    if not out:
        out = "model"
    if out[0].isdigit():
        out = f"m_{out}"
    return out


def c_escape(s: str) -> str:
    return s.replace("\\", "\\\\").replace('"', '\\"')


def format_c_array(values: Iterable, c_type: str, per_line: int = 8, float_fmt: str = ".9g") -> str:
    chunks: List[str] = []
    line: List[str] = []
    for i, v in enumerate(values):
        if c_type == "float":
            token = format(float(v), float_fmt)
            if "e" not in token and "E" not in token and "." not in token:
                token += ".0"
            token += "f"
        else:
            token = str(int(v))
        line.append(token)
        if (i + 1) % per_line == 0:
            chunks.append(", ".join(line))
            line = []
    if line:
        chunks.append(", ".join(line))
    return ",\n    ".join(chunks) if chunks else ""


def main() -> None:
    args = parse_args()
    model_path = Path(args.model)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    prefix = sanitize_identifier(args.prefix)
    prefix_upper = prefix.upper()
    header_guard = f"{prefix_upper}_H"

    bundle = joblib.load(model_path)
    pipe = bundle["stage2_model"]
    pre = pipe.named_steps["pre"]
    rf = pipe.named_steps["clf"]

    if not hasattr(rf, "estimators_"):
        raise RuntimeError("Stage-2 model must be RandomForestClassifier with estimators_.")

    transformers = {name: (trans, cols) for name, trans, cols in pre.transformers_ if name != "remainder"}

    if "num" not in transformers:
        raise RuntimeError("Preprocessor missing 'num' transformer.")

    num_trans, num_cols = transformers["num"]
    num_cols = list(num_cols)
    num_imputer = num_trans.named_steps["imputer"]
    num_scaler = num_trans.named_steps["scaler"]
    num_median = np.asarray(num_imputer.statistics_, dtype=np.float32)
    num_mean = np.asarray(num_scaler.mean_, dtype=np.float32)
    num_scale = np.asarray(num_scaler.scale_, dtype=np.float32)

    if len(num_cols) != len(num_median):
        raise RuntimeError("Numeric column count does not match imputer/scaler statistics.")

    cat_cols: List[str] = []
    cat_categories: List[List[str]] = []
    cat_default_idx: List[int] = []
    if "cat" in transformers:
        cat_trans, cat_cols_raw = transformers["cat"]
        cat_cols = list(cat_cols_raw)
        cat_imputer = cat_trans.named_steps["imputer"]
        onehot = cat_trans.named_steps["onehot"]

        for stats_value, cats in zip(cat_imputer.statistics_, onehot.categories_):
            cat_list = [str(c) for c in cats.tolist()]
            cat_categories.append(cat_list)
            default_val = str(stats_value)
            try:
                idx = cat_list.index(default_val)
            except ValueError:
                idx = 0
            cat_default_idx.append(idx)

    cat_sizes = [len(c) for c in cat_categories]
    cat_offsets: List[int] = []
    cur_offset = len(num_cols)
    for size in cat_sizes:
        cat_offsets.append(cur_offset)
        cur_offset += size
    total_transformed_features = cur_offset

    if total_transformed_features != int(rf.n_features_in_):
        raise RuntimeError(
            f"Transformed feature count mismatch: pre={total_transformed_features}, rf={rf.n_features_in_}"
        )

    gate_feature = str(bundle["gate_feature"])
    gate_threshold = float(bundle["gate_threshold"])
    gate_op = str(bundle["gate_op"])
    decision_threshold = float(bundle["decision_threshold"])
    if gate_feature not in num_cols:
        raise RuntimeError(
            f"Gate feature '{gate_feature}' is not in numeric columns. "
            "Current exporter supports numeric gate only."
        )
    gate_num_idx = num_cols.index(gate_feature)
    gate_op_ge = 1 if gate_op == ">=" else 0

    classes = np.asarray(rf.classes_)
    pos_idx_matches = np.where(classes == 1)[0]
    if pos_idx_matches.size == 0:
        raise RuntimeError("Classifier classes do not contain label=1.")
    pos_idx = int(pos_idx_matches[0])

    tree_offsets = [0]
    children_left: List[int] = []
    children_right: List[int] = []
    feature_idx: List[int] = []
    thresholds: List[float] = []
    node_pos_prob: List[float] = []

    for est in rf.estimators_:
        tree = est.tree_
        offset = tree_offsets[-1]
        n_nodes = tree.node_count

        for i in range(n_nodes):
            left = int(tree.children_left[i])
            right = int(tree.children_right[i])
            children_left.append(-1 if left < 0 else offset + left)
            children_right.append(-1 if right < 0 else offset + right)
            feature_idx.append(int(tree.feature[i]))
            thresholds.append(float(tree.threshold[i]))

            values = tree.value[i, 0, :]
            denom = float(values.sum())
            prob = float(values[pos_idx] / denom) if denom > 0 else 0.0
            node_pos_prob.append(prob)

        tree_offsets.append(offset + n_nodes)

    total_nodes = tree_offsets[-1]
    if not (
        len(children_left)
        == len(children_right)
        == len(feature_idx)
        == len(thresholds)
        == len(node_pos_prob)
        == total_nodes
    ):
        raise RuntimeError("Internal export size mismatch for flattened tree arrays.")

    cat_label_offsets: List[int] = []
    cat_labels_flat: List[str] = []
    running = 0
    for labels in cat_categories:
        cat_label_offsets.append(running)
        cat_labels_flat.extend(labels)
        running += len(labels)

    # -------- Header --------
    h_path = out_dir / f"{prefix}.h"
    h_text = f"""#ifndef {header_guard}
#define {header_guard}

#include <stdint.h>

#define {prefix_upper}_NUM_NUMERIC_FEATURES {len(num_cols)}
#define {prefix_upper}_NUM_CATEGORICAL_FEATURES {len(cat_cols)}
#define {prefix_upper}_NUM_TRANSFORMED_FEATURES {total_transformed_features}
#define {prefix_upper}_NUM_TREES {len(tree_offsets) - 1}
#define {prefix_upper}_TOTAL_TREE_NODES {total_nodes}

#define {prefix_upper}_GATE_NUMERIC_INDEX {gate_num_idx}
#define {prefix_upper}_GATE_THRESHOLD {gate_threshold:.9g}f
#define {prefix_upper}_GATE_OP_GE {gate_op_ge}
#define {prefix_upper}_DECISION_THRESHOLD {decision_threshold:.9g}f

typedef struct {{
    float num[{prefix_upper}_NUM_NUMERIC_FEATURES];
    int32_t cat[{max(1, len(cat_cols))}];
}} {prefix}_input_t;

extern const char *{prefix}_numeric_feature_names[{len(num_cols)}];
extern const char *{prefix}_categorical_feature_names[{max(1, len(cat_cols))}];
extern const int32_t {prefix}_cat_value_counts[{max(1, len(cat_cols))}];
extern const int32_t {prefix}_cat_default_indices[{max(1, len(cat_cols))}];
extern const int32_t {prefix}_cat_label_offsets[{max(1, len(cat_cols))}];
extern const char *{prefix}_cat_labels_flat[{max(1, len(cat_labels_flat))}];

int {prefix}_gate_pass(const {prefix}_input_t *in);
float {prefix}_predict_proba_stage2(const {prefix}_input_t *in);
float {prefix}_predict_proba(const {prefix}_input_t *in);
int {prefix}_predict_label(const {prefix}_input_t *in);

#endif
"""
    h_path.write_text(h_text, encoding="utf-8")

    # -------- Source --------
    num_names_c = ",\n    ".join(f"\"{c_escape(c)}\"" for c in num_cols)
    if cat_cols:
        cat_names_c = ",\n    ".join(f"\"{c_escape(c)}\"" for c in cat_cols)
        cat_counts_c = format_c_array(cat_sizes, "int32_t", per_line=12)
        cat_defaults_c = format_c_array(cat_default_idx, "int32_t", per_line=12)
        cat_offsets_c = format_c_array(cat_label_offsets, "int32_t", per_line=12)
        cat_labels_c = ",\n    ".join(f"\"{c_escape(c)}\"" for c in cat_labels_flat)
    else:
        cat_names_c = "\"\""
        cat_counts_c = "0"
        cat_defaults_c = "0"
        cat_offsets_c = "0"
        cat_labels_c = "\"\""

    c_text = f"""#include "{prefix}.h"

#include <math.h>
#include <stddef.h>

const char *{prefix}_numeric_feature_names[{len(num_cols)}] = {{
    {num_names_c}
}};

const char *{prefix}_categorical_feature_names[{max(1, len(cat_cols))}] = {{
    {cat_names_c}
}};

const int32_t {prefix}_cat_value_counts[{max(1, len(cat_cols))}] = {{
    {cat_counts_c}
}};

const int32_t {prefix}_cat_default_indices[{max(1, len(cat_cols))}] = {{
    {cat_defaults_c}
}};

const int32_t {prefix}_cat_label_offsets[{max(1, len(cat_cols))}] = {{
    {cat_offsets_c}
}};

const char *{prefix}_cat_labels_flat[{max(1, len(cat_labels_flat))}] = {{
    {cat_labels_c}
}};

static const float k_num_median[{len(num_cols)}] = {{
    {format_c_array(num_median.tolist(), "float", per_line=8)}
}};

static const float k_num_mean[{len(num_cols)}] = {{
    {format_c_array(num_mean.tolist(), "float", per_line=8)}
}};

static const float k_num_scale[{len(num_cols)}] = {{
    {format_c_array(num_scale.tolist(), "float", per_line=8)}
}};

static const int32_t k_tree_offsets[{len(tree_offsets)}] = {{
    {format_c_array(tree_offsets, "int32_t", per_line=12)}
}};

static const int32_t k_children_left[{total_nodes}] = {{
    {format_c_array(children_left, "int32_t", per_line=12)}
}};

static const int32_t k_children_right[{total_nodes}] = {{
    {format_c_array(children_right, "int32_t", per_line=12)}
}};

static const int32_t k_feature_idx[{total_nodes}] = {{
    {format_c_array(feature_idx, "int32_t", per_line=12)}
}};

static const float k_threshold[{total_nodes}] = {{
    {format_c_array(thresholds, "float", per_line=8)}
}};

static const float k_node_pos_prob[{total_nodes}] = {{
    {format_c_array(node_pos_prob, "float", per_line=8)}
}};

static void {prefix}_transform_input(const {prefix}_input_t *in, float *out) {{
    for (int i = 0; i < {prefix_upper}_NUM_TRANSFORMED_FEATURES; ++i) {{
        out[i] = 0.0f;
    }}

    for (int i = 0; i < {prefix_upper}_NUM_NUMERIC_FEATURES; ++i) {{
        float v = in->num[i];
        if (isnan(v)) {{
            v = k_num_median[i];
        }}
        if (k_num_scale[i] == 0.0f) {{
            out[i] = 0.0f;
        }} else {{
            out[i] = (v - k_num_mean[i]) / k_num_scale[i];
        }}
    }}

    for (int ci = 0; ci < {len(cat_cols)}; ++ci) {{
        int code = (int)in->cat[ci];
        int nvals = (int){prefix}_cat_value_counts[ci];
        int default_idx = (int){prefix}_cat_default_indices[ci];
        int base = (int){prefix}_cat_label_offsets[ci] + {len(num_cols)};
        if (code < 0 || code >= nvals) {{
            code = default_idx;
        }}
        out[base + code] = 1.0f;
    }}
}}

int {prefix}_gate_pass(const {prefix}_input_t *in) {{
    float v = in->num[{prefix_upper}_GATE_NUMERIC_INDEX];
    if (isnan(v)) {{
        v = k_num_median[{prefix_upper}_GATE_NUMERIC_INDEX];
    }}
    if ({prefix_upper}_GATE_OP_GE) {{
        return v >= {prefix_upper}_GATE_THRESHOLD;
    }}
    return v <= {prefix_upper}_GATE_THRESHOLD;
}}

float {prefix}_predict_proba_stage2(const {prefix}_input_t *in) {{
    float x[{prefix_upper}_NUM_TRANSFORMED_FEATURES];
    {prefix}_transform_input(in, x);

    float sum_prob = 0.0f;
    for (int t = 0; t < {prefix_upper}_NUM_TREES; ++t) {{
        int32_t node = k_tree_offsets[t];
        while (k_children_left[node] != -1) {{
            int32_t f = k_feature_idx[node];
            float thr = k_threshold[node];
            if (x[f] <= thr) {{
                node = k_children_left[node];
            }} else {{
                node = k_children_right[node];
            }}
        }}
        sum_prob += k_node_pos_prob[node];
    }}
    return sum_prob / (float){prefix_upper}_NUM_TREES;
}}

float {prefix}_predict_proba(const {prefix}_input_t *in) {{
    if (!{prefix}_gate_pass(in)) {{
        return 0.0f;
    }}
    return {prefix}_predict_proba_stage2(in);
}}

int {prefix}_predict_label(const {prefix}_input_t *in) {{
    float p = {prefix}_predict_proba(in);
    return (p >= {prefix_upper}_DECISION_THRESHOLD) ? 1 : 0;
}}
"""
    c_path = out_dir / f"{prefix}.c"
    c_path.write_text(c_text, encoding="utf-8")

    metadata = {
        "model_path": str(model_path),
        "prefix": prefix,
        "num_numeric_features": len(num_cols),
        "numeric_feature_names": num_cols,
        "num_categorical_features": len(cat_cols),
        "categorical_feature_names": cat_cols,
        "categorical_values": cat_categories,
        "categorical_default_index": cat_default_idx,
        "gate_feature": gate_feature,
        "gate_feature_numeric_index": gate_num_idx,
        "gate_threshold": gate_threshold,
        "gate_op": gate_op,
        "decision_threshold": decision_threshold,
        "num_trees": len(tree_offsets) - 1,
        "total_tree_nodes": total_nodes,
    }
    meta_path = out_dir / f"{prefix}_feature_map.json"
    meta_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")

    print("Export complete.")
    print(f"- Header: {h_path}")
    print(f"- Source: {c_path}")
    print(f"- Metadata: {meta_path}")
    print(f"- Trees: {len(tree_offsets) - 1}, total nodes: {total_nodes}")
    print(
        f"- Input layout: {len(num_cols)} numeric + {len(cat_cols)} categorical "
        f"({sum(cat_sizes)} one-hot dims)"
    )


if __name__ == "__main__":
    main()
