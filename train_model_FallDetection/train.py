import argparse
import json
from pathlib import Path

import numpy as np

ADL_FOLDER = "ADL"
FALLS_FOLDER = "FALLS"
EPS = 1e-8


def parse_args():
    script_dir = Path(__file__).resolve().parent
    default_dataset = script_dir / "archive" / "MobiFall_Dataset_v2.0"
    parser = argparse.ArgumentParser(
        description="Train a fall detection model on MobiFall using a robust numpy pipeline."
    )
    parser.add_argument("--dataset-path", type=str, default=str(default_dataset))
    parser.add_argument("--time-steps", type=int, default=150)
    parser.add_argument("--step", type=int, default=75)
    parser.add_argument("--use-gyro", action="store_true", default=True)
    parser.add_argument("--no-gyro", dest="use_gyro", action="store_false")
    parser.add_argument("--split-mode", choices=["subject", "sample"], default="subject")
    parser.add_argument("--val-ratio", type=float, default=0.2)
    parser.add_argument("--test-ratio", type=float, default=0.2)
    parser.add_argument("--max-windows-per-trial", type=int, default=0)
    parser.add_argument("--downsample-majority-ratio", type=float, default=2.0)
    parser.add_argument("--epochs", type=int, default=250)
    parser.add_argument("--batch-size", type=int, default=256)
    parser.add_argument("--lr", type=float, default=0.01)
    parser.add_argument("--l2", type=float, default=1e-4)
    parser.add_argument("--patience", type=int, default=35)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--model-out", type=str, default=str(script_dir / "fall_detector_model.npz"))
    parser.add_argument("--report-out", type=str, default=str(script_dir / "training_report.json"))
    return parser.parse_args()


def read_sensor_file(file_path: Path):
    rows = []
    data_started = False
    try:
        with file_path.open("r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                s = line.strip()
                if not s:
                    continue
                if not data_started:
                    if s.upper() == "@DATA":
                        data_started = True
                    continue
                parts = [p.strip() for p in s.split(",")]
                if len(parts) < 4:
                    continue
                try:
                    rows.append([float(parts[1]), float(parts[2]), float(parts[3])])
                except ValueError:
                    continue
    except OSError:
        return np.empty((0, 3), dtype=np.float32)
    if not rows:
        return np.empty((0, 3), dtype=np.float32)
    return np.asarray(rows, dtype=np.float32)


def series_features(series):
    diff = np.diff(series)
    q25, q75 = np.percentile(series, [25, 75])
    return [
        float(np.mean(series)),
        float(np.std(series)),
        float(np.min(series)),
        float(np.max(series)),
        float(np.max(series) - np.min(series)),
        float(np.median(series)),
        float(q25),
        float(q75),
        float(np.mean(np.abs(series))),
        float(np.sqrt(np.mean(series * series))),
        float(np.mean(np.abs(diff))) if diff.size else 0.0,
        float(np.std(diff)) if diff.size else 0.0,
    ]


def extract_features(window):
    feats = []
    for c in range(window.shape[1]):
        feats.extend(series_features(window[:, c]))
    if window.shape[1] >= 3:
        acc_mag = np.linalg.norm(window[:, :3], axis=1)
        feats.extend(series_features(acc_mag))
    if window.shape[1] >= 6:
        gyro_mag = np.linalg.norm(window[:, 3:6], axis=1)
        feats.extend(series_features(gyro_mag))
    return np.asarray(feats, dtype=np.float32)


def iter_subject_dirs(dataset_path: Path):
    subject_dirs = []
    for d in dataset_path.iterdir():
        if d.is_dir() and d.name.startswith("sub"):
            subject_dirs.append(d)
    return sorted(subject_dirs, key=lambda p: int(p.name[3:]) if p.name[3:].isdigit() else 9999)


def windows_from_signal(signal, time_steps, step):
    starts = list(range(0, signal.shape[0] - time_steps + 1, step))
    return starts


def build_dataset(dataset_path, time_steps, step, use_gyro, max_windows_per_trial, seed):
    rng = np.random.default_rng(seed)
    features = []
    labels = []
    subjects = []
    skipped = 0

    for sub_dir in iter_subject_dirs(dataset_path):
        subject_name = sub_dir.name
        label_roots = [
            (sub_dir / ADL_FOLDER, 0),
            (sub_dir / FALLS_FOLDER, 1),
        ]
        for root_dir, label in label_roots:
            if not root_dir.is_dir():
                continue
            for act_dir in sorted(root_dir.iterdir()):
                if not act_dir.is_dir():
                    continue
                for acc_path in sorted(act_dir.glob("*_acc_*.txt")):
                    acc = read_sensor_file(acc_path)
                    if acc.shape[0] == 0:
                        skipped += 1
                        continue
                    signal = acc
                    if use_gyro:
                        gyro_path = Path(str(acc_path).replace("_acc_", "_gyro_"))
                        gyro = read_sensor_file(gyro_path) if gyro_path.exists() else np.empty((0, 3), dtype=np.float32)
                        if gyro.shape[0] == 0:
                            skipped += 1
                            continue
                        length = min(acc.shape[0], gyro.shape[0])
                        signal = np.concatenate([acc[:length], gyro[:length]], axis=1)
                    if signal.shape[0] < time_steps:
                        skipped += 1
                        continue
                    starts = windows_from_signal(signal, time_steps, step)
                    if max_windows_per_trial > 0 and len(starts) > max_windows_per_trial:
                        starts = sorted(rng.choice(starts, size=max_windows_per_trial, replace=False))
                    for st in starts:
                        window = signal[st : st + time_steps]
                        features.append(extract_features(window))
                        labels.append(label)
                        subjects.append(subject_name)

    if not features:
        raise RuntimeError("No valid windows were built. Check dataset path or time_steps/step values.")

    return (
        np.asarray(features, dtype=np.float32),
        np.asarray(labels, dtype=np.int64),
        np.asarray(subjects),
        skipped,
    )


def has_both_classes(y):
    classes = set(int(v) for v in y.tolist())
    return 0 in classes and 1 in classes


def stratified_sample_split(y, val_ratio, test_ratio, seed):
    rng = np.random.default_rng(seed)
    idx_all = np.arange(len(y))
    idx_val = []
    idx_test = []
    idx_train = []
    for cls in [0, 1]:
        cls_idx = idx_all[y == cls]
        rng.shuffle(cls_idx)
        n_cls = len(cls_idx)
        n_test = max(1, int(round(n_cls * test_ratio)))
        n_val = max(1, int(round(n_cls * val_ratio)))
        if n_test + n_val >= n_cls:
            n_test = max(1, n_cls // 4)
            n_val = max(1, n_cls // 4)
        test_part = cls_idx[:n_test]
        val_part = cls_idx[n_test : n_test + n_val]
        train_part = cls_idx[n_test + n_val :]
        idx_test.append(test_part)
        idx_val.append(val_part)
        idx_train.append(train_part)
    train_idx = np.concatenate(idx_train)
    val_idx = np.concatenate(idx_val)
    test_idx = np.concatenate(idx_test)
    rng.shuffle(train_idx)
    rng.shuffle(val_idx)
    rng.shuffle(test_idx)
    return train_idx, val_idx, test_idx


def subject_split(subjects, y, val_ratio, test_ratio, seed):
    rng = np.random.default_rng(seed)
    unique_subjects = sorted(set(subjects.tolist()), key=lambda x: int(x[3:]) if x[3:].isdigit() else 9999)

    subject_to_labels = {}
    for sub in unique_subjects:
        sub_labels = set(int(v) for v in y[subjects == sub].tolist())
        subject_to_labels[sub] = sub_labels
    eligible_eval_subjects = [sub for sub in unique_subjects if subject_to_labels[sub] == {0, 1}]

    if len(eligible_eval_subjects) < 3:
        return None

    rng.shuffle(eligible_eval_subjects)
    n_eligible = len(eligible_eval_subjects)
    n_test_sub = max(1, int(round(n_eligible * test_ratio)))
    n_val_sub = max(1, int(round(n_eligible * val_ratio)))
    if n_test_sub + n_val_sub >= n_eligible:
        n_test_sub = 1
        n_val_sub = 1

    test_subjects = set(eligible_eval_subjects[:n_test_sub])
    val_subjects = set(eligible_eval_subjects[n_test_sub : n_test_sub + n_val_sub])
    if not val_subjects:
        val_subjects = {eligible_eval_subjects[n_test_sub]}
    train_subjects = set(unique_subjects) - val_subjects - test_subjects

    idx_all = np.arange(len(y))
    train_idx = idx_all[np.isin(subjects, list(train_subjects))]
    val_idx = idx_all[np.isin(subjects, list(val_subjects))]
    test_idx = idx_all[np.isin(subjects, list(test_subjects))]

    if len(train_idx) == 0 or len(val_idx) == 0 or len(test_idx) == 0:
        return None
    if not has_both_classes(y[train_idx]) or not has_both_classes(y[val_idx]) or not has_both_classes(y[test_idx]):
        return None

    return {
        "train_idx": train_idx,
        "val_idx": val_idx,
        "test_idx": test_idx,
        "train_subjects": sorted(train_subjects, key=lambda x: int(x[3:]) if x[3:].isdigit() else 9999),
        "val_subjects": sorted(val_subjects, key=lambda x: int(x[3:]) if x[3:].isdigit() else 9999),
        "test_subjects": sorted(test_subjects, key=lambda x: int(x[3:]) if x[3:].isdigit() else 9999),
    }


def standardize(train_x, val_x, test_x):
    mean = np.mean(train_x, axis=0)
    std = np.std(train_x, axis=0)
    std[std < 1e-6] = 1.0
    return (train_x - mean) / std, (val_x - mean) / std, (test_x - mean) / std, mean, std


def downsample_majority(x, y, subjects, ratio, seed):
    if ratio <= 0:
        return x, y, subjects
    rng = np.random.default_rng(seed)
    pos_idx = np.where(y == 1)[0]
    neg_idx = np.where(y == 0)[0]
    if len(pos_idx) == 0 or len(neg_idx) == 0:
        return x, y, subjects

    if len(pos_idx) > len(neg_idx):
        major_idx, minor_idx = pos_idx, neg_idx
    else:
        major_idx, minor_idx = neg_idx, pos_idx

    target_major = int(round(len(minor_idx) * ratio))
    if len(major_idx) <= target_major:
        return x, y, subjects

    keep_major = rng.choice(major_idx, size=target_major, replace=False)
    keep_idx = np.concatenate([minor_idx, keep_major])
    rng.shuffle(keep_idx)
    return x[keep_idx], y[keep_idx], subjects[keep_idx]


def sigmoid(z):
    z = np.clip(z, -35.0, 35.0)
    return 1.0 / (1.0 + np.exp(-z))


def predict_proba(x, w, b):
    return sigmoid(np.dot(x, w) + b)


def class_weights(y):
    n_pos = int(np.sum(y == 1))
    n_neg = int(np.sum(y == 0))
    n_total = n_pos + n_neg
    if n_pos == 0 or n_neg == 0:
        return {0: 1.0, 1: 1.0}
    return {0: n_total / (2.0 * n_neg), 1: n_total / (2.0 * n_pos)}


def weighted_logloss(y_true, y_prob, w, l2, sample_w):
    y_prob = np.clip(y_prob, EPS, 1.0 - EPS)
    ce = -(y_true * np.log(y_prob) + (1.0 - y_true) * np.log(1.0 - y_prob))
    loss = float(np.sum(ce * sample_w) / (np.sum(sample_w) + EPS))
    loss += 0.5 * l2 * float(np.sum(w * w))
    return loss


def train_logistic(
    train_x,
    train_y,
    val_x,
    val_y,
    lr=0.01,
    l2=1e-4,
    epochs=200,
    batch_size=256,
    patience=35,
    seed=42,
):
    rng = np.random.default_rng(seed)
    n_features = train_x.shape[1]
    w = rng.normal(0.0, 0.02, size=n_features).astype(np.float32)
    b = np.float32(0.0)
    c_w = class_weights(train_y)
    train_sample_w = np.where(train_y == 1, c_w[1], c_w[0]).astype(np.float32)
    val_sample_w = np.where(val_y == 1, c_w[1], c_w[0]).astype(np.float32)

    best_val_loss = float("inf")
    best_w = w.copy()
    best_b = float(b)
    best_epoch = 0
    bad_epochs = 0
    min_lr = 1e-5
    history = []

    for epoch in range(1, epochs + 1):
        perm = rng.permutation(len(train_y))
        x_shuf = train_x[perm]
        y_shuf = train_y[perm]
        sw_shuf = train_sample_w[perm]

        for start in range(0, len(train_y), batch_size):
            end = start + batch_size
            xb = x_shuf[start:end]
            yb = y_shuf[start:end]
            wb = sw_shuf[start:end]
            p = predict_proba(xb, w, b)
            err = (p - yb) * wb
            denom = np.sum(wb) + EPS
            grad_w = np.dot(xb.T, err) / denom + l2 * w
            grad_b = float(np.sum(err) / denom)
            w -= lr * grad_w
            b -= lr * grad_b

        train_prob = predict_proba(train_x, w, b)
        val_prob = predict_proba(val_x, w, b)
        train_loss = weighted_logloss(train_y, train_prob, w, l2, train_sample_w)
        val_loss = weighted_logloss(val_y, val_prob, w, l2, val_sample_w)
        history.append({"epoch": epoch, "train_loss": train_loss, "val_loss": val_loss, "lr": lr})

        if val_loss < best_val_loss - 1e-5:
            best_val_loss = val_loss
            best_w = w.copy()
            best_b = float(b)
            best_epoch = epoch
            bad_epochs = 0
        else:
            bad_epochs += 1
            if bad_epochs > 0 and bad_epochs % 10 == 0:
                lr = max(lr * 0.5, min_lr)
            if bad_epochs >= patience:
                break

    return best_w, best_b, history, best_epoch, best_val_loss


def metrics_from_probs(y_true, y_prob, threshold):
    y_pred = (y_prob >= threshold).astype(np.int64)
    tp = int(np.sum((y_true == 1) & (y_pred == 1)))
    tn = int(np.sum((y_true == 0) & (y_pred == 0)))
    fp = int(np.sum((y_true == 0) & (y_pred == 1)))
    fn = int(np.sum((y_true == 1) & (y_pred == 0)))

    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    specificity = tn / (tn + fp) if (tn + fp) > 0 else 0.0
    f1 = (2.0 * precision * recall / (precision + recall)) if (precision + recall) > 0 else 0.0
    acc = (tp + tn) / max(1, len(y_true))
    bal_acc = 0.5 * (recall + specificity)
    return {
        "accuracy": float(acc),
        "precision": float(precision),
        "recall": float(recall),
        "specificity": float(specificity),
        "f1": float(f1),
        "balanced_accuracy": float(bal_acc),
        "tp": tp,
        "tn": tn,
        "fp": fp,
        "fn": fn,
    }


def average_precision_score(y_true, y_prob):
    y_true = y_true.astype(np.int64)
    pos_total = int(np.sum(y_true == 1))
    if pos_total == 0:
        return 0.0
    order = np.argsort(-y_prob)
    y_sorted = y_true[order]
    tp_cum = np.cumsum(y_sorted == 1)
    fp_cum = np.cumsum(y_sorted == 0)
    precision = tp_cum / np.maximum(tp_cum + fp_cum, 1)
    recall = tp_cum / pos_total

    precision = np.concatenate([[1.0], precision])
    recall = np.concatenate([[0.0], recall])
    return float(np.trapezoid(precision, recall))


def choose_best_threshold(y_true, y_prob):
    best_t = 0.5
    best_metrics = metrics_from_probs(y_true, y_prob, best_t)
    for t in np.linspace(0.05, 0.95, 91):
        m = metrics_from_probs(y_true, y_prob, float(t))
        if m["f1"] > best_metrics["f1"] + 1e-12:
            best_t = float(t)
            best_metrics = m
        elif abs(m["f1"] - best_metrics["f1"]) <= 1e-12 and m["recall"] > best_metrics["recall"]:
            best_t = float(t)
            best_metrics = m
    return best_t, best_metrics


def print_split_stats(name, y):
    count = len(y)
    pos = int(np.sum(y == 1))
    neg = int(np.sum(y == 0))
    pos_ratio = (100.0 * pos / count) if count else 0.0
    print(f"{name:<6} -> samples={count:5d}, fall={pos:5d}, adl={neg:5d}, fall_ratio={pos_ratio:6.2f}%")


def print_metrics_block(name, metrics, ap):
    print(
        f"{name:<5} | acc={metrics['accuracy']:.4f} "
        f"bal_acc={metrics['balanced_accuracy']:.4f} "
        f"precision={metrics['precision']:.4f} "
        f"recall={metrics['recall']:.4f} "
        f"f1={metrics['f1']:.4f} ap={ap:.4f}"
    )
    print(f"       confusion: TP={metrics['tp']} TN={metrics['tn']} FP={metrics['fp']} FN={metrics['fn']}")


def ensure_parent(path_str):
    path = Path(path_str)
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def main():
    args = parse_args()
    dataset_path = Path(args.dataset_path).expanduser().resolve()
    if not dataset_path.exists():
        raise SystemExit(f"Dataset path does not exist: {dataset_path}")
    if args.val_ratio <= 0 or args.test_ratio <= 0 or args.val_ratio + args.test_ratio >= 0.9:
        raise SystemExit("Use sensible ratios: val_ratio > 0, test_ratio > 0, and val+test < 0.9")

    print(f"Dataset path: {dataset_path}")
    print(f"Using sensors: {'acc+gyro' if args.use_gyro else 'acc only'}")
    print(f"Window config: time_steps={args.time_steps}, step={args.step}")
    print("Building dataset windows and extracting features...")
    x_all, y_all, subjects, skipped = build_dataset(
        dataset_path=dataset_path,
        time_steps=args.time_steps,
        step=args.step,
        use_gyro=args.use_gyro,
        max_windows_per_trial=args.max_windows_per_trial,
        seed=args.seed,
    )
    print(f"Total windows: {len(y_all)}, features: {x_all.shape[1]}, skipped trials/files: {skipped}")

    split_info = None
    if args.split_mode == "subject":
        split_info = subject_split(subjects, y_all, args.val_ratio, args.test_ratio, args.seed)
        if split_info is None:
            print("Subject split unavailable (insufficient balanced subjects). Falling back to stratified sample split.")
        else:
            print(
                f"Subject split -> train_subjects={len(split_info['train_subjects'])}, "
                f"val_subjects={len(split_info['val_subjects'])}, test_subjects={len(split_info['test_subjects'])}"
            )

    if split_info is None:
        train_idx, val_idx, test_idx = stratified_sample_split(y_all, args.val_ratio, args.test_ratio, args.seed)
        train_subjects = sorted(set(subjects[train_idx].tolist()))
        val_subjects = sorted(set(subjects[val_idx].tolist()))
        test_subjects = sorted(set(subjects[test_idx].tolist()))
        split_mode_used = "sample"
    else:
        train_idx = split_info["train_idx"]
        val_idx = split_info["val_idx"]
        test_idx = split_info["test_idx"]
        train_subjects = split_info["train_subjects"]
        val_subjects = split_info["val_subjects"]
        test_subjects = split_info["test_subjects"]
        split_mode_used = "subject"

    train_x = x_all[train_idx]
    train_y = y_all[train_idx]
    train_subject_arr = subjects[train_idx]
    val_x = x_all[val_idx]
    val_y = y_all[val_idx]
    test_x = x_all[test_idx]
    test_y = y_all[test_idx]

    if args.downsample_majority_ratio > 0:
        train_x, train_y, train_subject_arr = downsample_majority(
            train_x, train_y, train_subject_arr, args.downsample_majority_ratio, args.seed
        )

    print_split_stats("Train", train_y)
    print_split_stats("Val", val_y)
    print_split_stats("Test", test_y)

    if not has_both_classes(train_y) or not has_both_classes(val_y) or not has_both_classes(test_y):
        raise SystemExit("Each split must contain both ADL and FALL samples. Adjust split ratios or split mode.")

    train_x, val_x, test_x, mean, std = standardize(train_x, val_x, test_x)

    print("Training weighted logistic regression with early stopping...")
    w, b, history, best_epoch, best_val_loss = train_logistic(
        train_x=train_x,
        train_y=train_y.astype(np.float32),
        val_x=val_x,
        val_y=val_y.astype(np.float32),
        lr=args.lr,
        l2=args.l2,
        epochs=args.epochs,
        batch_size=args.batch_size,
        patience=args.patience,
        seed=args.seed,
    )
    print(f"Best epoch: {best_epoch}, best val loss: {best_val_loss:.6f}")

    train_prob = predict_proba(train_x, w, b)
    val_prob = predict_proba(val_x, w, b)
    test_prob = predict_proba(test_x, w, b)

    threshold, val_best_metrics = choose_best_threshold(val_y, val_prob)
    train_metrics = metrics_from_probs(train_y, train_prob, threshold)
    val_metrics = metrics_from_probs(val_y, val_prob, threshold)
    test_metrics = metrics_from_probs(test_y, test_prob, threshold)
    train_ap = average_precision_score(train_y, train_prob)
    val_ap = average_precision_score(val_y, val_prob)
    test_ap = average_precision_score(test_y, test_prob)

    print(f"Best threshold from val F1: {threshold:.3f}")
    print_metrics_block("Train", train_metrics, train_ap)
    print_metrics_block("Val", val_metrics, val_ap)
    print_metrics_block("Test", test_metrics, test_ap)

    model_out = ensure_parent(args.model_out)
    np.savez(
        model_out,
        weights=w.astype(np.float32),
        bias=np.asarray([b], dtype=np.float32),
        mean=mean.astype(np.float32),
        std=std.astype(np.float32),
        threshold=np.asarray([threshold], dtype=np.float32),
        time_steps=np.asarray([args.time_steps], dtype=np.int32),
        step=np.asarray([args.step], dtype=np.int32),
        use_gyro=np.asarray([1 if args.use_gyro else 0], dtype=np.int8),
        feature_dim=np.asarray([train_x.shape[1]], dtype=np.int32),
    )

    report = {
        "dataset_path": str(dataset_path),
        "split_mode_requested": args.split_mode,
        "split_mode_used": split_mode_used,
        "time_steps": args.time_steps,
        "step": args.step,
        "use_gyro": bool(args.use_gyro),
        "seed": args.seed,
        "hyperparameters": {
            "epochs": args.epochs,
            "batch_size": args.batch_size,
            "lr": args.lr,
            "l2": args.l2,
            "patience": args.patience,
            "downsample_majority_ratio": args.downsample_majority_ratio,
        },
        "counts": {
            "total_windows": int(len(y_all)),
            "train_windows": int(len(train_y)),
            "val_windows": int(len(val_y)),
            "test_windows": int(len(test_y)),
        },
        "subjects": {
            "train": train_subjects,
            "val": val_subjects,
            "test": test_subjects,
        },
        "best_epoch": int(best_epoch),
        "best_val_loss": float(best_val_loss),
        "selected_threshold": float(threshold),
        "val_metrics_at_selected_threshold": val_best_metrics,
        "metrics": {
            "train": train_metrics,
            "val": val_metrics,
            "test": test_metrics,
        },
        "average_precision": {
            "train": float(train_ap),
            "val": float(val_ap),
            "test": float(test_ap),
        },
        "skipped_trials_or_files": int(skipped),
        "history": history,
    }

    report_out = ensure_parent(args.report_out)
    report_out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"Saved model: {model_out}")
    print(f"Saved report: {report_out}")


if __name__ == "__main__":
    main()
