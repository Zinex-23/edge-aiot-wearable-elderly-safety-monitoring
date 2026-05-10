import os
import shutil
import json
import numpy as np
import pandas as pd
import tensorflow as tf
import matplotlib.pyplot as plt
from pathlib import Path
from sklearn.model_selection import train_test_split
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    confusion_matrix, roc_curve, precision_recall_curve, auc
)

# Configuration
CONFIG = {
    "window_size": 100,
    "stride": 50,
    "epochs": 150,
    "batch_size": 64,
    "initial_lr": 5e-4, # Lower LR for stability
    "patience": 25,     # Higher patience
    "target_tflite_kb": 20,
    "seed": 42
}

np.random.seed(CONFIG["seed"])
tf.random.set_seed(CONFIG["seed"])

# Paths
BASE_DIR = Path("/home/zinex/CAPSTONE/AI/edge-aiot-wearable-elderly-safety-monitoring")
INPUT_DIR = BASE_DIR / "AI/Edge_AI/result_balanced_v2/dataset/rebuilt"
OUTPUT_DIR = BASE_DIR / "AI/model_updated_version_3"
MODELS_DIR = OUTPUT_DIR / "models"
RESULTS_DIR = OUTPUT_DIR / "results"

for d in [MODELS_DIR, RESULTS_DIR]:
    d.mkdir(parents=True, exist_ok=True)

def build_windows(df, label, window_size=100, stride=50):
    cols = ['ax', 'ay', 'az', 'gx', 'gy', 'gz']
    data = df[cols].values
    windows = []
    labels = []
    for i in range(0, len(data) - window_size + 1, stride):
        windows.append(data[i:i + window_size])
        labels.append(label)
    return np.array(windows), np.array(labels)

def load_data():
    print(f"Loading data from {INPUT_DIR}...")
    fall_df = pd.read_csv(INPUT_DIR / "fall.csv")
    non_fall_df = pd.read_csv(INPUT_DIR / "non_fall.csv")
    
    fall_x, fall_y = build_windows(fall_df, 1)
    non_x, non_y = build_windows(non_fall_df, 0)
    
    # EXACT 1:1 RATIO
    num_samples = min(len(fall_y), len(non_y))
    print(f"Balancing: EXACT 1:1 ratio. Using {num_samples} samples per class.")
    
    fall_idx = np.random.choice(len(fall_y), size=num_samples, replace=False)
    non_idx = np.random.choice(len(non_y), size=num_samples, replace=False)
    
    X = np.concatenate([fall_x[fall_idx], non_x[non_idx]], axis=0)
    y = np.concatenate([fall_y[fall_idx], non_y[non_idx]], axis=0)
    
    return train_test_split(X, y, test_size=0.3, stratify=y, random_state=CONFIG["seed"])

def build_model_v3(input_shape):
    # Stabilized Architecture for V3
    inputs = tf.keras.Input(shape=input_shape)
    
    # Pre-processing Layer
    x = tf.keras.layers.Normalization(axis=-1)(inputs)
    
    # Conv Block 1
    x = tf.keras.layers.Conv1D(16, 3, padding='same', kernel_regularizer=tf.keras.regularizers.l2(1e-4))(x)
    x = tf.keras.layers.BatchNormalization()(x)
    x = tf.keras.layers.Activation('relu')(x)
    x = tf.keras.layers.MaxPooling1D(2)(x)
    
    # Conv Block 2 (Separable for efficiency)
    x = tf.keras.layers.SeparableConv1D(16, 3, padding='same', 
                                        depthwise_regularizer=tf.keras.regularizers.l2(1e-4),
                                        pointwise_regularizer=tf.keras.regularizers.l2(1e-4))(x)
    x = tf.keras.layers.BatchNormalization()(x)
    x = tf.keras.layers.Activation('relu')(x)
    x = tf.keras.layers.MaxPooling1D(2)(x)
    
    # Conv Block 3
    x = tf.keras.layers.SeparableConv1D(32, 3, padding='same',
                                        depthwise_regularizer=tf.keras.regularizers.l2(1e-4),
                                        pointwise_regularizer=tf.keras.regularizers.l2(1e-4))(x)
    x = tf.keras.layers.BatchNormalization()(x)
    x = tf.keras.layers.Activation('relu')(x)
    x = tf.keras.layers.GlobalAveragePooling1D()(x)
    
    # Fully Connected
    x = tf.keras.layers.Dropout(0.4)(x) # Increased dropout for stability
    x = tf.keras.layers.Dense(16, activation='relu', kernel_regularizer=tf.keras.regularizers.l2(1e-4))(x)
    outputs = tf.keras.layers.Dense(1, activation='sigmoid')(x)
    
    model = tf.keras.Model(inputs, outputs, name="FallDetection_V3_Stable")
    model.compile(
        optimizer=tf.keras.optimizers.Adam(learning_rate=CONFIG["initial_lr"]),
        loss='binary_crossentropy',
        metrics=['accuracy', tf.keras.metrics.Recall(name='recall'), tf.keras.metrics.Precision(name='precision')]
    )
    return model

def main():
    # 1. Load and Split Data
    train_x, test_x, train_y, test_y = load_data()
    train_x, val_x, train_y, val_y = train_test_split(train_x, train_y, test_size=0.2, stratify=train_y, random_state=CONFIG["seed"])

    # 2. Build and Adapt Normalization
    model = build_model_v3((CONFIG["window_size"], 6))
    
    # Adapt normalization layer
    norm_layer = model.layers[1]
    norm_layer.adapt(train_x)
    
    model.summary()

    # 3. Train with stability callbacks
    callbacks = [
        tf.keras.callbacks.EarlyStopping(
            patience=CONFIG["patience"], 
            restore_best_weights=True, 
            monitor='val_recall', # Prioritize recall during early stopping? No, val_loss is safer for overall stability.
            mode='max' if 'recall' in 'val_recall' else 'auto'
        ),
        tf.keras.callbacks.ReduceLROnPlateau(factor=0.2, patience=10, min_lr=1e-7, monitor='val_loss')
    ]
    
    # Override monitor to val_loss for overall stability but watch recall
    callbacks[0].monitor = 'val_loss'
    callbacks[0].mode = 'min'

    print("Starting training V3...")
    history = model.fit(
        train_x, train_y,
        validation_data=(val_x, val_y),
        epochs=CONFIG["epochs"],
        batch_size=CONFIG["batch_size"],
        callbacks=callbacks,
        # 1:1 ratio so no class_weight needed, or subtle weight for Recall
        class_weight={0: 1.0, 1: 1.2}, 
        verbose=1
    )

    # 4. Save results
    pd.DataFrame(history.history).to_csv(RESULTS_DIR / "history.csv", index=False)

    # 5. Optimize Threshold on Val set for High Recall + Low FAR
    val_probs = model.predict(val_x).reshape(-1)
    best_thr = 0.5
    best_score = -1
    
    thresholds = np.arange(0.05, 0.95, 0.01)
    decision_metrics = []
    
    for thr in thresholds:
        preds = (val_probs >= thr).astype(int)
        rec = recall_score(val_y, preds, zero_division=0)
        prec = precision_score(val_y, preds, zero_division=0)
        f1 = f1_score(val_y, preds, zero_division=0)
        
        cm_val = confusion_matrix(val_y, preds)
        tn_v, fp_v, fn_v, tp_v = cm_val.ravel()
        far_v = fp_v / (fp_v + tn_v) if (fp_v + tn_v) > 0 else 0
        
        # Scoring function: Prioritize low FAR while maintaining good Recall
        # Goal: FAR < 0.08, Recall > 0.90
        score = rec * 1.0 - far_v * 3.0 
        
        decision_metrics.append({
            "threshold": thr, "f1": f1, "recall": rec, "precision": prec, "far": far_v, "score": score
        })
        
        if score > best_score:
            best_score = score
            best_thr = thr

    print(f"Optimal Threshold found: {best_thr:.2f} (Score: {best_score:.2f})")
    pd.DataFrame(decision_metrics).to_csv(RESULTS_DIR / "threshold_metrics.csv", index=False)

    # 6. Final Evaluation
    test_probs = model.predict(test_x).reshape(-1)
    test_preds = (test_probs >= best_thr).astype(int)

    cm = confusion_matrix(test_y, test_preds)
    tn, fp, fn, tp = cm.ravel()
    metrics = {
        "accuracy": float(accuracy_score(test_y, test_preds)),
        "precision": float(precision_score(test_y, test_preds)),
        "recall": float(recall_score(test_y, test_preds)),
        "f1": float(f1_score(test_y, test_preds)),
        "false_alarm_rate": float(fp / (fp + tn)),
        "miss_rate": float(fn / (fn + tp)),
        "confusion_matrix": cm.tolist()
    }

    print("\n--- Test Metrics V3 ---")
    print(json.dumps(metrics, indent=4))
    with open(RESULTS_DIR / "metrics_v3.json", "w") as f:
        json.dump(metrics, f, indent=4)

    # --- PLOTTING ---
    print("\nGenerating V3 plots...")
    
    # 1. Training curves
    plt.figure(figsize=(12, 4))
    plt.subplot(1, 2, 1)
    plt.plot(history.history['loss'], label='Train Loss')
    plt.plot(history.history['val_loss'], label='Val Loss')
    plt.title('V3 Training Loss (Stabilized)')
    plt.legend(); plt.grid(True, alpha=0.3)
    
    plt.subplot(1, 2, 2)
    plt.plot(history.history['accuracy'], label='Train Acc')
    plt.plot(history.history['val_accuracy'], label='Val Acc')
    plt.title('V3 Training Accuracy')
    plt.legend(); plt.grid(True, alpha=0.3)
    plt.savefig(RESULTS_DIR / "training_curves.png", dpi=150)

    # 2. Confusion Matrix
    plt.figure(figsize=(6, 5))
    plt.imshow(cm, interpolation='nearest', cmap=plt.cm.Greens)
    plt.title(f"V3 Confusion Matrix (Thr={best_thr:.2f})")
    plt.colorbar()
    for i in range(2):
        for j in range(2):
            plt.text(j, i, format(cm[i, j], 'd'), ha="center", va="center", color="black")
    plt.xticks([0,1], ['Non-Fall', 'Fall']); plt.yticks([0,1], ['Non-Fall', 'Fall'])
    plt.savefig(RESULTS_DIR / "confusion_matrix.png", dpi=150)

    # 3. Decision Analysis
    df_dm = pd.DataFrame(decision_metrics)
    plt.figure(figsize=(10, 6))
    plt.plot(df_dm['threshold'], df_dm['recall'], label='Recall', lw=2)
    plt.plot(df_dm['threshold'], df_dm['far'], label='False Alarm Rate', lw=2)
    plt.axvline(best_thr, color='red', linestyle='--', label=f'Best Thr ({best_thr:.2f})')
    plt.title('Recall vs FAR across Thresholds')
    plt.xlabel('Threshold'); plt.ylabel('Rate'); plt.legend(); plt.grid(True, alpha=0.3)
    plt.savefig(RESULTS_DIR / "decision_analysis.png", dpi=150)

    # 4. ROC/PR
    fpr, tpr, _ = roc_curve(test_y, test_probs)
    roc_auc = auc(fpr, tpr)
    plt.figure(figsize=(6, 5))
    plt.plot(fpr, tpr, label=f'AUC = {roc_auc:.3f}')
    plt.plot([0,1],[0,1],'k--')
    plt.title('ROC Curve V3'); plt.legend(); plt.grid(True, alpha=0.3)
    plt.savefig(RESULTS_DIR / "roc_curve.png", dpi=150)

    # 5. Dashboard
    fig = plt.figure(figsize=(15, 10))
    fig.suptitle('CaraFall AI V3 Final Dashboard', fontsize=20)
    ax1 = fig.add_subplot(2, 2, 1)
    ax1.plot(history.history['loss'], label='Loss'); ax1.set_title('Stability (Loss)')
    ax2 = fig.add_subplot(2, 2, 2)
    ax2.imshow(cm, cmap=plt.cm.Greens); ax2.set_title('Final Confusion Matrix')
    ax3 = fig.add_subplot(2, 2, 3)
    ax3.plot(df_dm['threshold'], df_dm['recall'], label='Recall')
    ax3.plot(df_dm['threshold'], df_dm['far'], label='FAR')
    ax3.axvline(best_thr, color='r'); ax3.set_title('Threshold Tuning')
    ax4 = fig.add_subplot(2, 2, 4)
    ax4.bar(['Fall', 'Non-Fall'], [int(np.sum(test_y==1)), int(np.sum(test_y==0))])
    ax4.set_title('Test Set Balance (1:1)')
    plt.tight_layout(rect=[0, 0.03, 1, 0.95])
    plt.savefig(RESULTS_DIR / "dashboard.png", dpi=200)

    # 7. TFLite Conversion
    def representative_dataset():
        for _ in range(100):
            yield [train_x[np.random.choice(len(train_x))][np.newaxis, ...].astype(np.float32)]

    print("\nConverting V3 to TFLite INT8...")
    converter = tf.lite.TFLiteConverter.from_keras_model(model)
    converter.optimizations = [tf.lite.Optimize.DEFAULT]
    converter.representative_dataset = representative_dataset
    converter.target_spec.supported_ops = [tf.lite.OpsSet.TFLITE_BUILTINS_INT8]
    converter.inference_input_type = tf.int8
    converter.inference_output_type = tf.int8
    
    tflite_model = converter.convert()
    (MODELS_DIR / "fall_detection_v3.tflite").write_bytes(tflite_model)
    print(f"V3 Size: {len(tflite_model)/1024:.2f} KB")

    # Header Export
    tokens = [f"0x{b:02x}" for b in tflite_model]
    lines = [", ".join(tokens[i:i + 12]) for i in range(0, len(tokens), 12)]
    header = "#ifndef FALL_DETECTION_V3_H\n#define FALL_DETECTION_V3_H\n\n"
    header += "const unsigned char fall_detection_v3_tflite[] = {\n  " + ",\n  ".join(lines) + "\n};\n"
    header += f"const unsigned int fall_detection_v3_tflite_len = {len(tflite_model)};\n#endif"
    (MODELS_DIR / "fall_detection_v3.h").write_text(header)

if __name__ == "__main__":
    main()
