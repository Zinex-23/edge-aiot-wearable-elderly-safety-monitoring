# Huong dan su dung folder `train_ready` de hieu va phan tich du lieu

Tai lieu nay giup ban:
- hieu vai tro tung file trong `train_ready`
- chay nhanh cac buoc phan tich co ban
- kiem tra chat luong split truoc khi train model

## 1) Cac file trong folder

- `windows_all.csv`: toan bo windows + features + cot `split` (train/validation/test).
- `train.csv`: du lieu train (khong co cot `split`).
- `validation.csv`: du lieu validation.
- `test.csv`: du lieu test.
- `split_summary.json`: thong ke nhanh so dong, so fall/non-fall, subjects, trials theo split.
- `subject_splits.json`: danh sach `subject_id` thuoc moi split (de tranh leak subject).

Thong ke hien tai (theo `split_summary.json`):
- train: 9,250 rows (fall 2,426 / non-fall 6,824), 21 subjects, 788 trials
- validation: 2,280 rows (fall 553 / non-fall 1,727), 5 subjects, 180 trials
- test: 1,475 rows (fall 414 / non-fall 1,061), 3 subjects, 127 trials

## 2) Dung duoc ngay sau khi move folder

Dat bien moi truong tro den folder `train_ready` moi:

```bash
export TRAIN_READY_DIR="/duong_dan_moi/train_ready"
cd "$TRAIN_READY_DIR"
ls -lh
```

Kiem tra nhanh file bat buoc:

```bash
python3 - << 'PY'
from pathlib import Path
import os
base = Path(os.environ["TRAIN_READY_DIR"])
required = [
    "windows_all.csv",
    "train.csv",
    "validation.csv",
    "test.csv",
    "split_summary.json",
    "subject_splits.json",
]
missing = [f for f in required if not (base / f).exists()]
print("OK" if not missing else f"Missing: {missing}")
PY
```

## 3) Hieu schema trong CSV

### 3.1 Metadata columns (y nghia nghiep vu)

- `source`: nguon du lieu (`UP` hoac `WEDA`)
- `subject_id`: id nguoi dung (vi du `UP_01`, `WEDA_05`)
- `trial_id`: id lan ghi
- `activity_code`: ma hoat dong (`Fxx` thuong la fall, `Dxx` thuong la non-fall ben WEDA)
- `label`: nhan dich (`1=fall`, `0=non-fall`)
- `source_freq_hz`: tan so lay mau cua nguon
- `window_index`: thu tu cua window trong trial
- `start_index`: sample bat dau cua window
- `num_samples`: so sample trong window

### 3.2 Feature columns

Pattern ten cot:
- `<channel>_<stat>`

Channels:
- `acc_x`, `acc_y`, `acc_z`, `gyro_x`, `gyro_y`, `gyro_z`, `acc_mag`, `gyro_mag`

Stats:
- `mean`, `std`, `min`, `max`, `median`, `p25`, `p75`, `iqr`, `energy`, `abs_mean`

## 4) Checklist phan tich toi thieu truoc khi train

## 4.1 Kiem tra class imbalance theo split

```bash
python3 - << 'PY'
import os, pandas as pd
from pathlib import Path
base = Path(os.environ["TRAIN_READY_DIR"])
for name in ["train.csv","validation.csv","test.csv"]:
    df = pd.read_csv(base / name)
    total = len(df)
    fall = int(df["label"].sum())
    non_fall = total - fall
    print(f"{name:14} total={total:5d} fall={fall:5d} non_fall={non_fall:5d} fall_ratio={fall/total:.3f}")
PY
```

Muc dich:
- biet muc do lech lop
- quyet dinh co can `class_weight`, threshold tuning, hoac re-sampling

## 4.2 Kiem tra leakage theo subject

```bash
python3 - << 'PY'
import json, os
from pathlib import Path
base = Path(os.environ["TRAIN_READY_DIR"])
splits = json.loads((base / "subject_splits.json").read_text())
tr = set(splits["train"]); va = set(splits["validation"]); te = set(splits["test"])
print("train_inter_val :", tr & va)
print("train_inter_test:", tr & te)
print("val_inter_test  :", va & te)
PY
```

Ky vong:
- ca 3 giao nhau phai rong (`set()`).

## 4.3 Kiem tra domain mix (UP vs WEDA)

```bash
python3 - << 'PY'
import os, pandas as pd
from pathlib import Path
base = Path(os.environ["TRAIN_READY_DIR"])
for name in ["train.csv","validation.csv","test.csv"]:
    df = pd.read_csv(base / name)
    print("\\n", name)
    print(pd.crosstab(df["source"], df["label"], margins=True))
PY
```

Ghi chu:
- hien tai split test co xu huong nghieng ve WEDA (khong dai dien day du cho cross-domain neu ban muon do tong quat tren UP).

## 4.4 Kiem tra distribution shift nhanh tren mot vai feature quan trong

```bash
python3 - << 'PY'
import os, pandas as pd
from pathlib import Path
base = Path(os.environ["TRAIN_READY_DIR"])
cols = ["acc_mag_mean","acc_mag_std","gyro_mag_mean","gyro_mag_std"]
for name in ["train.csv","validation.csv","test.csv"]:
    df = pd.read_csv(base / name)
    print(f"\\n{name}")
    print(df[cols].describe().loc[["mean","std","min","max"]])
PY
```

Neu test co phan bo rat khac train:
- model co the overfit domain train
- can bo sung split cross-dataset hoac thu thap du lieu that tren thiet bi deo

## 5) Quy trinh doc nhanh de "hieu du lieu trong 5 phut"

1. Mo `split_summary.json` de nam quy mo va class ratio.
2. Mo `subject_splits.json` de xem split theo subject co dung khong.
3. Mo 20 dong dau `windows_all.csv` de hieu schema.
4. Chay 4 lenh o muc 4.1 -> 4.4.
5. Ghi ket luan ngan:
   - class imbalance muc nao?
   - co leak subject khong?
   - test co dai dien domain muc tieu deploy khong?
   - can dieu chinh threshold hay can them du lieu?

## 6) Neu ban muon train lai sau khi move folder

Neu project script van o repo cu, chi can chi ro path CSV moi (vi du):

```bash
python3 train_model.py \
  --train-csv "/duong_dan_moi/train_ready/train.csv" \
  --val-csv "/duong_dan_moi/train_ready/validation.csv" \
  --test-csv "/duong_dan_moi/train_ready/test.csv"
```

Neu can, ban co the copy file nay di cung folder `train_ready` moi de dung nhu runbook.
