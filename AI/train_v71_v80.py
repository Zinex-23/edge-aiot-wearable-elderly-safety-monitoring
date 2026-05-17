"""
Train V71-V80 — designed to beat V64 (F1=93.17%, FAR=10.82%).

V64 baseline: [32,64,64,96]/K3/D32, LR=3e-4, drop=0.4, L2=1e-4, batch=32, cw=1.2
─────────────────────────────────────────────────────────────────────────────
V71: V64 + LR=1e-4          → finer convergence on proven arch
V72: V64 + batch=16         → smaller batch → better generalization + lower FAR
V73: [32,64,96,96]/K3/D32+batch=32  → V23 FAR-record arch (7.84%) + D32+batch=32
V74: [32,64,64,96]/K5/D32+batch=32  → V64 arch switched to K5
V75: V64 + dropout=0.3      → less regularization, more capacity for complex patterns
V76: V64 + cw={0:1.0,1:1.1} → less recall bias → FAR↓ while keeping Recall decent
V77: [32,48,64,96]/K5/D32+batch=32+LR=1e-4 → V54+V59+V58 all combined
V78: [32,64,64,128]/K3/D32+batch=32 → V64 with wider last conv filter (96→128)
V79: [32,64,64,96]/K3/D48+batch=32  → V64 with larger Dense (32→48)
V80: [32,64,64,96]/K3/D32+batch=32+L2=3e-4 → V64 + tuned L2 between 1e-4 and 5e-4
─────────────────────────────────────────────────────────────────────────────
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

VERSIONS = {
    71: dict(
        filters=[32,64,64,96], kernels=[3,3,3,3], dense=32,
        lr=1e-4, dropout=0.4, l2=1e-4, batch=32, epochs=250, cw={0:1.0,1:1.2},
        thr_score=lambda r,f: r*1.5 - f*2.0,
        note="V64 + LR=1e-4 (finer convergence on best arch)",
    ),
    72: dict(
        filters=[32,64,64,96], kernels=[3,3,3,3], dense=32,
        lr=3e-4, dropout=0.4, l2=1e-4, batch=16, epochs=200, cw={0:1.0,1:1.2},
        thr_score=lambda r,f: r*1.5 - f*2.0,
        note="V64 + batch=16 (smaller batch → better generalization)",
    ),
    73: dict(
        filters=[32,64,96,96], kernels=[3,3,3,3], dense=32,
        lr=3e-4, dropout=0.4, l2=1e-4, batch=32, epochs=200, cw={0:1.0,1:1.2},
        thr_score=lambda r,f: r*1.5 - f*2.0,
        note="V23 arch [32,64,96,96]/K3 + D32+batch=32 (V23 had FAR=7.84%)",
    ),
    74: dict(
        filters=[32,64,64,96], kernels=[5,5,5,5], dense=32,
        lr=3e-4, dropout=0.4, l2=1e-4, batch=32, epochs=200, cw={0:1.0,1:1.2},
        thr_score=lambda r,f: r*1.5 - f*2.0,
        note="V64 arch switched to K5 + D32 + batch=32",
    ),
    75: dict(
        filters=[32,64,64,96], kernels=[3,3,3,3], dense=32,
        lr=3e-4, dropout=0.3, l2=1e-4, batch=32, epochs=200, cw={0:1.0,1:1.2},
        thr_score=lambda r,f: r*1.5 - f*2.0,
        note="V64 + dropout=0.3 (less regularization, more capacity)",
    ),
    76: dict(
        filters=[32,64,64,96], kernels=[3,3,3,3], dense=32,
        lr=3e-4, dropout=0.4, l2=1e-4, batch=32, epochs=200, cw={0:1.0,1:1.1},
        thr_score=lambda r,f: r*1.5 - f*2.5,
        note="V64 + cw=1.1 + FAR penalty×2.5 (less recall bias → lower FAR)",
    ),
    77: dict(
        filters=[32,48,64,96], kernels=[5,5,5,5], dense=32,
        lr=1e-4, dropout=0.4, l2=1e-4, batch=32, epochs=250, cw={0:1.0,1:1.2},
        thr_score=lambda r,f: r*1.5 - f*2.0,
        note="V54+V59+V58: [32,48,64,96]/K5/D32 + batch=32 + LR=1e-4",
    ),
    78: dict(
        filters=[32,64,64,128], kernels=[3,3,3,3], dense=32,
        lr=3e-4, dropout=0.4, l2=1e-4, batch=32, epochs=200, cw={0:1.0,1:1.2},
        thr_score=lambda r,f: r*1.5 - f*2.0,
        note="V64 + last filter 96→128 (wider feature extraction)",
    ),
    79: dict(
        filters=[32,64,64,96], kernels=[3,3,3,3], dense=48,
        lr=3e-4, dropout=0.4, l2=1e-4, batch=32, epochs=200, cw={0:1.0,1:1.2},
        thr_score=lambda r,f: r*1.5 - f*2.0,
        note="V64 + Dense=48 (more classification capacity)",
    ),
    80: dict(
        filters=[32,64,64,96], kernels=[3,3,3,3], dense=32,
        lr=3e-4, dropout=0.4, l2=3e-4, batch=32, epochs=200, cw={0:1.0,1:1.2},
        thr_score=lambda r,f: r*1.5 - f*2.0,
        note="V64 + L2=3e-4 (tuned regularization between 1e-4 and 5e-4)",
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
    fx,fy = build_windows(pd.read_csv(DATA_DIR/"fall.csv"),     1)
    nx,ny = build_windows(pd.read_csv(DATA_DIR/"non_fall.csv"), 0)
    np.random.seed(seed)
    n  = min(len(fy), len(ny))
    X  = np.concatenate([fx[np.random.choice(len(fy),n,replace=False)],
                         nx[np.random.choice(len(ny),n,replace=False)]])
    y  = np.concatenate([fy[:n], ny[:n]])
    np.random.shuffle(idx := np.arange(len(y))); X,y = X[idx],y[idx]
    tr_x,tmp_x,tr_y,tmp_y = train_test_split(X,y,test_size=0.30,stratify=y,random_state=seed)
    va_x,te_x,va_y,te_y   = train_test_split(tmp_x,tmp_y,test_size=0.50,stratify=tmp_y,random_state=seed)
    return tr_x,va_x,te_x,tr_y,va_y,te_y

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
              loss='binary_crossentropy',metrics=['accuracy'])
    return m

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
    # Training curves
    fig,ax=plt.subplots(1,2,figsize=(12,4))
    ax[0].plot(hist.history['loss'],label='Train'); ax[0].plot(hist.history['val_loss'],label='Val')
    ax[0].set_title(f'V{v} Loss'); ax[0].legend()
    ax[1].plot(hist.history['accuracy'],label='Train'); ax[1].plot(hist.history['val_accuracy'],label='Val')
    ax[1].set_title(f'V{v} Accuracy'); ax[1].legend()
    plt.tight_layout(); plt.savefig(rd/"training_curves.png",dpi=150); plt.close()
    # Confusion matrix
    plt.figure(figsize=(6,5)); plt.imshow(cm,cmap='Blues')
    plt.title(f'V{v} CM (thr={thr:.2f})')
    for i in range(2):
        for j in range(2): plt.text(j,i,str(cm[i,j]),ha='center',va='center',fontsize=14)
    plt.xticks([0,1],['Non-Fall','Fall']); plt.yticks([0,1],['Non-Fall','Fall'])
    plt.savefig(rd/"confusion_matrix.png",dpi=150); plt.close()
    # Decision analysis
    plt.figure(figsize=(10,5))
    plt.plot(df_thr['threshold'],df_thr['recall'],label='Recall')
    plt.plot(df_thr['threshold'],df_thr['far'],label='FAR')
    plt.axvline(thr,color='r',ls='--',label=f'thr={thr:.2f}')
    plt.title(f'V{v} Decision Analysis'); plt.legend()
    plt.savefig(rd/"decision_analysis.png",dpi=150); plt.close()
    # ROC
    fpr,tpr,_=roc_curve(te_y,te_probs); rauc=auc(fpr,tpr)
    plt.figure(figsize=(6,5)); plt.plot(fpr,tpr,label=f'AUC={rauc:.3f}'); plt.plot([0,1],[0,1],'k--')
    plt.title(f'V{v} ROC'); plt.legend(); plt.savefig(rd/"roc_curve.png",dpi=150); plt.close()
    # Error analysis
    tp=(te_probs>=thr).astype(int)
    fn_i=np.where((tp==0)&(te_y==1))[0]; fp_i=np.where((tp==1)&(te_y==0))[0]
    fig,ax=plt.subplots(1,2,figsize=(12,5))
    if len(fn_i): ax[0].plot(te_x[fn_i[0]]); ax[0].set_title('False Negative sample')
    if len(fp_i): ax[1].plot(te_x[fp_i[0]]); ax[1].set_title('False Positive sample')
    plt.tight_layout(); plt.savefig(rd/"error_analysis.png",dpi=150); plt.close()
    # Dashboard
    fig=plt.figure(figsize=(15,10)); fig.suptitle(f'V{v} Dashboard',fontsize=18)
    a1=fig.add_subplot(2,2,1); a1.plot(hist.history['loss'],label='Train Loss')
    a1.plot(hist.history['val_loss'],label='Val Loss'); a1.legend(); a1.set_title('Loss')
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

# ─── Run ─────────────────────────────────────────────────────────────────────
def run_version(v, cfg):
    print(f"\n{'='*24} V{v} {'='*24}")
    print(f"  {cfg['note']}")
    out=AI_DIR/f"model_updated_version_{v}"
    md=out/"models"; rd=out/"results"; dd=out/"docs"
    for d in [md,rd,dd]: d.mkdir(parents=True,exist_ok=True)

    seed=v*100; tf.random.set_seed(seed)
    tr_x,va_x,te_x,tr_y,va_y,te_y = load_data(seed)

    model=build_model(cfg)
    model.layers[1].adapt(tr_x)
    cbs=[
        tf.keras.callbacks.EarlyStopping(patience=30,restore_best_weights=True,monitor='val_loss'),
        tf.keras.callbacks.ReduceLROnPlateau(factor=0.2,patience=12,min_lr=1e-8),
    ]
    hist=model.fit(tr_x,tr_y,validation_data=(va_x,va_y),
                   epochs=cfg['epochs'],batch_size=cfg['batch'],
                   callbacks=cbs,class_weight=cfg['cw'],verbose=0)

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
    cm=confusion_matrix(te_y,te_preds); tn,fp,fn,tp=cm.ravel()
    m={
        "version":v,
        "accuracy":         float(accuracy_score(te_y,te_preds)),
        "precision":        float(precision_score(te_y,te_preds,zero_division=0)),
        "recall":           float(recall_score(te_y,te_preds,zero_division=0)),
        "f1":               float(f1_score(te_y,te_preds,zero_division=0)),
        "false_alarm_rate": float(fp/(fp+tn)) if (fp+tn)>0 else 0,
        "miss_rate":        float(fn/(fn+tp)) if (fn+tp)>0 else 0,
        "best_threshold":   best_thr,
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
        f"| Miss Rate | **{m['miss_rate']*100:.2f}%** |\n")
    (rd/"metrics_summary.txt").write_text(
        f"Accuracy:  {m['accuracy']:.4f}\nRecall:    {m['recall']:.4f}\n"
        f"Precision: {m['precision']:.4f}\nF1:        {m['f1']:.4f}\n"
        f"FAR:       {m['false_alarm_rate']:.4f}\nMissRate:  {m['miss_rate']:.4f}\n"
        f"Threshold: {best_thr:.2f}\n")

    make_plots(v,hist,cm,te_probs,te_x,te_y,df_thr,best_thr,rd)
    size_kb=export_tflite(model,tr_x,md,v)
    m['size_kb']=size_kb

    (dd/"experiment_report.md").write_text(
        f"# Experiment Report — V{v}\n\n## Config\n"
        f"- Arch: {len(cfg['filters'])}×Conv1D {cfg['filters']}, K={cfg['kernels']}, Dense={cfg['dense']}\n"
        f"- LR={cfg['lr']} | Dropout={cfg['dropout']} | L2={cfg['l2']} | Batch={cfg['batch']}\n"
        f"- Class weight: {cfg['cw']} | Epochs={cfg['epochs']}\n"
        f"- Note: {cfg['note']}\n\n## Results\n"
        f"- F1: {m['f1']:.4f} | Recall: {m['recall']:.4f} | FAR: {m['false_alarm_rate']:.4f}\n"
        f"- Accuracy: {m['accuracy']:.4f} | Size: {size_kb:.2f} KB | Threshold: {best_thr:.2f}\n")
    (out/"README.md").write_text(
        f"# Model V{v}\n\n**{cfg['note']}**\n\n"
        f"| Metric | Value |\n|---|---|\n"
        f"| F1 | {m['f1']*100:.2f}% |\n| Recall | {m['recall']*100:.2f}% |\n"
        f"| FAR | {m['false_alarm_rate']*100:.2f}% |\n| Size | {size_kb:.2f} KB |\n\n"
        f"## Deploy\nplatformio.ini: `-I ../AI/model_updated_version_{v}/models`\n"
        f"main.cpp: `#include \"fall_detection_v{v}.h\"`\n")

    print(f"  V{v}: Acc={m['accuracy']:.4f} Rec={m['recall']:.4f} "
          f"F1={m['f1']:.4f} FAR={m['false_alarm_rate']:.4f} Size={size_kb:.2f}KB")
    return m

# ─── Main ────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    all_results=[]
    for v in sorted(VERSIONS):
        try:
            all_results.append(run_version(v,VERSIONS[v]))
        except Exception as e:
            print(f"  ERROR V{v}: {e}")
            import traceback; traceback.print_exc()

    print("\n"+"="*65)
    print(f"{'V':<6} {'Acc':>7} {'Recall':>8} {'F1':>8} {'FAR':>8} {'Size':>8}")
    print("-"*65)
    for m in all_results:
        marker=" ← NEW BEST" if m['f1']>0.9317 else ""
        print(f"V{m['version']:<5} {m['accuracy']*100:>6.2f}% {m['recall']*100:>7.2f}% "
              f"{m['f1']*100:>7.2f}% {m['false_alarm_rate']*100:>7.2f}% "
              f"{m['size_kb']:>7.2f}KB{marker}")

    # Update experiments_summary.md
    sp=AI_DIR/"experiments_summary.md"; existing=sp.read_text()
    section="\n## V71-V80 Results\n\n"
    section+="| Version | Note | Accuracy | Recall | F1 | FAR | Size |\n"
    section+="| :--- | :--- | :--- | :--- | :--- | :--- | :--- |\n"
    for m in all_results:
        section+=(f"| **V{m['version']}** | {VERSIONS[m['version']]['note'][:50]} "
                  f"| {m['accuracy']*100:.2f}% | {m['recall']*100:.2f}% "
                  f"| {m['f1']*100:.2f}% | {m['false_alarm_rate']*100:.2f}% "
                  f"| {m['size_kb']:.2f} KB |\n")
    tag="## V71-V80 Results"
    sp.write_text(existing[:existing.index(tag)]+section if tag in existing else existing+section)

    # Update model_comparison file
    comp_path=AI_DIR/"model_comparison_v1_v70.md"
    if comp_path.exists():
        comp=comp_path.read_text()
        new_rows="\n## V71-V80 (Appended)\n\n"
        new_rows+="| Version | Architecture | Acc | Recall | F1 | FAR | Miss | Size (KB) | Ghi chú |\n"
        new_rows+="| :--- | :--- | ---: | ---: | ---: | ---: | ---: | ---: | :--- |\n"
        for m in all_results:
            cfg=VERSIONS[m['version']]
            new_rows+=(f"| V{m['version']} | {cfg['filters']}/K{cfg['kernels'][0]}/D{cfg['dense']} "
                       f"| {m['accuracy']*100:.2f}% | {m['recall']*100:.2f}% "
                       f"| {m['f1']*100:.2f}% | {m['false_alarm_rate']*100:.2f}% "
                       f"| {m['miss_rate']*100:.2f}% | {m['size_kb']:.2f} | {cfg['note'][:40]} |\n")
        comp_path.write_text(comp+new_rows)
        # Rename to reflect 80 models
        new_comp=AI_DIR/"model_comparison_v1_v80.md"
        comp_path.rename(new_comp)
        print(f"\nComparison table updated: {new_comp}")
    print("\nAll done.")
