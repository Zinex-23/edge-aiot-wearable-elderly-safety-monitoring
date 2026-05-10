import os
import json
import pandas as pd
from pathlib import Path

BASE_DIR = Path("/home/zinex/CAPSTONE/AI/edge-aiot-wearable-elderly-safety-monitoring")
results_summary = []

for version in range(4, 15):
    try:
        metrics_path = BASE_DIR / f"AI/model_updated_version_{version}/results/metrics_v{version}.json"
        with open(metrics_path, "r") as f:
            m = json.load(f)
        
        # Get size from .md table
        md_path = BASE_DIR / f"AI/model_updated_version_{version}/results/metrics_v{version}.md"
        size = "Unknown"
        if md_path.exists():
            for line in md_path.read_text().split("\n"):
                if "Model Size" in line:
                    size = line.split("**")[1]
        
        results_summary.append({
            "Version": f"V{version}",
            "Accuracy": f"{m['accuracy']*100:.2f}%",
            "Recall": f"{m['recall']*100:.2f}%",
            "Precision": f"{m['precision']*100:.2f}%",
            "F1": f"{m['f1']*100:.2f}%",
            "FAR": f"{m['false_alarm_rate']*100:.2f}%",
            "Size": size
        })
    except Exception as e:
        print(f"Error reading V{version}: {e}")

# Final Summary Markdown
df_sum = pd.DataFrame(results_summary)
summary_path = BASE_DIR / "AI/experiments_summary.md"
with open(summary_path, "w") as f:
    f.write("# Final Experiments Summary (V4 - V14)\n\n")
    f.write("Comparison of 11 training iterations with 70:15:15 split and 1:1 balanced data.\n\n")
    f.write(df_sum.to_markdown(index=False))
    f.write("\n\n## Conclusion\n")
    # Find best model (highest F1)
    best_v = df_sum.loc[df_sum['F1'].str.replace('%','').astype(float).idxmax()]
    f.write(f"The best performing model overall is **{best_v['Version']}** with an F1-score of {best_v['F1']}.")

print(f"\nFinal summary saved to {summary_path}")
