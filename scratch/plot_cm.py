import matplotlib.pyplot as plt
import numpy as np
from pathlib import Path

def plot_confusion_improved(cm, out_path):
    arr = np.asarray(cm)
    fig, ax = plt.subplots(figsize=(6, 5))
    im = ax.imshow(arr, cmap="Blues")
    ax.set_title("Confusion Matrix (High Contrast)", fontsize=14, pad=20)
    ax.set_xlabel("Predicted Label", fontsize=12)
    ax.set_ylabel("True Label", fontsize=12)
    ax.set_xticks([0, 1], labels=["non-fall", "fall"], fontsize=11)
    ax.set_yticks([0, 1], labels=["non-fall", "fall"], fontsize=11)
    
    thresh = arr.max() / 2.
    for i in range(2):
        for j in range(2):
            color = "white" if arr[i, j] > thresh else "black"
            ax.text(j, i, str(arr[i, j]), ha="center", va="center", 
                    color=color, fontsize=14, fontweight='bold')
            
    fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    fig.tight_layout()
    fig.savefig(out_path, dpi=300) # High DPI for slides
    plt.close(fig)

if __name__ == "__main__":
    cm = [[204, 41], [4, 240]]
    out_file = "/home/dsoft1/CAPSTONE/Code/System_Architecture/ai/confusion_matrix.png"
    plot_confusion_improved(cm, out_file)
    print(f"Improved confusion matrix saved to {out_file}")
