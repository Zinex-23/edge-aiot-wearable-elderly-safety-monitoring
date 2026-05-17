"""
Train V61-V70 fall detection models.

Design rationale (learned from V1-V60):
─────────────────────────────────────────────────────────────────────────────
V22  [16,32,48,64]/K5/D16  → FAR=10.07%, F1=92.53%  best small-model K5
V27  [32,64,64,96]/K3/D32  → FAR=8.96%              D32 reduces FAR
V54  D32 added to V50      → F1=93.07%               best F1 ever
V59  batch=32 with V50     → FAR=8.21%               best FAR/F1 tradeoff
V56  dropout=0.5           → FAR=7.84%               regularization lowers FAR

Key combos never tried together:
  V54 + V59  : [32,48,64,96]/K5/D32 + batch=32
  V22 arch   : [16,32,48,64]/K5    + D32 + batch=32
  V56 + V59  : dropout=0.5         + batch=32
  V27 arch   : [32,64,64,96]/K3/D32 + batch=32
  5 conv layers (novel depth beyond V50)
─────────────────────────────────────────────────────────────────────────────

V61: [16,32,48,64]/K5/D32 + batch=32 + cw=1.2   (V22 arch + best training)
V62: [32,48,64,96]/K5/D32 + batch=32 + cw=1.2   (V54 + V59 combined)
V63: [32,48,64,96]/K5/D20 + dropout=0.5 + batch=32 + cw=1.2 (V56 + V59)
V64: [32,64,64,96]/K3/D32 + batch=32 + cw=1.2   (V27 arch + batch=32)
V65: [24,48,64,96]/K5/D24 + batch=32 + cw=1.2   (V37 arch + D24 + batch=32)
V66: [16,32,48,64]/K5/D24 + batch=32 + dropout=0.45 + cw=1.2 (V22 tuned)
V67: [32,48,64,96]/K5/D32 + dropout=0.5 + batch=32 + cw=1.2  (max regularize)
V68: [32,48,64,96]/K5/D20 + LR=1e-4 + batch=32 + cw=1.2      (V58+V59)
V69: [32,48,64,96]/K5/D32 + L2=5e-4 + batch=32 + cw=1.2      (V54+V59+V57)
V70: [16,32,48,64,96]/K5/D24 + batch=32 + cw=1.2  (5 conv layers — novel)
"""

import json
import numpy as np
import pandas as pd
import tensorflow as tf
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from pathlib import Path
from sklearn.model_selection import train_test_split
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    confusion_matrix, roc_curve, precision_recall_curve, auc
)

BASE_DIR = Path("/home/zinex/CAPSTONE/AI/edge-aiot-wearable-elderly-safety-monitoring")
DATA_DIR = BASE_DIR / "AI/Edge_AI/result_balanced_v2/dataset/rebuilt"
AI_DIR   = BASE_DIR / "AI"

# ─────────────────────────────────────────────────────────────────────────────
VERSIONS = {
    61: dict(
        filters=[16,32,48,64], kernels=[5,5,5,5], dense=32,
        lr=3e-4, dropout=0.4, l2=1e-4, batch=32, epochs=200, cw={0:1.0,1:1.2},
        thr_score=lambda r,f: r*1.5 - f*2.0,
        note="V22 arch [16,32,48,64]/K5 + D32 + batch=32",
    ),
    62: dict(
        filters=[32,48,64,96], kernels=[5,5,5,5], dense=32,
        lr=3e-4, dropout=0.4, l2=1e-4, batch=32, epochs=200, cw={0:1.0,1:1.2},
        thr_score=lambda r,f: r*1.5 - f*2.0,
        note="V54+V59 combo: D32 + batch=32 (best F1 + best FAR combo)",
    ),
    63: dict(
        filters=[32,48,64,96], kernels=[5,5,5,5], dense=20,
        lr=3e-4, dropout=0.5, l2=1e-4, batch=32, epochs=200, cw={0:1.0,1:1.2},
        thr_score=lambda r,f: r*1.5 - f*2.0,
        note="V56+V59 combo: dropout=0.5 + batch=32 (FAR reduction focus)",
    ),
    64: dict(
        filters=[32,64,64,96], kernels=[3,3,3,3], dense=32,
        lr=3e-4, dropout=0.4, l2=1e-4, batch=32, epochs=200, cw={0:1.0,1:1.2},
        thr_score=lambda r,f: r*1.5 - f*2.0,
        note="V27 arch [32,64,64,96]/K3/D32 + batch=32",
    ),
    65: dict(
        filters=[24,48,64,96], kernels=[5,5,5,5], dense=24,
        lr=3e-4, dropout=0.4, l2=1e-4, batch=32, epochs=200, cw={0:1.0,1:1.2},
        thr_score=lambda r,f: r*1.5 - f*2.0,
        note="V37 arch [24,48,64,96]/K5 + D24 + batch=32",
    ),
    66: dict(
        filters=[16,32,48,64], kernels=[5,5,5,5], dense=24,
        lr=3e-4, dropout=0.45, l2=1e-4, batch=32, epochs=200, cw={0:1.0,1:1.2},
        thr_score=lambda r,f: r*1.5 - f*2.0,
        note="V22 arch tuned: D24 + dropout=0.45 + batch=32",
    ),
    67: dict(
        filters=[32,48,64,96], kernels=[5,5,5,5], dense=32,
        lr=3e-4, dropout=0.5, l2=1e-4, batch=32, epochs=200, cw={0:1.0,1:1.2},
        thr_score=lambda r,f: r*1.5 - f*2.5,
        note="Max regularize: D32 + dropout=0.5 + batch=32 + FAR penalty×2.5",
    ),
    68: dict(
        filters=[32,48,64,96], kernels=[5,5,5,5], dense=20,
        lr=1e-4, dropout=0.4, l2=1e-4, batch=32, epochs=200, cw={0:1.0,1:1.2},
        thr_score=lambda r,f: r*1.5 - f*2.0,
        note="V58+V59 combo: LR=1e-4 + batch=32",
    ),
    69: dict(
        filters=[32,48,64,96], kernels=[5,5,5,5], dense=32,
        lr=3e-4, dropout=0.4, l2=5e-4, batch=32, epochs=200, cw={0:1.0,1:1.2},
        thr_score=lambda r,f: r*1.5 - f*2.0,
        note="V54+V59+V57 combo: D32 + batch=32 + L2=5e-4",
    ),
    70: dict(
        filters=[16,32,48,64,96], kernels=[5,5,5,5,5], dense=24,
        lr=3e-4, dropout=0.4, l2=1e-4, batch=32, epochs=200, cw={0:1.0,1:1.2},
        thr_score=lambda r,f: r*1.5 - f*2.0,
        note="5 conv layers [16,32,48,64,96]/K5 — novel depth + batch=32",
    ),
}

# ─────────────────────────────────────────────────────────────────────────────
def build_windows(df, label, ws=100, stride=50):
    data = df[['ax','ay','az','gx','gy','gz']].values
    wins, labs = [], []
    for i in range(0, len(data)-ws+1, stride):
        wins.append(data[i:i+ws]); labs.append(label)
    return np.array(wins), np.array(labs)

def load_data(seed):
    fx, fy = build_windows(pd.read_csv(DATA_DIR/"fall.csv"),     1)
    nx, ny = build_windows(pd.read_csv(DATA_DIR/"non_fall.csv"), 0)
    np.random.seed(seed)
    n  = min(len(fy), len(ny))
    fi = np.random.choice(len(fy), n, replace=False)
    ni = np.random.choice(len(ny), n, replace=False)
    X  = np.concatenate([fx[fi], nx[ni]])
    y  = np.concatenate([fy[fi], ny[ni]])
    tr_x, tmp_x, tr_y, tmp_y = train_test_split(X, y, test_size=0.30, stratify=y, random_state=seed)
    va_x, te_x, va_y, te_y   = train_test_split(tmp_x, tmp_y, test_size=0.50, stratify=tmp_y, random_state=seed)
    return tr_x, va_x, te_x, tr_y, va_y, te_y

def build_model(cfg):
    reg = tf.keras.regularizers.l2(cfg['l2'])
    inp = tf.keras.Input(shape=(100,6))
    x   = tf.keras.layers.Normalization(axis=-1)(inp)
    for i,(f,k) in enumerate(zip(cfg['filters'], cfg['kernels'])):
        x = tf.keras.layers.Conv1D(f, k, padding='same', kernel_regularizer=reg)(x)
        x = tf.keras.layers.BatchNormalization()(x)
        x = tf.keras.layers.Activation('relu')(x)
        if i < len(cfg['filters'])-1:
            x = tf.keras.layers.MaxPooling1D(2)(x)
    x   = tf.keras.layers.GlobalAveragePooling1D()(x)
    x   = tf.keras.layers.Dropout(cfg['dropout'])(x)
    x   = tf.keras.layers.Dense(cfg['dense'], activation='relu', kernel_regularizer=reg)(x)
    out = tf.keras.layers.Dense(1, activation='sigmoid')(x)
    m   = tf.keras.Model(inp, out)
    m.compile(optimizer=tf.keras.optimizers.Adam(cfg['lr']),
              loss='binary_crossentropy', metrics=['accuracy'])
    return m

def export_tflite(model, tr_x, models_dir, v):
    def rep():
        for _ in range(200):
            yield [tr_x[np.random.randint(len(tr_x))][np.newaxis].astype(np.float32)]
    c = tf.lite.TFLiteConverter.from_keras_model(model)
    c.optimizations = [tf.lite.Optimize.DEFAULT]
    c.representative_dataset = rep
    c.target_spec.supported_ops = [tf.lite.OpsSet.TFLITE_BUILTINS_INT8]
    c.inference_input_type  = tf.int8
    c.inference_output_type = tf.int8
    tflite = c.convert()
    (models_dir/f"fall_detection_v{v}.tflite").write_bytes(tflite)
    tokens = [f"0x{b:02x}" for b in tflite]
    lines  = [", ".join(tokens[i:i+12]) for i in range(0, len(tokens), 12)]
    header = (f"#ifndef FALL_DETECTION_V{v}_H\n#define FALL_DETECTION_V{v}_H\n\n"
              f"const unsigned char fall_detection_model_tflite[] = {{\n  "
              + ",\n  ".join(lines)
              + f"\n}};\nconst unsigned int fall_detection_model_tflite_len = {len(tflite)};\n\n"
              f"#endif // FALL_DETECTION_V{v}_H\n")
    (models_dir/f"fall_detection_v{v}.h").write_text(header)
    return len(tflite)/1024

def make_plots(v, hist, cm, te_probs, te_x, te_y, df_thr, best_thr, res_dir):
    fig,ax = plt.subplots(1,2,figsize=(12,4))
    ax[0].plot(hist.history['loss'],label='Train'); ax[0].plot(hist.history['val_loss'],label='Val')
    ax[0].set_title(f'V{v} Loss'); ax[0].legend()
    ax[1].plot(hist.history['accuracy'],label='Train'); ax[1].plot(hist.history['val_accuracy'],label='Val')
    ax[1].set_title(f'V{v} Acc'); ax[1].legend()
    plt.tight_layout(); plt.savefig(res_dir/"training_curves.png",dpi=150); plt.close()

    plt.figure(figsize=(6,5)); plt.imshow(cm,cmap='Blues')
    plt.title(f'V{v} Confusion Matrix (thr={best_thr:.2f})')
    for i in range(2):
        for j in range(2): plt.text(j,i,str(cm[i,j]),ha='center',va='center',fontsize=14)
    plt.xticks([0,1],['Non-Fall','Fall']); plt.yticks([0,1],['Non-Fall','Fall'])
    plt.savefig(res_dir/"confusion_matrix.png",dpi=150); plt.close()

    plt.figure(figsize=(10,5))
    plt.plot(df_thr['threshold'],df_thr['recall'],label='Recall')
    plt.plot(df_thr['threshold'],df_thr['far'],label='FAR')
    plt.axvline(best_thr,color='r',ls='--',label=f'thr={best_thr:.2f}')
    plt.title(f'V{v} Decision Analysis'); plt.legend()
    plt.savefig(res_dir/"decision_analysis.png",dpi=150); plt.close()

    fpr,tpr,_ = roc_curve(te_y,te_probs); rauc=auc(fpr,tpr)
    plt.figure(figsize=(6,5)); plt.plot(fpr,tpr,label=f'AUC={rauc:.3f}'); plt.plot([0,1],[0,1],'k--')
    plt.title(f'V{v} ROC'); plt.legend(); plt.savefig(res_dir/"roc_curve.png",dpi=150); plt.close()

    tp=(te_probs>=best_thr).astype(int)
    fn_i=np.where((tp==0)&(te_y==1))[0]; fp_i=np.where((tp==1)&(te_y==0))[0]
    fig,ax=plt.subplots(1,2,figsize=(12,5))
    if len(fn_i): ax[0].plot(te_x[fn_i[0]]); ax[0].set_title('False Negative')
    if len(fp_i): ax[1].plot(te_x[fp_i[0]]); ax[1].set_title('False Positive')
    plt.tight_layout(); plt.savefig(res_dir/"error_analysis.png",dpi=150); plt.close()

    fig=plt.figure(figsize=(15,10)); fig.suptitle(f'V{v} Dashboard',fontsize=18)
    a1=fig.add_subplot(2,2,1); a1.plot(hist.history['loss']); a1.set_title('Loss')
    a2=fig.add_subplot(2,2,2); a2.imshow(cm,cmap='Blues')
    for i in range(2):
        for j in range(2): a2.text(j,i,str(cm[i,j]),ha='center',va='center')
    a2.set_title('Confusion Matrix')
    a3=fig.add_subplot(2,2,3)
    a3.plot(df_thr['threshold'],df_thr['recall'],label='Recall')
    a3.plot(df_thr['threshold'],df_thr['far'],label='FAR')
    a3.axvline(best_thr,color='r',ls='--'); a3.set_title('Threshold'); a3.legend()
    a4=fig.add_subplot(2,2,4)
    a4.bar(['Fall','Non-Fall'],[int(np.sum(te_y==1)),int(np.sum(te_y==0))],color=['tomato','steelblue'])
    a4.set_title('Test Distribution')
    plt.tight_layout(rect=[0,0.03,1,0.95])
    plt.savefig(res_dir/"dashboard.png",dpi=200); plt.close()

def run_version(v, cfg):
    print(f"\n{'='*24} V{v} {'='*24}")
    print(f"  {cfg['note']}")
    out = AI_DIR/f"model_updated_version_{v}"
    md  = out/"models"; rd = out/"results"; dd = out/"docs"
    for d in [md,rd,dd]: d.mkdir(parents=True,exist_ok=True)

    seed = v*100
    tf.random.set_seed(seed)
    tr_x,va_x,te_x,tr_y,va_y,te_y = load_data(seed)

    model = build_model(cfg)
    model.layers[1].adapt(tr_x)

    cbs = [
        tf.keras.callbacks.EarlyStopping(patience=25, restore_best_weights=True, monitor='val_loss'),
        tf.keras.callbacks.ReduceLROnPlateau(factor=0.2, patience=10, min_lr=1e-7),
    ]
    hist = model.fit(tr_x, tr_y, validation_data=(va_x,va_y),
                     epochs=cfg['epochs'], batch_size=cfg['batch'],
                     callbacks=cbs, class_weight=cfg['cw'], verbose=0)

    va_probs = model.predict(va_x,verbose=0).reshape(-1)
    best_thr,best_score = 0.5,-1
    rows=[]
    for thr in np.arange(0.05,0.95,0.01):
        p   = (va_probs>=thr).astype(int)
        rec = recall_score(va_y,p,zero_division=0)
        f1  = f1_score(va_y,p,zero_division=0)
        cv  = confusion_matrix(va_y,p); tn,fp,_,_ = cv.ravel()
        far = fp/(fp+tn) if (fp+tn)>0 else 0
        sc  = cfg['thr_score'](rec,far)
        rows.append({"threshold":round(float(thr),2),"recall":rec,"far":far,"f1":f1})
        if sc>best_score: best_score,best_thr = sc,float(thr)
    df_thr = pd.DataFrame(rows)
    df_thr.to_csv(rd/"threshold_metrics.csv",index=False)

    te_probs = model.predict(te_x,verbose=0).reshape(-1)
    te_preds = (te_probs>=best_thr).astype(int)
    cm       = confusion_matrix(te_y,te_preds)
    tn,fp,fn,tp = cm.ravel()
    m = {
        "version":v,
        "accuracy":         float(accuracy_score(te_y,te_preds)),
        "precision":        float(precision_score(te_y,te_preds,zero_division=0)),
        "recall":           float(recall_score(te_y,te_preds,zero_division=0)),
        "f1":               float(f1_score(te_y,te_preds,zero_division=0)),
        "false_alarm_rate": float(fp/(fp+tn)) if (fp+tn)>0 else 0,
        "miss_rate":        float(fn/(fn+tp)) if (fn+tp)>0 else 0,
        "best_threshold":   best_thr,
        "config": {k:str(v2) for k,v2 in cfg.items() if k!='thr_score'},
    }
    (rd/f"metrics_v{v}.json").write_text(json.dumps(m,indent=2))

    md_txt = (f"# Model V{v}: {cfg['note']}\n\n"
              f"| Metric | Value |\n| :--- | :--- |\n"
              f"| Accuracy | **{m['accuracy']*100:.2f}%** |\n"
              f"| Recall   | **{m['recall']*100:.2f}%** |\n"
              f"| Precision| **{m['precision']*100:.2f}%** |\n"
              f"| F1-score | **{m['f1']*100:.2f}%** |\n"
              f"| FAR      | **{m['false_alarm_rate']*100:.2f}%** |\n"
              f"| Miss Rate| **{m['miss_rate']*100:.2f}%** |\n")
    (rd/f"metrics_v{v}.md").write_text(md_txt)
    (rd/"metrics_summary.txt").write_text(
        f"Accuracy:  {m['accuracy']:.4f}\nRecall:    {m['recall']:.4f}\n"
        f"Precision: {m['precision']:.4f}\nF1:        {m['f1']:.4f}\n"
        f"FAR:       {m['false_alarm_rate']:.4f}\nMissRate:  {m['miss_rate']:.4f}\n"
        f"Threshold: {best_thr:.2f}\n")

    make_plots(v, hist, cm, te_probs, te_x, te_y, df_thr, best_thr, rd)
    size_kb = export_tflite(model, tr_x, md, v)
    m['size_kb'] = size_kb

    report = (f"# Experiment Report — V{v}\n\n## Config\n"
              f"- Arch: {len(cfg['filters'])}×Conv1D {cfg['filters']}, K={cfg['kernels']}, Dense={cfg['dense']}\n"
              f"- LR={cfg['lr']} | Dropout={cfg['dropout']} | L2={cfg['l2']} | Batch={cfg['batch']}\n"
              f"- Class weight: {cfg['cw']}\n- Note: {cfg['note']}\n\n## Results\n"
              f"- Accuracy: {m['accuracy']:.4f}\n- Recall: {m['recall']:.4f}\n"
              f"- F1: {m['f1']:.4f}\n- FAR: {m['false_alarm_rate']:.4f}\n"
              f"- Size: {size_kb:.2f} KB | Threshold: {best_thr:.2f}\n")
    (dd/"experiment_report.md").write_text(report)

    readme = (f"# Model V{v}\n\n**{cfg['note']}**\n\n"
              f"| Metric | Value |\n|---|---|\n"
              f"| F1 | {m['f1']*100:.2f}% |\n| Recall | {m['recall']*100:.2f}% |\n"
              f"| FAR | {m['false_alarm_rate']*100:.2f}% |\n| Size | {size_kb:.2f} KB |\n\n"
              f"## Deploy\nplatformio.ini: `-I ../AI/model_updated_version_{v}/models`\n"
              f"main.cpp: `#include \"fall_detection_v{v}.h\"`\n")
    (out/"README.md").write_text(readme)

    print(f"  V{v}: Acc={m['accuracy']:.4f} Rec={m['recall']:.4f} "
          f"F1={m['f1']:.4f} FAR={m['false_alarm_rate']:.4f} Size={size_kb:.2f}KB")
    return m

# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    all_results = []
    for v in sorted(VERSIONS):
        try:
            all_results.append(run_version(v, VERSIONS[v]))
        except Exception as e:
            print(f"  ERROR V{v}: {e}")
            import traceback; traceback.print_exc()

    print("\n" + "="*60)
    print(f"{'V':<6} {'Acc':>7} {'Recall':>8} {'F1':>8} {'FAR':>8} {'Size':>8}")
    for m in all_results:
        print(f"V{m['version']:<5} {m['accuracy']*100:>6.2f}% {m['recall']*100:>7.2f}% "
              f"{m['f1']*100:>7.2f}% {m['false_alarm_rate']*100:>7.2f}% {m['size_kb']:>7.2f}KB")

    # Append to experiments_summary.md
    summary_path = AI_DIR/"experiments_summary.md"
    existing = summary_path.read_text()
    new_section = "\n## V61-V70 Results\n\n"
    new_section += "| Version | Note | Accuracy | Recall | F1 | FAR | Size |\n"
    new_section += "| :--- | :--- | :--- | :--- | :--- | :--- | :--- |\n"
    for m in all_results:
        new_section += (f"| **V{m['version']}** | {VERSIONS[m['version']]['note'][:45]} "
                        f"| {m['accuracy']*100:.2f}% | {m['recall']*100:.2f}% "
                        f"| {m['f1']*100:.2f}% | {m['false_alarm_rate']*100:.2f}% "
                        f"| {m['size_kb']:.2f} KB |\n")
    if "## V61-V70 Results" in existing:
        idx = existing.index("## V61-V70 Results")
        updated = existing[:idx] + new_section
    else:
        updated = existing + new_section
    summary_path.write_text(updated)
    print(f"\nUpdated {summary_path}")
