"""
Train V81-V90 — fix overfitting observed in V80.

V80 problem: train loss ↓ steadily, val loss plateaus at epoch ~30 with oscillations.
Root cause: model memorizes training data instead of generalizing.

Strategy per version:
───────────────────────────────────────────────────────────────────────
V81: patience=10 (user suggestion) — baseline test, may stop mid-oscillation
V82: patience=20 + ReduceLROnPlateau(factor=0.1, patience=5) — aggressive LR drop
V83: V80 + Dropout=0.5 + L2=5e-4 — strong regularization
V84: V80 + Gaussian noise augmentation σ=0.05 — fix overfitting at root
V85: V80 + cosine decay LR schedule — smooth convergence, no oscillation
V86: V80 + augmentation σ=0.05 + L2=5e-4 — two strongest fixes combined
V87: patience=10 + augmentation σ=0.05 — user idea + root fix
V88: V80 + Dropout=0.45 + factor=0.1 patience=5 LR — tuned regularize + LR
V89: V80 + augmentation σ=0.10 (stronger noise)
V90: Best combo: Dropout=0.45 + L2=5e-4 + aug σ=0.05 + factor=0.1 patience=5 + patience=20
───────────────────────────────────────────────────────────────────────
All use V80 architecture: [32,64,64,96]/K3/D32 + batch=32 + L2=3e-4 (base)
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
    confusion_matrix, roc_curve, auc
)

BASE_DIR = Path("/home/zinex/CAPSTONE/AI/edge-aiot-wearable-elderly-safety-monitoring")
DATA_DIR = BASE_DIR / "AI/Edge_AI/result_balanced_v2/dataset/rebuilt"
AI_DIR   = BASE_DIR / "AI"

# ─── Version configs ──────────────────────────────────────────────────────────
# Base V80: [32,64,64,96]/K3/D32, LR=3e-4, drop=0.4, L2=3e-4, batch=32, cw=1.2
VERSIONS = {
    81: dict(
        filters=[32,64,64,96], kernels=[3,3,3,3], dense=32,
        lr=3e-4, dropout=0.4, l2=3e-4, batch=32, epochs=200,
        cw={0:1.0,1:1.2}, aug_sigma=0.0,
        es_patience=10, lr_factor=0.2, lr_patience=10,
        thr_score=lambda r,f: r*1.5 - f*2.0,
        note="patience=10 — user suggestion, baseline test",
    ),
    82: dict(
        filters=[32,64,64,96], kernels=[3,3,3,3], dense=32,
        lr=3e-4, dropout=0.4, l2=3e-4, batch=32, epochs=300,
        cw={0:1.0,1:1.2}, aug_sigma=0.0,
        es_patience=20, lr_factor=0.1, lr_patience=5,
        thr_score=lambda r,f: r*1.5 - f*2.0,
        note="patience=20 + ReduceLR(factor=0.1, patience=5) — aggressive LR",
    ),
    83: dict(
        filters=[32,64,64,96], kernels=[3,3,3,3], dense=32,
        lr=3e-4, dropout=0.5, l2=5e-4, batch=32, epochs=300,
        cw={0:1.0,1:1.2}, aug_sigma=0.0,
        es_patience=25, lr_factor=0.2, lr_patience=10,
        thr_score=lambda r,f: r*1.5 - f*2.0,
        note="Dropout=0.5 + L2=5e-4 — strong regularization",
    ),
    84: dict(
        filters=[32,64,64,96], kernels=[3,3,3,3], dense=32,
        lr=3e-4, dropout=0.4, l2=3e-4, batch=32, epochs=300,
        cw={0:1.0,1:1.2}, aug_sigma=0.05,
        es_patience=25, lr_factor=0.2, lr_patience=10,
        thr_score=lambda r,f: r*1.5 - f*2.0,
        note="Gaussian noise aug σ=0.05 — fix overfitting at root",
    ),
    85: dict(
        filters=[32,64,64,96], kernels=[3,3,3,3], dense=32,
        lr=3e-4, dropout=0.4, l2=3e-4, batch=32, epochs=300,
        cw={0:1.0,1:1.2}, aug_sigma=0.0,
        es_patience=25, lr_factor=0.2, lr_patience=10,
        use_cosine=True,
        thr_score=lambda r,f: r*1.5 - f*2.0,
        note="Cosine decay LR — smooth convergence, no oscillation",
    ),
    86: dict(
        filters=[32,64,64,96], kernels=[3,3,3,3], dense=32,
        lr=3e-4, dropout=0.4, l2=5e-4, batch=32, epochs=300,
        cw={0:1.0,1:1.2}, aug_sigma=0.05,
        es_patience=25, lr_factor=0.1, lr_patience=5,
        thr_score=lambda r,f: r*1.5 - f*2.0,
        note="aug σ=0.05 + L2=5e-4 + LR aggressive — two strongest fixes",
    ),
    87: dict(
        filters=[32,64,64,96], kernels=[3,3,3,3], dense=32,
        lr=3e-4, dropout=0.4, l2=3e-4, batch=32, epochs=300,
        cw={0:1.0,1:1.2}, aug_sigma=0.05,
        es_patience=10, lr_factor=0.2, lr_patience=10,
        thr_score=lambda r,f: r*1.5 - f*2.0,
        note="patience=10 + aug σ=0.05 — user idea + root fix combined",
    ),
    88: dict(
        filters=[32,64,64,96], kernels=[3,3,3,3], dense=32,
        lr=3e-4, dropout=0.45, l2=3e-4, batch=32, epochs=300,
        cw={0:1.0,1:1.2}, aug_sigma=0.0,
        es_patience=20, lr_factor=0.1, lr_patience=5,
        thr_score=lambda r,f: r*1.5 - f*2.0,
        note="Dropout=0.45 + aggressive LR(factor=0.1, p=5) — tuned regularize",
    ),
    89: dict(
        filters=[32,64,64,96], kernels=[3,3,3,3], dense=32,
        lr=3e-4, dropout=0.4, l2=3e-4, batch=32, epochs=300,
        cw={0:1.0,1:1.2}, aug_sigma=0.10,
        es_patience=25, lr_factor=0.2, lr_patience=10,
        thr_score=lambda r,f: r*1.5 - f*2.0,
        note="Gaussian noise aug σ=0.10 — stronger augmentation",
    ),
    90: dict(
        filters=[32,64,64,96], kernels=[3,3,3,3], dense=32,
        lr=3e-4, dropout=0.45, l2=5e-4, batch=32, epochs=300,
        cw={0:1.0,1:1.2}, aug_sigma=0.05,
        es_patience=20, lr_factor=0.1, lr_patience=5,
        thr_score=lambda r,f: r*1.5 - f*2.0,
        note="BEST COMBO: drop=0.45+L2=5e-4+aug0.05+LR_aggr+p=20",
    ),
}

# ─── Data ────────────────────────────────────────────────────────────────────
def build_windows(df, label, ws=100, stride=50):
    data = df[['ax','ay','az','gx','gy','gz']].values
    wins, labs = [], []
    for i in range(0, len(data)-ws+1, stride):
        wins.append(data[i:i+ws]); labs.append(label)
    return np.array(wins), np.array(labs)

def load_data(seed):
    fx,fy = build_windows(pd.read_csv(DATA_DIR/"fall.csv"), 1)
    nx,ny = build_windows(pd.read_csv(DATA_DIR/"non_fall.csv"), 0)
    np.random.seed(seed)
    n  = min(len(fy), len(ny))
    fi = np.random.choice(len(fy), n, replace=False)
    ni = np.random.choice(len(ny), n, replace=False)
    X  = np.concatenate([fx[fi], nx[ni]])
    y  = np.concatenate([fy[fi], ny[ni]])
    tr_x,tmp_x,tr_y,tmp_y = train_test_split(X,y,test_size=0.30,stratify=y,random_state=seed)
    va_x,te_x,va_y,te_y   = train_test_split(tmp_x,tmp_y,test_size=0.50,stratify=tmp_y,random_state=seed)
    return tr_x,va_x,te_x,tr_y,va_y,te_y

# ─── Augmentation ────────────────────────────────────────────────────────────
class GaussianNoiseDataset:
    """Wrap training data with random Gaussian noise per batch."""
    def __init__(self, X, y, batch_size, sigma, class_weight):
        self.X = X; self.y = y
        self.batch_size = batch_size; self.sigma = sigma
        self.cw = class_weight

    def as_tf_dataset(self):
        ds = tf.data.Dataset.from_tensor_slices((self.X.astype(np.float32),
                                                  self.y.astype(np.float32)))
        def add_noise(x, y):
            noise = tf.random.normal(tf.shape(x), stddev=self.sigma)
            return x + noise, y
        ds = ds.shuffle(len(self.X)).batch(self.batch_size)
        if self.sigma > 0:
            ds = ds.map(add_noise, num_parallel_calls=tf.data.AUTOTUNE)
        return ds.prefetch(tf.data.AUTOTUNE)

# ─── Model ───────────────────────────────────────────────────────────────────
def build_model(cfg):
    reg = tf.keras.regularizers.l2(cfg['l2'])
    inp = tf.keras.Input(shape=(100,6))
    x   = tf.keras.layers.Normalization(axis=-1)(inp)
    for i,(f,k) in enumerate(zip(cfg['filters'],cfg['kernels'])):
        x = tf.keras.layers.Conv1D(f,k,padding='same',kernel_regularizer=reg)(x)
        x = tf.keras.layers.BatchNormalization()(x)
        x = tf.keras.layers.Activation('relu')(x)
        if i < len(cfg['filters'])-1:
            x = tf.keras.layers.MaxPooling1D(2)(x)
    x   = tf.keras.layers.GlobalAveragePooling1D()(x)
    x   = tf.keras.layers.Dropout(cfg['dropout'])(x)
    x   = tf.keras.layers.Dense(cfg['dense'],activation='relu',kernel_regularizer=reg)(x)
    out = tf.keras.layers.Dense(1,activation='sigmoid')(x)
    m   = tf.keras.Model(inp,out)
    m.compile(optimizer=tf.keras.optimizers.Adam(cfg['lr']),
              loss='binary_crossentropy', metrics=['accuracy'])
    return m

# ─── LR schedule (cosine decay) ───────────────────────────────────────────
def cosine_lr_schedule(epoch, total_epochs=300, lr_max=3e-4, lr_min=1e-7):
    return lr_min + 0.5*(lr_max - lr_min)*(1 + np.cos(np.pi * epoch / total_epochs))

# ─── Export ──────────────────────────────────────────────────────────────────
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
    lines  = [", ".join(tokens[i:i+12]) for i in range(0,len(tokens),12)]
    (models_dir/f"fall_detection_v{v}.h").write_text(
        f"#ifndef FALL_DETECTION_V{v}_H\n#define FALL_DETECTION_V{v}_H\n\n"
        f"const unsigned char fall_detection_model_tflite[] = {{\n  "
        + ",\n  ".join(lines)
        + f"\n}};\nconst unsigned int fall_detection_model_tflite_len = {len(tflite)};\n\n"
        f"#endif // FALL_DETECTION_V{v}_H\n")
    return len(tflite)/1024

# ─── Plots ───────────────────────────────────────────────────────────────────
def make_plots(v, hist, cm, te_probs, te_x, te_y, df_thr, thr, rd):
    fig,ax=plt.subplots(1,2,figsize=(12,4))
    ax[0].plot(hist.history['loss'],label='Train'); ax[0].plot(hist.history['val_loss'],label='Val')
    ax[0].set_title(f'V{v} Loss'); ax[0].legend()
    ax[1].plot(hist.history['accuracy'],label='Train'); ax[1].plot(hist.history['val_accuracy'],label='Val')
    ax[1].set_title(f'V{v} Accuracy'); ax[1].legend()
    plt.tight_layout(); plt.savefig(rd/"training_curves.png",dpi=150); plt.close()

    plt.figure(figsize=(6,5)); plt.imshow(cm,cmap='Blues')
    plt.title(f'V{v} CM (thr={thr:.2f})')
    for i in range(2):
        for j in range(2): plt.text(j,i,str(cm[i,j]),ha='center',va='center',fontsize=14)
    plt.xticks([0,1],['Non-Fall','Fall']); plt.yticks([0,1],['Non-Fall','Fall'])
    plt.savefig(rd/"confusion_matrix.png",dpi=150); plt.close()

    plt.figure(figsize=(10,5))
    plt.plot(df_thr['threshold'],df_thr['recall'],label='Recall')
    plt.plot(df_thr['threshold'],df_thr['far'],label='FAR')
    plt.axvline(thr,color='r',ls='--',label=f'thr={thr:.2f}')
    plt.title(f'V{v} Decision Analysis'); plt.legend()
    plt.savefig(rd/"decision_analysis.png",dpi=150); plt.close()

    fpr,tpr,_=roc_curve(te_y,te_probs); rauc=auc(fpr,tpr)
    plt.figure(figsize=(6,5)); plt.plot(fpr,tpr,label=f'AUC={rauc:.3f}'); plt.plot([0,1],[0,1],'k--')
    plt.title(f'V{v} ROC'); plt.legend(); plt.savefig(rd/"roc_curve.png",dpi=150); plt.close()

    tp_arr=(te_probs>=thr).astype(int)
    fn_i=np.where((tp_arr==0)&(te_y==1))[0]; fp_i=np.where((tp_arr==1)&(te_y==0))[0]
    fig,ax=plt.subplots(1,2,figsize=(12,5))
    if len(fn_i): ax[0].plot(te_x[fn_i[0]]); ax[0].set_title('False Negative sample')
    if len(fp_i): ax[1].plot(te_x[fp_i[0]]); ax[1].set_title('False Positive sample')
    plt.tight_layout(); plt.savefig(rd/"error_analysis.png",dpi=150); plt.close()

    fig=plt.figure(figsize=(15,10)); fig.suptitle(f'V{v} Dashboard',fontsize=18)
    a1=fig.add_subplot(2,2,1)
    a1.plot(hist.history['loss'],label='Train Loss'); a1.plot(hist.history['val_loss'],label='Val Loss')
    final_gap = abs(hist.history['loss'][-1] - hist.history['val_loss'][-1])
    gap_label = f'Loss (gap={final_gap:.3f} {"⚠ overfit" if final_gap > 0.08 else "✓ ok"})'
    a1.set_title(gap_label); a1.legend()
    a2=fig.add_subplot(2,2,2); a2.imshow(cm,cmap='Blues'); a2.set_title('Confusion Matrix')
    for i in range(2):
        for j in range(2): a2.text(j,i,str(cm[i,j]),ha='center',va='center')
    a3=fig.add_subplot(2,2,3)
    a3.plot(df_thr['threshold'],df_thr['recall'],label='Recall')
    a3.plot(df_thr['threshold'],df_thr['far'],label='FAR')
    a3.axvline(thr,color='r',ls='--'); a3.set_title('Threshold'); a3.legend()
    a4=fig.add_subplot(2,2,4)
    a4.bar(['Fall','Non-Fall'],[int(np.sum(te_y==1)),int(np.sum(te_y==0))],color=['tomato','steelblue'])
    a4.set_title('Test Distribution')
    plt.tight_layout(rect=[0,0.03,1,0.95]); plt.savefig(rd/"dashboard.png",dpi=200); plt.close()

# ─── Run one version ─────────────────────────────────────────────────────────
def run_version(v, cfg):
    print(f"\n{'='*24} V{v} {'='*24}")
    print(f"  {cfg['note']}")
    out=AI_DIR/f"model_updated_version_{v}"
    md=out/"models"; rd=out/"results"; dd=out/"docs"
    for d in [md,rd,dd]: d.mkdir(parents=True,exist_ok=True)

    seed=v*100; tf.random.set_seed(seed)
    tr_x,va_x,te_x,tr_y,va_y,te_y = load_data(seed)

    model = build_model(cfg)
    model.layers[1].adapt(tr_x)

    # Callbacks
    cbs = [
        tf.keras.callbacks.EarlyStopping(
            patience=cfg['es_patience'],
            restore_best_weights=True,
            monitor='val_loss'),
        tf.keras.callbacks.ReduceLROnPlateau(
            factor=cfg['lr_factor'],
            patience=cfg['lr_patience'],
            min_lr=1e-8,
            monitor='val_loss'),
    ]
    if cfg.get('use_cosine', False):
        cbs.append(tf.keras.callbacks.LearningRateScheduler(
            lambda ep: cosine_lr_schedule(ep, cfg['epochs'])))

    # Training — with or without augmentation
    sigma = cfg.get('aug_sigma', 0.0)
    if sigma > 0:
        train_ds = GaussianNoiseDataset(tr_x, tr_y, cfg['batch'], sigma, cfg['cw']).as_tf_dataset()
        hist = model.fit(
            train_ds,
            validation_data=(va_x, va_y),
            epochs=cfg['epochs'],
            callbacks=cbs,
            class_weight=cfg['cw'],
            verbose=0)
    else:
        hist = model.fit(
            tr_x, tr_y,
            validation_data=(va_x, va_y),
            epochs=cfg['epochs'],
            batch_size=cfg['batch'],
            callbacks=cbs,
            class_weight=cfg['cw'],
            verbose=0)

    best_epoch = len(hist.history['val_loss']) - cfg['es_patience']
    print(f"  Stopped at epoch {len(hist.history['val_loss'])} (best ~ep {max(1,best_epoch)})")

    # Threshold tuning
    va_probs=model.predict(va_x,verbose=0).reshape(-1)
    best_thr,best_score=0.5,-1; rows=[]
    for thr in np.arange(0.05,0.95,0.01):
        p=( va_probs>=thr).astype(int)
        rec=recall_score(va_y,p,zero_division=0)
        f1 =f1_score(va_y,p,zero_division=0)
        cv =confusion_matrix(va_y,p); tn,fp,_,_=cv.ravel()
        far=fp/(fp+tn) if (fp+tn)>0 else 0
        rows.append({"threshold":round(float(thr),2),"recall":rec,"far":far,"f1":f1})
        sc=cfg['thr_score'](rec,far)
        if sc>best_score: best_score,best_thr=sc,float(thr)
    df_thr=pd.DataFrame(rows)
    df_thr.to_csv(rd/"threshold_metrics.csv",index=False)

    # Evaluate
    te_probs=model.predict(te_x,verbose=0).reshape(-1)
    te_preds=(te_probs>=best_thr).astype(int)
    cm=confusion_matrix(te_y,te_preds); tn,fp,fn,tp_c=cm.ravel()
    m={
        "version":v,
        "accuracy":         float(accuracy_score(te_y,te_preds)),
        "precision":        float(precision_score(te_y,te_preds,zero_division=0)),
        "recall":           float(recall_score(te_y,te_preds,zero_division=0)),
        "f1":               float(f1_score(te_y,te_preds,zero_division=0)),
        "false_alarm_rate": float(fp/(fp+tn)) if (fp+tn)>0 else 0,
        "miss_rate":        float(fn/(fn+tp_c)) if (fn+tp_c)>0 else 0,
        "best_threshold":   best_thr,
        "stopped_epoch":    len(hist.history['val_loss']),
        "config":{k:str(v2) for k,v2 in cfg.items() if k!='thr_score'},
    }
    (rd/f"metrics_v{v}.json").write_text(json.dumps(m,indent=2))
    (rd/f"metrics_v{v}.md").write_text(
        f"# V{v}: {cfg['note']}\n\n"
        f"| Metric | Value |\n| :--- | :--- |\n"
        f"| Accuracy  | **{m['accuracy']*100:.2f}%** |\n"
        f"| Recall    | **{m['recall']*100:.2f}%** |\n"
        f"| Precision | **{m['precision']*100:.2f}%** |\n"
        f"| F1-score  | **{m['f1']*100:.2f}%** |\n"
        f"| FAR       | **{m['false_alarm_rate']*100:.2f}%** |\n"
        f"| Miss Rate | **{m['miss_rate']*100:.2f}%** |\n"
        f"| Stopped epoch | {m['stopped_epoch']} |\n")
    (rd/"metrics_summary.txt").write_text(
        f"Accuracy:  {m['accuracy']:.4f}\nRecall:    {m['recall']:.4f}\n"
        f"Precision: {m['precision']:.4f}\nF1:        {m['f1']:.4f}\n"
        f"FAR:       {m['false_alarm_rate']:.4f}\nMissRate:  {m['miss_rate']:.4f}\n"
        f"Threshold: {best_thr:.2f}\nEpoch:     {m['stopped_epoch']}\n")

    make_plots(v,hist,cm,te_probs,te_x,te_y,df_thr,best_thr,rd)
    size_kb=export_tflite(model,tr_x,md,v)
    m['size_kb']=size_kb

    val_gap = hist.history['loss'][-1] - hist.history['val_loss'][-1]
    (dd/"experiment_report.md").write_text(
        f"# Experiment Report — V{v}\n\n## Config\n"
        f"- Arch: [32,64,64,96]/K3/D32 + batch={cfg['batch']}\n"
        f"- LR={cfg['lr']} | Dropout={cfg['dropout']} | L2={cfg['l2']}\n"
        f"- EarlyStopping patience={cfg['es_patience']} | ReduceLR factor={cfg['lr_factor']} patience={cfg['lr_patience']}\n"
        f"- Augmentation sigma={cfg.get('aug_sigma',0)} | Cosine LR={cfg.get('use_cosine',False)}\n"
        f"- Note: {cfg['note']}\n\n## Results\n"
        f"- F1: {m['f1']:.4f} | Recall: {m['recall']:.4f} | FAR: {m['false_alarm_rate']:.4f}\n"
        f"- Accuracy: {m['accuracy']:.4f} | Size: {size_kb:.2f} KB | Threshold: {best_thr:.2f}\n"
        f"- Stopped at epoch: {m['stopped_epoch']}\n"
        f"- Train/Val loss gap (last epoch): {val_gap:.4f} "
        f"({'overfitting' if val_gap < -0.05 else 'ok'})\n")
    (out/"README.md").write_text(
        f"# Model V{v}\n\n**{cfg['note']}**\n\n"
        f"| Metric | Value |\n|---|---|\n"
        f"| F1 | {m['f1']*100:.2f}% |\n| Recall | {m['recall']*100:.2f}% |\n"
        f"| FAR | {m['false_alarm_rate']*100:.2f}% |\n| Size | {size_kb:.2f} KB |\n\n"
        f"## Deploy\nplatformio.ini: `-I ../AI/model_updated_version_{v}/models`\n"
        f"main.cpp: `#include \"fall_detection_v{v}.h\"`\n")

    marker = " ← NEW BEST" if m['f1'] > 0.9338 else ""
    print(f"  V{v}: Acc={m['accuracy']:.4f} Rec={m['recall']:.4f} "
          f"F1={m['f1']:.4f} FAR={m['false_alarm_rate']:.4f} "
          f"Size={size_kb:.2f}KB ep={m['stopped_epoch']}{marker}")
    return m

# ─── Main ────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    all_results = []
    for v in sorted(VERSIONS):
        try:
            all_results.append(run_version(v, VERSIONS[v]))
        except Exception as e:
            print(f"  ERROR V{v}: {e}")
            import traceback; traceback.print_exc()

    print("\n" + "="*72)
    print(f"{'V':<6} {'Acc':>7} {'Recall':>8} {'F1':>8} {'FAR':>8} {'Size':>8} {'Epoch':>6}")
    print("-"*72)
    for m in all_results:
        marker = " ← BEST" if m['f1'] > 0.9338 else ""
        print(f"V{m['version']:<5} {m['accuracy']*100:>6.2f}% {m['recall']*100:>7.2f}% "
              f"{m['f1']*100:>7.2f}% {m['false_alarm_rate']*100:>7.2f}% "
              f"{m['size_kb']:>7.2f}KB {m['stopped_epoch']:>5}{marker}")

    # Update experiments_summary.md
    sp = AI_DIR/"experiments_summary.md"
    existing = sp.read_text()
    section  = "\n## V81-V90 Results (Overfitting Fix)\n\n"
    section += "| V | Strategy | Acc | Recall | F1 | FAR | Epoch |\n"
    section += "| :--- | :--- | :--- | :--- | :--- | :--- | :--- |\n"
    for m in all_results:
        section += (f"| **V{m['version']}** | {VERSIONS[m['version']]['note'][:45]} "
                    f"| {m['accuracy']*100:.2f}% | {m['recall']*100:.2f}% "
                    f"| {m['f1']*100:.2f}% | {m['false_alarm_rate']*100:.2f}% "
                    f"| {m['stopped_epoch']} |\n")
    tag = "## V81-V90 Results"
    sp.write_text(existing[:existing.index(tag)]+section if tag in existing else existing+section)

    # Update comparison file
    comp = AI_DIR/"model_comparison_v1_v80.md"
    new_rows = "\n## V81-V90 (Overfitting Fix)\n\n"
    new_rows += "| Version | Strategy | Acc | Recall | F1 | FAR | Miss | Size | Epoch |\n"
    new_rows += "| :--- | :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |\n"
    for m in all_results:
        cfg = VERSIONS[m['version']]
        new_rows += (f"| V{m['version']} | {cfg['note'][:40]} "
                     f"| {m['accuracy']*100:.2f}% | {m['recall']*100:.2f}% "
                     f"| {m['f1']*100:.2f}% | {m['false_alarm_rate']*100:.2f}% "
                     f"| {m['miss_rate']*100:.2f}% | {m['size_kb']:.2f}KB "
                     f"| {m['stopped_epoch']} |\n")
    comp_text = comp.read_text() + new_rows
    new_comp = AI_DIR/"model_comparison_v1_v90.md"
    new_comp.write_text(comp_text)
    comp.unlink()
    print(f"\nComparison table: {new_comp}")

    print("\nDone. Check dashboard.png of each version to verify train/val gap improved.")
