# AI Model Experiments Summary (Full V1 - V50)

## 🏆 BẢNG XẾP HẠNG MÔ HÌNH (LEADERBOARD)

Dưới đây là các mô hình "Winner" được phân loại theo từng mục tiêu cụ thể:

| Hạng mục | Phiên bản | Thành tích nổi bật | Lý do bình chọn |
| :--- | :--- | :--- | :--- |
| **🥇 BEST OVERALL (Toàn diện)** | **V50** | F1: **91.68%**, Size: **41.85 KB** | Đạt mọi chỉ số >90% trong giới hạn 50KB. Cực kỳ ổn định. |
| **🥈 RUNNER UP (Toàn diện)** | **V43** | F1: **92.01%**, Size: **45.91 KB** | Có F1 cao nhất trong nhóm mô hình đời mới. |
| **🛡️ BEST FAR (Chống báo động giả)** | **V23** | FAR: **7.84%** | Tỷ lệ báo động sai thấp nhất lịch sử dự án. |
| **👁️ BEST RECALL (Độ nhạy)** | **V35** | Recall: **98.51%** | Gần như không thể bỏ sót bất kỳ cú ngã nào. |
| **⚡ BEST EFFICIENCY (Gọn nhẹ)** | **Balanced V2** | Size: **10.71 KB** | Hiệu năng cực tốt (F1 91%) trong một kích thước siêu nhỏ. |
| **⭐ HONORABLE MENTION (Đề cử)** | **V27** | F1: **90.64%**, FAR: **8.96%** | "Công thần" kiến trúc. Tuy hơi quá 50KB (51.7 KB) nhưng là tiền đề cho V31-V50. |

---

## 📊 Bảng so sánh chi tiết (V1 - V50)

| Phiên bản | Cấu hình (Filters/Kernel/Dense) | Accuracy | Recall | F1 | FAR | Size | Ghi chú |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **V50** | [32,48,64,96] / K5 / D20 | **91.23%** | **96.64%** | **91.68%** | 14.18% | 41.85 KB | **Winner**. |
| **V49** | [24,48,64,96] / K5 / D16 (LR 3e-4) | **90.67%** | **92.54%** | **90.84%** | **11.19%** | 40.27 KB | Cân bằng. |
| **V48** | [32,48,80,96] / K5 / D16 | 88.99% | **95.52%** | 89.67% | 17.54% | 44.56 KB | |
| **V47** | [24,48,64,96] / K5 / D24 | 88.81% | 87.69% | 88.68% | **10.07%** | 41.25 KB | |
| **V46** | [24,48,64,96] / K5 / D16 (CW 1.1) | 89.74% | **98.51%** | **90.57%** | 19.03% | 40.27 KB | |
| **V45** | [24,48,64,96] / K5 / D16 (FAR 3x) | **90.49%** | **94.03%** | **90.81%** | 13.06% | 40.27 KB | |
| **V44** | [24,48,64,96] / K5 / D16 (FAR 2.5x) | **91.42%** | **97.01%** | **91.87%** | 14.18% | 40.24 KB | |
| **V43** | [32,64,80,80] / K5 / D24 | **91.60%** | **96.64%** | **92.01%** | 13.43% | 45.91 KB | |
| **V42** | [32,64,80,96] / K5 / D16 | **90.67%** | **94.40%** | **91.01%** | 13.06% | 47.13 KB | |
| **V41** | [32,48,64,96] / K5 / D16 | **90.49%** | **95.90%** | **90.97%** | 14.93% | 40.79 KB | |
| **V40** | [32,64,80,80] / K3 / D24 | **91.79%** | **97.01%** | **92.20%** | 13.43% | 45.30 KB | |
| **V39** | [32,64,80,80] / K3 / D16 | 89.18% | **90.67%** | 89.34% | 12.31% | 44.45 KB | |
| **V38** | [32,48,64,80] / K5 / D24 | 86.01% | 82.46% | 85.49% | **10.45%** | 40.52 KB | |
| **V37** | [24,48,64,96] / K5 / D16 | **91.04%** | **92.91%** | **91.21%** | **10.82%** | **40.27 KB** | |
| **V35** | [32,64,64,96] / K3 / D16 (CW 1.2) | **92.16%** | **98.51%** | **92.63%** | 14.18% | 42.70 KB | |
| **V31** | [32,64,64,96] / K3 / D16 | **90.30%** | **96.64%** | **90.88%** | 16.04% | 42.14 KB | |
| **V30** | [32,48,64,64] / K5 / D32 (FAR 3x) | 87.50% | 84.70% | 87.14% | **9.70%** | 39.28 KB | |
| **V27** | [32,64,64,96] / K3 / D32 | **90.67%** | **90.30%** | **90.64%** | **8.96%** | 51.73 KB | |
| **V23** | [32,64,96,96] / K3 / D16 | **90.67%** | 89.18% | **90.53%** | **7.84%** | 49.24 KB | |
| **V22** | [16,32,48,64] / K5 / D16 | **92.35%** | **94.78%** | **92.53%** | **10.07%** | 34.46 KB | |
| **Balanced V2**| [16,32] / K3 / D16 | **90.80%** | **98.36%** | **91.43%** | 16.73% | **10.71 KB** | **Official**. |
| **V13** | [16,32] / K3 / D16 (Optimized) | **92.16%** | **96.64%** | **92.50%** | 12.31% | 17.55 KB | |
| **V4** | [16,16] / K3 / D16 | **91.60%** | **97.39%** | **92.06%** | 14.18% | 17.08 KB | |
| **V2** | [8,16] / K3 / D16 | 87.94% | 83.58% | 82.20% | **9.89%** | 19.76 KB | |

---
*Ghi chú: Bảng trên rút gọn các cột mốc quan trọng và cấu hình tương ứng. Filters hiển thị dưới dạng danh sách các lớp Conv. K3=Kernel 3, K5=Kernel 5. D=Dense Size.*

## 🏁 Tổng kết toàn diện:
- **Tiến trình**: Đã hoàn thành 100% (V1 -> V50).
- **Phân tích tham số**: Sự chuyển dịch từ **Kernel 3 sang Kernel 5** (từ V37) và việc tăng số lớp Conv từ 2 lên 4 (từ V21) là chìa khóa để đạt được sự cân bằng giữa độ nhạy và báo động giả trong khi vẫn giữ kích thước dưới 50KB.
- **Khuyến nghị**: Sử dụng **V50** vì nó tận dụng tốt nhất kiến trúc Kernel 5 và bộ lọc [32,48,64,96] để đạt hiệu năng toàn diện trên 90%.

## V51-V60 Results

| Version | Note | Accuracy | Recall | F1 | FAR | Size |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **V51** | V50 base, cw=1:1, FAR-penalized scoring | 83.21% | 72.76% | 81.25% | 6.34% | 76.64 KB |
| **V52** | V50 base, cw=1:1.5, Recall-maximizing sc | 92.16% | 97.39% | 92.55% | 13.06% | 77.06 KB |
| **V53** | K7 kernels — larger temporal receptive f | 90.49% | 97.76% | 91.13% | 16.79% | 98.52 KB |
| **V54** | V50 base + Dense=32 (more classification | 92.72% | 97.76% | 93.07% | 12.31% | 78.68 KB |
| **V55** | Wider filters [48,64,80,96] — more featu | 91.23% | 96.64% | 91.68% | 14.18% | 104.00 KB |
| **V56** | V50 base + Dropout=0.5 (more regularizat | 90.86% | 89.55% | 90.74% | 7.84% | 77.23 KB |
| **V57** | V50 base + L2=5e-4 (stronger weight deca | 91.04% | 97.01% | 91.55% | 14.93% | 77.23 KB |
| **V58** | V50 base + LR=1e-4 (finer convergence) | 91.23% | 93.66% | 91.44% | 11.19% | 77.23 KB |
| **V59** | V50 base + BatchSize=32 (better generali | 92.16% | 92.54% | 92.19% | 8.21% | 77.23 KB |
| **V60** | Mixed kernels K3/K5/K5/K3 — multi-scale  | 88.99% | 89.93% | 89.09% | 11.94% | 64.85 KB |

## V61-V70 Results

| Version | Note | Accuracy | Recall | F1 | FAR | Size |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **V61** | V22 arch [16,32,48,64]/K5 + D32 + batch=32 | 86.94% | 90.30% | 87.36% | 16.42% | 46.95 KB |
| **V62** | V54+V59 combo: D32 + batch=32 (best F1 + best | 90.49% | 97.01% | 91.07% | 16.04% | 78.52 KB |
| **V63** | V56+V59 combo: dropout=0.5 + batch=32 (FAR re | 89.55% | 92.16% | 89.82% | 13.06% | 77.14 KB |
| **V64** | V27 arch [32,64,64,96]/K3/D32 + batch=32 | 92.91% | 96.64% | 93.17% | 10.82% | 62.09 KB |
| **V65** | V37 arch [24,48,64,96]/K5 + D24 + batch=32 | 89.18% | 96.27% | 89.90% | 17.91% | 75.38 KB |
| **V66** | V22 arch tuned: D24 + dropout=0.45 + batch=32 | 91.79% | 95.52% | 92.09% | 11.94% | 46.81 KB |
| **V67** | Max regularize: D32 + dropout=0.5 + batch=32  | 88.62% | 96.64% | 89.46% | 19.40% | 78.70 KB |
| **V68** | V58+V59 combo: LR=1e-4 + batch=32 | 89.74% | 95.90% | 90.33% | 16.42% | 77.23 KB |
| **V69** | V54+V59+V57 combo: D32 + batch=32 + L2=5e-4 | 90.67% | 97.39% | 91.26% | 16.04% | 78.70 KB |
| **V70** | 5 conv layers [16,32,48,64,96]/K5 — novel dep | 90.86% | 94.03% | 91.14% | 12.31% | 83.25 KB |

## V71-V80 Results

| Version | Note | Accuracy | Recall | F1 | FAR | Size |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **V71** | V64 + LR=1e-4 (finer convergence on best arch) | 90.11% | 93.66% | 90.45% | 13.43% | 61.51 KB |
| **V72** | V64 + batch=16 (smaller batch → better generalizat | 89.18% | 97.01% | 89.97% | 18.66% | 61.93 KB |
| **V73** | V23 arch [32,64,96,96]/K3 + D32+batch=32 (V23 had  | 90.67% | 91.04% | 90.71% | 9.70% | 77.88 KB |
| **V74** | V64 arch switched to K5 + D32 + batch=32 | 90.86% | 96.64% | 91.36% | 14.93% | 86.46 KB |
| **V75** | V64 + dropout=0.3 (less regularization, more capac | 89.93% | 95.90% | 90.49% | 16.04% | 62.09 KB |
| **V76** | V64 + cw=1.1 + FAR penalty×2.5 (less recall bias → | 90.11% | 92.16% | 90.31% | 11.94% | 62.10 KB |
| **V77** | V54+V59+V58: [32,48,64,96]/K5/D32 + batch=32 + LR= | 91.23% | 92.16% | 91.31% | 9.70% | 78.70 KB |
| **V78** | V64 + last filter 96→128 (wider feature extraction | 89.93% | 95.90% | 90.49% | 16.04% | 69.98 KB |
| **V79** | V64 + Dense=48 (more classification capacity) | 91.42% | 93.28% | 91.58% | 10.45% | 64.05 KB |
| **V80** | V64 + L2=3e-4 (tuned regularization between 1e-4 a | 93.10% | 97.39% | 93.38% | 11.19% | 62.10 KB |

## V81-V90 Results (Overfitting Fix)

| V | Strategy | Acc | Recall | F1 | FAR | Epoch |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **V81** | patience=10 — user suggestion, baseline test | 91.23% | 92.16% | 91.31% | 9.70% | 30 |
| **V82** | patience=20 + ReduceLR(factor=0.1, patience=5 | 92.16% | 98.88% | 92.66% | 14.55% | 46 |
| **V83** | Dropout=0.5 + L2=5e-4 — strong regularization | 90.30% | 95.90% | 90.81% | 15.30% | 66 |
| **V84** | Gaussian noise aug σ=0.05 — fix overfitting a | 93.10% | 98.51% | 93.45% | 12.31% | 78 |
| **V85** | Cosine decay LR — smooth convergence, no osci | 89.74% | 97.76% | 90.50% | 18.28% | 43 |
| **V86** | aug σ=0.05 + L2=5e-4 + LR aggressive — two st | 91.79% | 98.13% | 92.28% | 14.55% | 65 |
| **V87** | patience=10 + aug σ=0.05 — user idea + root f | 88.43% | 94.40% | 89.08% | 17.54% | 20 |
| **V88** | Dropout=0.45 + aggressive LR(factor=0.1, p=5) | 91.42% | 96.64% | 91.84% | 13.81% | 31 |
| **V89** | Gaussian noise aug σ=0.10 — stronger augmenta | 90.49% | 94.78% | 90.88% | 13.81% | 57 |
| **V90** | BEST COMBO: drop=0.45+L2=5e-4+aug0.05+LR_aggr | 89.18% | 95.15% | 89.79% | 16.79% | 93 |
