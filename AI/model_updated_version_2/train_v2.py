import os
import shutil
import json
import numpy as np
import pandas as pd
import tensorflow as tf
import matplotlib.pyplot as tf_plt
import matplotlib.pyplot as plt
from pathlib import Path
from sklearn.model_selection import train_test_split
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    confusion_matrix, roc_auc_score, precision_recall_curve, auc
)

# Configuration
CONFIG = {
    "window_size": 100,
    "stride": 50,
    "epochs": 100,
    "batch_size": 32,
    "initial_lr": 1e-3,
    "patience": 15,
    "target_tflite_kb": 20,
    "seed": 42
}

np.random.seed(CONFIG["seed"])
tf.random.set_seed(CONFIG["seed"])

# Paths
BASE_DIR = Path("/home/zinex/CAPSTONE/AI/edge-aiot-wearable-elderly-safety-monitoring")
INPUT_DIR = BASE_DIR / "AI/Edge_AI/result_balanced_v2/dataset/rebuilt"
OUTPUT_DIR = BASE_DIR / "AI/model_updated_version_2"
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
    
    # We will use 1:2 ratio to give more ADL exposure for lowering FAR
    num_fall = len(fall_y)
    num_non_fall = min(len(non_y), num_fall * 2)
    
    print(f"Balancing: Keeping all {num_fall} fall windows and {num_non_fall} non-fall windows.")
    
    non_idx = np.random.choice(len(non_y), size=num_non_fall, replace=False)
    non_x_bal = non_x[non_idx]
    non_y_bal = non_y[non_idx]
    
    X = np.concatenate([fall_x, non_x_bal], axis=0)
    y = np.concatenate([fall_y, non_y_bal], axis=0)
    
    return train_test_split(X, y, test_size=0.3, stratify=y, random_state=CONFIG["seed"])

def build_model_v2(input_shape):
    inputs = tf.keras.Input(shape=input_shape)
    
    # Pre-processing Layer
    x = tf.keras.layers.Normalization(axis=-1)(inputs)
    
    # V2 Deeper Architecture - Ultra Slim for < 20KB
    x = tf.keras.layers.Conv1D(8, 3, padding='same', activation='relu')(x)
    x = tf.keras.layers.BatchNormalization()(x)
    x = tf.keras.layers.MaxPooling1D(2)(x)
    
    x = tf.keras.layers.Conv1D(16, 3, padding='same', activation='relu')(x)
    x = tf.keras.layers.BatchNormalization()(x)
    x = tf.keras.layers.MaxPooling1D(2)(x)
    
    x = tf.keras.layers.Conv1D(32, 3, padding='same', activation='relu')(x)
    x = tf.keras.layers.BatchNormalization()(x)
    x = tf.keras.layers.GlobalAveragePooling1D()(x)
    
    x = tf.keras.layers.Dropout(0.3)(x)
    x = tf.keras.layers.Dense(16, activation='relu')(x)
    outputs = tf.keras.layers.Dense(1, activation='sigmoid')(x)
    
    model = tf.keras.Model(inputs, outputs, name="FallDetection_V2_UltraSlim")
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
    model = build_model_v2((CONFIG["window_size"], 6))
    
    # Adapt normalization layer
    norm_layer = model.layers[1]
    norm_layer.adapt(train_x)
    
    model.summary()

    # 3. Train
    callbacks = [
        tf.keras.callbacks.EarlyStopping(patience=CONFIG["patience"], restore_best_weights=True, monitor='val_loss'),
        tf.keras.callbacks.ReduceLROnPlateau(factor=0.5, patience=5, min_lr=1e-6, monitor='val_loss')
    ]

    # Class weights to prioritize Recall while training on 1:2 ratio
    # Increasing weight for Fall class (1) to 3.0
    class_weight = {0: 1.0, 1: 3.0} 

    print("Starting training...")
    history = model.fit(
        train_x, train_y,
        validation_data=(val_x, val_y),
        epochs=CONFIG["epochs"],
        batch_size=CONFIG["batch_size"],
        callbacks=callbacks,
        class_weight=class_weight,
        verbose=1
    )

    # 4. Save results
    pd.DataFrame(history.history).to_csv(RESULTS_DIR / "history.csv", index=False)

    # 5. Optimize Threshold on Val set for F1 and low FAR
    val_probs = model.predict(val_x).reshape(-1)
    best_thr = 0.5
    best_f1 = 0
    
    thresholds = np.arange(0.1, 0.95, 0.01)
    decision_metrics = []
    
    for thr in thresholds:
        preds = (val_probs >= thr).astype(int)
        f1 = f1_score(val_y, preds, zero_division=0)
        rec = recall_score(val_y, preds, zero_division=0)
        prec = precision_score(val_y, preds, zero_division=0)
        
        cm_val = confusion_matrix(val_y, preds)
        tn_v, fp_val, fn_val, tp_val = cm_val.ravel()
        far_val = fp_val / (fp_val + tn_v) if (fp_val + tn_v) > 0 else 0
        
        decision_metrics.append({
            "threshold": thr,
            "f1": f1,
            "recall": rec,
            "precision": prec,
            "far": far_val
        })
        
        if f1 > best_f1:
            best_f1 = f1
            best_thr = thr

    print(f"Optimal Threshold found on validation set: {best_thr:.2f}")
    
    # Save decision metrics
    pd.DataFrame(decision_metrics).to_csv(RESULTS_DIR / "threshold_metrics.csv", index=False)

    # 6. Evaluate on Test set
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

    print("\n--- Test Metrics ---")
    print(json.dumps(metrics, indent=4))

    with open(RESULTS_DIR / "metrics_v2.json", "w") as f:
        json.dump(metrics, f, indent=4)

    # --- ENHANCED PLOTTING ---
    print("\nGenerating visualization plots...")
    
    # Plot Training History
    plt.figure(figsize=(12, 4))
    plt.subplot(1, 2, 1)
    plt.plot(history.history['loss'], label='Train Loss')
    plt.plot(history.history['val_loss'], label='Val Loss')
    plt.title('Training Loss')
    plt.xlabel('Epoch')
    plt.ylabel('Loss')
    plt.legend()
    plt.grid(True, alpha=0.3)
    
    plt.subplot(1, 2, 2)
    plt.plot(history.history['accuracy'], label='Train Acc')
    plt.plot(history.history['val_accuracy'], label='Val Acc')
    plt.title('Training Accuracy')
    plt.xlabel('Epoch')
    plt.ylabel('Accuracy')
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.savefig(RESULTS_DIR / "training_curves.png", dpi=150)
    plt.savefig(RESULTS_DIR / "training_loss.png", dpi=150) # Split for compatibility
    
    # Plot Confusion Matrix
    plt.figure(figsize=(6, 5))
    plt.imshow(cm, interpolation='nearest', cmap=plt.cm.Blues)
    plt.title(f"Confusion Matrix (Thr={best_thr:.2f})")
    plt.colorbar()
    tick_marks = np.arange(2)
    plt.xticks(tick_marks, ['Non-Fall', 'Fall'])
    plt.yticks(tick_marks, ['Non-Fall', 'Fall'])
    
    thresh = cm.max() / 2.
    for i in range(cm.shape[0]):
        for j in range(cm.shape[1]):
            plt.text(j, i, format(cm[i, j], 'd'),
                     ha="center", va="center",
                     color="white" if cm[i, j] > thresh else "black")
    plt.ylabel('True Label')
    plt.xlabel('Predicted Label')
    plt.tight_layout()
    plt.savefig(RESULTS_DIR / "confusion_matrix.png", dpi=150)
    
    # Plot ROC and PR Curves
    plt.figure(figsize=(12, 5))
    
    # ROC
    from sklearn.metrics import roc_curve, auc as sk_auc
    fpr, tpr, _ = roc_curve(test_y, test_probs)
    roc_auc = sk_auc(fpr, tpr)
    plt.subplot(1, 2, 1)
    plt.plot(fpr, tpr, color='darkorange', lw=2, label=f'ROC curve (area = {roc_auc:.3f})')
    plt.plot([0, 1], [0, 1], color='navy', lw=2, linestyle='--')
    plt.xlim([0.0, 1.0])
    plt.ylim([0.0, 1.05])
    plt.xlabel('False Positive Rate')
    plt.ylabel('True Positive Rate')
    plt.title('ROC Curve')
    plt.legend(loc="lower right")
    plt.grid(True, alpha=0.3)
    
    # PR
    prec_pts, rec_pts, _ = precision_recall_curve(test_y, test_probs)
    pr_auc = sk_auc(rec_pts, prec_pts)
    plt.subplot(1, 2, 2)
    plt.plot(rec_pts, prec_pts, color='green', lw=2, label=f'PR curve (area = {pr_auc:.3f})')
    plt.xlabel('Recall')
    plt.ylabel('Precision')
    plt.title('Precision-Recall Curve')
    plt.legend(loc="lower left")
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(RESULTS_DIR / "roc_pr_curves.png", dpi=150)
    plt.savefig(RESULTS_DIR / "roc_curve.png", dpi=150)
    plt.savefig(RESULTS_DIR / "precision_recall_curve.png", dpi=150)

    # Plot Decision Analysis (Threshold Sweep)
    df_dm = pd.DataFrame(decision_metrics)
    plt.figure(figsize=(10, 6))
    plt.plot(df_dm['threshold'], df_dm['f1'], label='F1-Score', lw=2)
    plt.plot(df_dm['threshold'], df_dm['recall'], label='Recall', linestyle='--')
    plt.plot(df_dm['threshold'], df_dm['precision'], label='Precision', linestyle='--')
    plt.axvline(best_thr, color='red', linestyle=':', label=f'Optimal Thr ({best_thr:.2f})')
    plt.title('Metric vs Threshold Analysis')
    plt.xlabel('Threshold')
    plt.ylabel('Score')
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.savefig(RESULTS_DIR / "decision_analysis.png", dpi=150)

    # Window Distribution (Dummy counts for now based on load_data logic)
    # In a real script we'd pass these from load_data
    plt.figure(figsize=(8, 5))
    plt.bar(['Fall', 'Non-Fall'], [int(np.sum(train_y==1) + np.sum(test_y==1) + np.sum(val_y==1)), 
                                   int(np.sum(train_y==0) + np.sum(test_y==0) + np.sum(val_y==0))],
            color=['#ff9999','#66b3ff'])
    plt.title('Final Balanced Dataset Distribution')
    plt.ylabel('Number of Windows')
    plt.savefig(RESULTS_DIR / "class_distribution.png", dpi=150)
    plt.savefig(RESULTS_DIR / "window_distribution.png", dpi=150)

    # Temporal Behavior (Mock-up continuous stream)
    print("Generating temporal behavior plot...")
    plt.figure(figsize=(15, 6))
    # Concatenate 5 windows for a "continuous" feel
    indices = np.random.choice(len(test_x), size=10, replace=False)
    long_signal = np.concatenate([test_x[i] for i in indices], axis=0)
    
    # Calculate probs for each window in a rolling fashion (step=10)
    rolling_probs = []
    for start in range(0, len(long_signal) - 100 + 1, 10):
        w = long_signal[start:start+100][np.newaxis, ...]
        p = model.predict(w, verbose=0)[0][0]
        rolling_probs.append(p)
    
    plt.subplot(2, 1, 1)
    plt.plot(long_signal[:, :3]) # Acc only for clarity
    plt.title('Simulated Continuous IMU Stream (Accelerometer)')
    plt.ylabel('Normalized G')
    
    plt.subplot(2, 1, 2)
    plt.plot(np.arange(len(rolling_probs))*10 + 50, rolling_probs, color='red', label='Fall Prob')
    plt.axhline(best_thr, color='black', linestyle='--', label='Threshold')
    plt.fill_between(np.arange(len(rolling_probs))*10 + 50, rolling_probs, best_thr, 
                     where=(np.array(rolling_probs) >= best_thr), color='red', alpha=0.3)
    plt.title('Detection Probability Over Time')
    plt.xlabel('Sample Index')
    plt.ylabel('Probability')
    plt.legend()
    plt.tight_layout()
    plt.savefig(RESULTS_DIR / "temporal_behavior.png", dpi=150)

    # Error Analysis
    print("Generating error analysis plot...")
    fp_indices = np.where((test_preds == 1) & (test_y == 0))[0]
    fn_indices = np.where((test_preds == 0) & (test_y == 1))[0]
    
    plt.figure(figsize=(12, 8))
    for i in range(min(4, len(fp_indices))):
        plt.subplot(2, 4, i+1)
        plt.plot(test_x[fp_indices[i]])
        plt.title(f'False Positive {i+1}')
    for i in range(min(4, len(fn_indices))):
        plt.subplot(2, 4, i+5)
        plt.plot(test_x[fn_indices[i]])
        plt.title(f'False Negative {i+1}')
    plt.suptitle('Error Analysis: Misclassified Windows', fontsize=16)
    plt.tight_layout(rect=[0, 0.03, 1, 0.95])
    plt.savefig(RESULTS_DIR / "error_analysis.png", dpi=150)

    # Create Dashboard (Summary)
    fig = plt.figure(figsize=(15, 12))
    fig.suptitle('CaraFall AI V2 Training Dashboard', fontsize=24, fontweight='bold')
    
    # Add existing plots to dashboard (re-plotting for layout control)
    ax1 = fig.add_subplot(3, 3, 1)
    ax1.plot(history.history['loss'], label='Train')
    ax1.plot(history.history['val_loss'], label='Val')
    ax1.set_title('Loss History')
    ax1.legend()
    
    ax2 = fig.add_subplot(3, 3, 2)
    ax2.plot(history.history['accuracy'], label='Train')
    ax2.plot(history.history['val_accuracy'], label='Val')
    ax2.set_title('Accuracy History')
    ax2.legend()
    
    ax3 = fig.add_subplot(3, 3, 3)
    ax3.imshow(cm, cmap=plt.cm.Blues)
    ax3.set_title('Confusion Matrix')
    
    ax4 = fig.add_subplot(3, 3, 4)
    ax4.plot(fpr, tpr, color='orange', label=f'AUC={roc_auc:.2f}')
    ax4.set_title('ROC Curve')
    ax4.legend()
    
    ax5 = fig.add_subplot(3, 3, 5)
    ax5.plot(df_dm['threshold'], df_dm['f1'], label='F1')
    ax5.axvline(best_thr, color='r', linestyle=':')
    ax5.set_title('Threshold Tuning')
    
    ax6 = fig.add_subplot(3, 3, 6)
    ax6.plot(rec_pts, prec_pts, color='green', label=f'PR={pr_auc:.2f}')
    ax6.set_title('Precision-Recall')
    ax6.legend()

    ax7 = fig.add_subplot(3, 1, 3)
    ax7.plot(long_signal[:, :3], alpha=0.5)
    ax7_2 = ax7.twinx()
    ax7_2.plot(np.arange(len(rolling_probs))*10 + 50, rolling_probs, color='red', lw=2)
    ax7_2.set_ylabel('Prob', color='red')
    ax7.set_title('Detection Behavior on Stream')
    
    plt.tight_layout(rect=[0, 0.03, 1, 0.95])
    plt.savefig(RESULTS_DIR / "dashboard.png", dpi=200)

    # 7. TFLite Conversion (INT8 Quantization)
    def representative_dataset():
        for i in range(100):
            sample = train_x[np.random.choice(len(train_x))]
            yield [sample[np.newaxis, ...].astype(np.float32)]

    print("\nConverting to TFLite INT8...")
    converter = tf.lite.TFLiteConverter.from_keras_model(model)
    converter.optimizations = [tf.lite.Optimize.DEFAULT]
    converter.representative_dataset = representative_dataset
    converter.target_spec.supported_ops = [tf.lite.OpsSet.TFLITE_BUILTINS_INT8]
    converter.inference_input_type = tf.int8
    converter.inference_output_type = tf.int8
    
    tflite_model = converter.convert()
    tflite_path = MODELS_DIR / "fall_detection_v2.tflite"
    tflite_path.write_bytes(tflite_model)
    
    size_kb = len(tflite_model) / 1024.0
    print(f"TFLite model size: {size_kb:.2f} KB")

    # 8. Export C++ Header
    tokens = [f"0x{b:02x}" for b in tflite_model]
    lines = [", ".join(tokens[i:i + 12]) for i in range(0, len(tokens), 12)]
    header_content = "#ifndef FALL_DETECTION_V2_H\n#define FALL_DETECTION_V2_H\n\n"
    header_content += "const unsigned char fall_detection_v2_tflite[] = {\n  " + ",\n  ".join(lines) + "\n};\n\n"
    header_content += f"const unsigned int fall_detection_v2_tflite_len = {len(tflite_model)};\n\n#endif"
    
    (MODELS_DIR / "fall_detection_v2.h").write_text(header_content)
    print("Exported C++ header.")

if __name__ == "__main__":
    main()
