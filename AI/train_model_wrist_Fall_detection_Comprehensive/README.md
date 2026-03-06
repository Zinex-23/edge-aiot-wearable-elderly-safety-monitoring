# train_model_wrist_Fall_detection_Comprehensive

Pipeline huan luyen model phat hien te nga cho du lieu deo tay, su dung:
- UP-Fall wrist: `Fall_UP_Dataset/up_fall_wrist.csv`
- WEDA-FALL 50Hz: `WEDA-FALL-main/dataset/50Hz`

## Cau truc tao ra

- `train_ready/windows_all.csv`: toan bo cua so + feature + split.
- `train_ready/train.csv`: tap train.
- `train_ready/validation.csv`: tap validation.
- `train_ready/test.csv`: tap test.
- `train_ready/subject_splits.json`: danh sach subject theo split (khong leak subject).
- `train_ready/split_summary.json`: thong ke nhanh moi split.
- `artifacts/rf_fall_model.joblib`: model RandomForest.
- `artifacts/metrics.json`: ket qua train/val/test.
- `artifacts/validation_predictions.csv`, `artifacts/test_predictions.csv`: du doan.
- `wrist_band_fall.h`: model C header de tich hop firmware (ESP32, etc.).

## Cai dat

```bash
cd /home/dsoft1/Downloads/train_model_wrist_Fall_detection_Comprehensive
python3 -m pip install -r requirements.txt
```

## Buoc 1: Tao train-ready + chia train/val/test

```bash
python3 prepare_train_ready.py
```

Mac dinh:
- window = `2.0s`
- overlap = `50%`
- UP sampling = `4Hz`
- WEDA sampling = `50Hz`
- split theo subject: `70/15/15`

Co the doi tham so:

```bash
python3 prepare_train_ready.py \
  --window-seconds 2.0 \
  --overlap 0.5 \
  --train-ratio 0.7 \
  --val-ratio 0.15 \
  --test-ratio 0.15 \
  --seed 42
```

## Buoc 2: Train model

```bash
python3 train_model.py --model-type logistic --top-k 0 --quantize-int8
```

Khuyen nghi cho ESP32-C2:
- dung `--model-type logistic`
- dung `--top-k 0 --quantize-int8` (0 = giu tat ca feature, van nho)
- model header se rat nho (KB-level).

Co the doi hyper-parameters:

```bash
python3 train_model.py \
  --model-type extra_trees \
  --n-estimators 500 \
  --min-samples-leaf 2 \
  --max-depth 14 \
  --max-features 0.5 \
  --class-weight balanced \
  --seed 42
```

Xuat model `.h` voi ten/duong dan tuy chon:

```bash
python3 train_model.py --export-header ./wrist_band_fall.h
```

## Ghi chu

- Script chia theo `subject_id` de tranh leakage.
- Label:
  - UP: dung cot `is_fall`.
  - WEDA: folder `Fxx` la fall (`1`), `Dxx` la non-fall (`0`).
- Feature duoc trich tu 6 kenh: `acc_x,y,z` va `gyro_x,y,z` + do lon vector.
- Tree ensemble (`extra_trees`, `random_forest`) thuong cho header C rat lon, khong phu hop ESP32-C2 4MB.
