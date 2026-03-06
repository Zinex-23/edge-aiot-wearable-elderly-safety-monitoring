#include <stdbool.h>
#include <stdio.h>
#include <string.h>

#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "esp_log.h"

#include "hybrid_s3.h"

#define TAG "FALL_APP"

#define SOURCE_CODE_UP 0
#define SOURCE_CODE_WEDA 1
#define INFER_PERIOD_MS 1000

static void fill_demo_non_fall(hybrid_s3_input_t *in) {
    memset(in, 0, sizeof(*in));
    in->cat[0] = SOURCE_CODE_WEDA;

    // source_freq_hz
    in->num[0] = 50.0f;

    // Minimal plausible motion values so gate/model have non-zero signal.
    in->num[1] = 10.1f;   // acc_mag_abs_mean
    in->num[4] = 11.2f;   // acc_mag_max
    in->num[5] = 10.0f;   // acc_mag_mean
    in->num[10] = 0.7f;   // acc_mag_std (gate feature index 10)
    in->num[50] = 0.12f;  // gyro_mag_energy
    in->num[58] = 0.08f;  // gyro_mag_std
}

static void fill_demo_fall(hybrid_s3_input_t *in) {
    memset(in, 0, sizeof(*in));
    in->cat[0] = SOURCE_CODE_WEDA;
    in->num[0] = 50.0f;

    // Synthetic high-energy pattern to test the pipeline on device.
    in->num[1] = 16.8f;
    in->num[4] = 22.5f;
    in->num[5] = 14.2f;
    in->num[10] = 3.8f;
    in->num[12] = 140.0f;
    in->num[22] = 180.0f;
    in->num[32] = 165.0f;
    in->num[42] = 210.0f;
    in->num[50] = 12.0f;
    in->num[58] = 2.6f;
}

static void log_model_info_once(void) {
    ESP_LOGI(TAG, "Model loaded: trees=%d, nodes=%d",
             HYBRID_S3_NUM_TREES, HYBRID_S3_TOTAL_TREE_NODES);
    ESP_LOGI(TAG, "Gate: feature[%d]=%s %s %.6f",
             HYBRID_S3_GATE_NUMERIC_INDEX,
             hybrid_s3_numeric_feature_names[HYBRID_S3_GATE_NUMERIC_INDEX],
             HYBRID_S3_GATE_OP_GE ? ">=" : "<=",
             HYBRID_S3_GATE_THRESHOLD);
    ESP_LOGI(TAG, "Decision threshold: %.3f", HYBRID_S3_DECISION_THRESHOLD);
    ESP_LOGI(TAG, "Categorical feature '%s': code 0='%s', code 1='%s'",
             hybrid_s3_categorical_feature_names[0],
             hybrid_s3_cat_labels_flat[0],
             hybrid_s3_cat_labels_flat[1]);
}

void app_main(void) {
    log_model_info_once();

    int counter = 0;
    while (1) {
        hybrid_s3_input_t in;
        bool simulate_fall = ((counter % 10) >= 7);
        if (simulate_fall) {
            fill_demo_fall(&in);
        } else {
            fill_demo_non_fall(&in);
        }

        int gate = hybrid_s3_gate_pass(&in);
        float proba = hybrid_s3_predict_proba(&in);
        int pred = hybrid_s3_predict_label(&in);

        ESP_LOGI(TAG,
                 "iter=%d mode=%s gate=%d prob=%.4f pred=%d",
                 counter,
                 simulate_fall ? "FALL_DEMO" : "NON_FALL_DEMO",
                 gate,
                 (double)proba,
                 pred);
        if (pred == 1) {
            ESP_LOGW(TAG, "FALL ALERT");
        }

        counter++;
        vTaskDelay(pdMS_TO_TICKS(INFER_PERIOD_MS));
    }
}
