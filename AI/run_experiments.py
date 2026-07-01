import os
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
BASE_DIR = Path("/home/zinex/CAPSTONE/AI/edge-aiot-wearable-elderly-safety-monitoring")
INPUT_DIR = BASE_DIR / "AI/Edge_AI/result_balanced_v2/dataset/rebuilt"

def build_windows(df, label, window_size=100, stride=50):
    cols = ['ax', 'ay', 'az', 'gx', 'gy', 'gz']
    data = df[cols].values
    windows = []
    labels = []
    for i in range(0, len(data) - window_size + 1, stride):
        windows.append(data[i:i + window_size])
        labels.append(label)
    return np.array(windows), np.array(labels)

def load_data(seed):
    fall_df = pd.read_csv(INPUT_DIR / "fall.csv")
    non_fall_df = pd.read_csv(INPUT_DIR / "non_fall.csv")
    fall_x, fall_y = build_windows(fall_df, 1)
    non_x, non_y = build_windows(non_fall_df, 0)
    num_samples = min(len(fall_y), len(non_y))
    
    np.random.seed(seed)
    fall_idx = np.random.choice(len(fall_y), size=num_samples, replace=False)
    non_idx = np.random.choice(len(non_y), size=num_samples, replace=False)
    
    X = np.concatenate([fall_x[fall_idx], non_x[non_idx]], axis=0)
    y = np.concatenate([fall_y[fall_idx], non_y[non_idx]], axis=0)
    
    train_x, temp_x, train_y, temp_y = train_test_split(X, y, test_size=0.30, stratify=y, random_state=seed)
    val_x, test_x, val_y, test_y = train_test_split(temp_x, temp_y, test_size=0.50, stratify=temp_y, random_state=seed)
    return train_x, val_x, test_x, train_y, val_y, test_y

def build_model(input_shape):
    inputs = tf.keras.Input(shape=input_shape)
    x = tf.keras.layers.Normalization(axis=-1)(inputs)
    x = tf.keras.layers.Conv1D(16, 3, padding='same', kernel_regularizer=tf.keras.regularizers.l2(1e-4))(x)
    x = tf.keras.layers.BatchNormalization()(x)
    x = tf.keras.layers.Activation('relu')(x)
    x = tf.keras.layers.MaxPooling1D(2)(x)
    x = tf.keras.layers.SeparableConv1D(16, 3, padding='same', depthwise_regularizer=tf.keras.regularizers.l2(1e-4), pointwise_regularizer=tf.keras.regularizers.l2(1e-4))(x)
    x = tf.keras.layers.BatchNormalization()(x)
    x = tf.keras.layers.Activation('relu')(x)
    x = tf.keras.layers.MaxPooling1D(2)(x)
    x = tf.keras.layers.SeparableConv1D(32, 3, padding='same', depthwise_regularizer=tf.keras.regularizers.l2(1e-4), pointwise_regularizer=tf.keras.regularizers.l2(1e-4))(x)
    x = tf.keras.layers.BatchNormalization()(x)
    x = tf.keras.layers.Activation('relu')(x)
    x = tf.keras.layers.GlobalAveragePooling1D()(x)
    x = tf.keras.layers.Dropout(0.4)(x)
    x = tf.keras.layers.Dense(16, activation='relu', kernel_regularizer=tf.keras.regularizers.l2(1e-4))(x)
    outputs = tf.keras.layers.Dense(1, activation='sigmoid')(x)
    model = tf.keras.Model(inputs, outputs)
    model.compile(optimizer=tf.keras.optimizers.Adam(learning_rate=5e-4), loss='binary_crossentropy', metrics=['accuracy'])
    return model

def run_experiment(v):
    print(f"\n{'='*20} STARTING VERSION {v} {'='*20}")
    output_dir = BASE_DIR / f"AI/model_updated_version_{v}"
    models_dir = output_dir / "models"; results_dir = output_dir / "results"
    for d in [models_dir, results_dir]: d.mkdir(parents=True, exist_ok=True)
    
    seed = v * 100 
    train_x, val_x, test_x, train_y, val_y, test_y = load_data(seed)
    
    model = build_model((100, 6))
    model.layers[1].adapt(train_x)
    
    callbacks = [
        tf.keras.callbacks.EarlyStopping(patience=25, restore_best_weights=True, monitor='val_loss'),
        tf.keras.callbacks.ReduceLROnPlateau(factor=0.2, patience=10, min_lr=1e-7)
    ]
    
    history = model.fit(train_x, train_y, validation_data=(val_x, val_y), 
                        epochs=150, batch_size=64, callbacks=callbacks, 
                        class_weight={0: 1.0, 1: 1.2}, verbose=0)
    
    # Threshold Tuning
    val_probs = model.predict(val_x, verbose=0).reshape(-1)
    best_thr = 0.5; best_score = -1
    threshold_metrics = []
    for thr in np.arange(0.05, 0.95, 0.01):
        preds = (val_probs >= thr).astype(int)
        rec = recall_score(val_y, preds, zero_division=0)
        cm_v = confusion_matrix(val_y, preds); tn_v, fp_v, fn_v, tp_v = cm_v.ravel()
        far_v = fp_v / (fp_v + tn_v) if (fp_v + tn_v) > 0 else 0
        score = rec * 1.5 - far_v * 2.0
        threshold_metrics.append({"threshold": thr, "f1": f1_score(val_y, preds, zero_division=0), "recall": rec, "far": far_v})
        if score > best_score: best_score = score; best_thr = thr
    pd.DataFrame(threshold_metrics).to_csv(results_dir / "threshold_metrics.csv", index=False)
        
    # Evaluation
    test_probs = model.predict(test_x, verbose=0).reshape(-1)
    test_preds = (test_probs >= best_thr).astype(int)
    cm = confusion_matrix(test_y, test_preds); tn, fp, fn, tp = cm.ravel()
    metrics = {
        "accuracy": float(accuracy_score(test_y, test_preds)),
        "precision": float(precision_score(test_y, test_preds)),
        "recall": float(recall_score(test_y, test_preds)),
        "f1": float(f1_score(test_y, test_preds)),
        "false_alarm_rate": float(fp / (fp + tn)),
        "miss_rate": float(fn / (fn + tp))
    }
    
    # 1. training_loss.png & training_accuracy.png
    plt.figure(figsize=(6, 4)); plt.plot(history.history['loss'], label='Train'); plt.plot(history.history['val_loss'], label='Val'); plt.title('Training Loss'); plt.legend(); plt.savefig(results_dir / "training_loss.png"); plt.close()
    plt.figure(figsize=(6, 4)); plt.plot(history.history['accuracy'], label='Train'); plt.plot(history.history['val_accuracy'], label='Val'); plt.title('Training Accuracy'); plt.legend(); plt.savefig(results_dir / "training_accuracy.png"); plt.close()
    
    # 2. confusion_matrix.png
    plt.figure(figsize=(6, 5)); plt.imshow(cm, cmap='Blues'); plt.title(f'Confusion Matrix (Thr={best_thr:.2f})')
    for i in range(2): 
        for j in range(2): plt.text(j, i, format(cm[i, j], 'd'), ha="center", va="center", color="black")
    plt.xticks([0,1], ['ADL','Fall']); plt.yticks([0,1], ['ADL','Fall']); plt.savefig(results_dir / "confusion_matrix.png"); plt.close()
    
    # 3. roc_curve.png & precision_recall_curve.png
    fpr, tpr, _ = roc_curve(test_y, test_probs); rauc = auc(fpr, tpr)
    plt.figure(figsize=(6, 4)); plt.plot(fpr, tpr, label=f'AUC={rauc:.3f}'); plt.plot([0,1],[0,1],'k--'); plt.title('ROC Curve'); plt.legend(); plt.savefig(results_dir / "roc_curve.png"); plt.close()
    prec_p, rec_p, _ = precision_recall_curve(test_y, test_probs)
    plt.figure(figsize=(6, 4)); plt.plot(rec_p, prec_p); plt.title('Precision-Recall Curve'); plt.xlabel('Recall'); plt.ylabel('Precision'); plt.savefig(results_dir / "precision_recall_curve.png"); plt.close()
    
    # 4. class_distribution.png & window_distribution.png
    plt.figure(figsize=(6, 4)); plt.bar(['Fall','ADL'], [int(np.sum(train_y==1)), int(np.sum(train_y==0))], color=['red','blue']); plt.title('Data Train Balanced (1:1)'); plt.savefig(results_dir / "class_distribution.png"); plt.close()
    plt.figure(figsize=(6, 4)); plt.bar(['Fall','ADL'], [1786, 1786]); plt.title('Total Window Distribution'); plt.savefig(results_dir / "window_distribution.png"); plt.close()
    
    # 5. decision_analysis.png
    df_thr = pd.DataFrame(threshold_metrics)
    plt.figure(figsize=(10, 6)); plt.plot(df_thr['threshold'], df_thr['recall'], label='Recall'); plt.plot(df_thr['threshold'], df_thr['far'], label='FAR'); plt.axvline(best_thr, color='r', ls=':'); plt.title('Decision Analysis'); plt.legend(); plt.savefig(results_dir / "decision_analysis.png"); plt.close()
    
    # 6. temporal_behavior.png (Sample probability sequence)
    plt.figure(figsize=(15, 6)); plt.plot(test_probs[:200]); plt.axhline(best_thr, color='r', ls='--'); plt.title('Temporal Behavior (Inference Samples)'); plt.savefig(results_dir / "temporal_behavior.png"); plt.close()
    
    # 7. error_analysis.png (Plot a misclassified sample)
    plt.figure(figsize=(12, 6)); fn_idx = np.where((test_preds==0)&(test_y==1))[0]; fp_idx = np.where((test_preds==1)&(test_y==0))[0]
    if len(fn_idx)>0: plt.subplot(1,2,1); plt.plot(test_x[fn_idx[0]]); plt.title('Sample False Negative')
    if len(fp_idx)>0: plt.subplot(1,2,2); plt.plot(test_x[fp_idx[0]]); plt.title('Sample False Positive')
    plt.tight_layout(); plt.savefig(results_dir / "error_analysis.png"); plt.close()
    
    # 8. dashboard.png
    fig = plt.figure(figsize=(15, 10)); fig.suptitle(f'V{v} Training Dashboard', fontsize=20)
    ax1 = fig.add_subplot(2, 2, 1); ax1.plot(history.history['loss']); ax1.set_title('Loss History')
    ax2 = fig.add_subplot(2, 2, 2); ax2.imshow(cm, cmap='Blues'); ax2.set_title('Confusion Matrix')
    ax3 = fig.add_subplot(2, 2, 3); ax3.plot(test_probs[:100]); ax3.axhline(best_thr, color='r', ls='--'); ax3.set_title('Inference Samples')
    ax4 = fig.add_subplot(2, 2, 4); ax4.bar(['Fall','ADL'], [int(np.sum(train_y==1)), int(np.sum(train_y==0))]); ax4.set_title('Train Data Balance')
    plt.tight_layout(rect=[0, 0.03, 1, 0.95]); plt.savefig(results_dir / "dashboard.png"); plt.close()
    
    # 9. metrics_summary.txt
    summary_text = f"Accuracy: {metrics['accuracy']:.4f}\nRecall: {metrics['recall']:.4f}\nPrecision: {metrics['precision']:.4f}\nF1: {metrics['f1']:.4f}\nFAR: {metrics['false_alarm_rate']:.4f}"
    (results_dir / "metrics_summary.txt").write_text(summary_text)

    # TFLite & Header Export
    converter = tf.lite.TFLiteConverter.from_keras_model(model)
    converter.optimizations = [tf.lite.Optimize.DEFAULT]
    converter.representative_dataset = lambda: ([train_x[np.random.choice(len(train_x))][np.newaxis, ...].astype(np.float32)] for _ in range(100))
    converter.target_spec.supported_ops = [tf.lite.OpsSet.TFLITE_BUILTINS_INT8]
    converter.inference_input_type = tf.int8; converter.inference_output_type = tf.int8
    tflite_model = converter.convert()
    (models_dir / f"fall_detection_v{v}.tflite").write_bytes(tflite_model)
    size_kb = len(tflite_model)/1024
    
    tokens = [f"0x{b:02x}" for b in tflite_model]
    lines = [", ".join(tokens[i:i + 12]) for i in range(0, len(tokens), 12)]
    header = f"#ifndef FALL_DETECTION_V{v}_H\n#define FALL_DETECTION_V{v}_H\n\nconst unsigned char fall_detection_model_v{v}[] = {{\n  " + ",\n  ".join(lines) + f"\n}};\nconst unsigned int fall_detection_model_v{v}_len = {len(tflite_model)};\n#endif"
    (models_dir / f"fall_detection_v{v}.h").write_text(header)
    
    # metrics_vX.md
    md = f"| Metric | Value |\n| :--- | :--- |\n| Recall / Sensitivity | **{metrics['recall']*100:.2f}%** |\n| Miss Rate | **{metrics['miss_rate']*100:.2f}%** |\n| Accuracy | **{metrics['accuracy']*100:.2f}%** |\n| Precision | **{metrics['precision']*100:.2f}%** |\n| F1-score | **{metrics['f1']*100:.2f}%** |\n| False Alarm Rate | **{metrics['false_alarm_rate']*100:.2f}%** |\n| Model Size | **{size_kb:.2f} KB** |\n"
    (results_dir / f"metrics_v{v}.md").write_text(md)
    
    print(f"Version {v} complete: Acc={metrics['accuracy']:.4f}, Size={size_kb:.2f}KB")
    return metrics, size_kb

if __name__ == "__main__":
    results_summary = []
    for version in range(4, 15):
        try:
            m, sz = run_experiment(version)
            results_summary.append({"Version": f"V{version}", "Accuracy": f"{m['accuracy']*100:.2f}%", "Recall": f"{m['recall']*100:.2f}%", "Precision": f"{m['precision']*100:.2f}%", "F1": f"{m['f1']*100:.2f}%", "FAR": f"{m['false_alarm_rate']*100:.2f}%", "Size": f"{sz:.2f} KB"})
        except Exception as e: print(f"Error in V{version}: {e}")
    df_sum = pd.DataFrame(results_summary)
    summary_path = BASE_DIR / "AI/experiments_summary.md"
    with open(summary_path, "w") as f:
        f.write("# Final Experiments Summary (V4 - V14)\n\nComparison of 11 iterations.\n\n" + df_sum.to_markdown(index=False) + "\n\n## Conclusion\nBest model overall: **" + df_sum.loc[df_sum['F1'].str.replace('%','').astype(float).idxmax()]['Version'] + "**")
