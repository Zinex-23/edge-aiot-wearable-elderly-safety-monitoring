#ifndef HYBRID_S3_H
#define HYBRID_S3_H

#include <stdint.h>

#define HYBRID_S3_NUM_NUMERIC_FEATURES 81
#define HYBRID_S3_NUM_CATEGORICAL_FEATURES 1
#define HYBRID_S3_NUM_TRANSFORMED_FEATURES 83
#define HYBRID_S3_NUM_TREES 40
#define HYBRID_S3_TOTAL_TREE_NODES 22242

#define HYBRID_S3_GATE_NUMERIC_INDEX 10
#define HYBRID_S3_GATE_THRESHOLD 0.0278328691f
#define HYBRID_S3_GATE_OP_GE 1
#define HYBRID_S3_DECISION_THRESHOLD 0.495f

typedef struct {
    float num[HYBRID_S3_NUM_NUMERIC_FEATURES];
    int32_t cat[1];
} hybrid_s3_input_t;

extern const char *hybrid_s3_numeric_feature_names[81];
extern const char *hybrid_s3_categorical_feature_names[1];
extern const int32_t hybrid_s3_cat_value_counts[1];
extern const int32_t hybrid_s3_cat_default_indices[1];
extern const int32_t hybrid_s3_cat_label_offsets[1];
extern const char *hybrid_s3_cat_labels_flat[2];

int hybrid_s3_gate_pass(const hybrid_s3_input_t *in);
float hybrid_s3_predict_proba_stage2(const hybrid_s3_input_t *in);
float hybrid_s3_predict_proba(const hybrid_s3_input_t *in);
int hybrid_s3_predict_label(const hybrid_s3_input_t *in);

#endif
