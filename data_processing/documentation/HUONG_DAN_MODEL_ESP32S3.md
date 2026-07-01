# Huong Dan Model Fall Detection tren ESP32-S3

Tai lieu nay mo ta model da export sang C trong project:
- `components/hybrid_model/hybrid_s3.c`
- `components/hybrid_model/include/hybrid_s3.h`
- `components/hybrid_model/hybrid_s3_feature_map.json`

## 1) Model hoat dong nhu the nao

Model theo kieu **Hybrid Edge AI** gom 2 stage:

1. Stage-1 Gate (rule):
   - Feature gate: `acc_mag_std`
   - Dieu kien gate: `acc_mag_std >= 0.0278328691`
   - Neu gate khong dat -> output xac suat fall = `0.0`

2. Stage-2 Classifier:
   - Random Forest: `40 trees`, `max_depth=12`, `min_samples_leaf=4`
   - So node tong: `22,242`
   - So feature sau transform: `83` (81 numeric + 2 one-hot)
   - Nguong quyet dinh label: `0.495`

## 2) Input model

Kieu input trong C:

```c
typedef struct {
    float num[81];
    int32_t cat[1];
} hybrid_s3_input_t;
```

Yeu cau:
- `num[81]`: 81 feature numeric, **dung dung thu tu** trong:
  - `hybrid_s3_numeric_feature_names` (khai bao trong `hybrid_s3.c/.h`)
  - hoac file `hybrid_s3_feature_map.json`
- `cat[0]`: feature categorical `source`
  - `0 = UP`
  - `1 = WEDA`
  - neu khong ro, dat `-1` de fallback ve gia tri mac dinh cua model.

Luu y quan trong:
- Neu thu tu feature sai, ket qua se sai.
- Cac feature phai duoc tinh tu cua so IMU giong pipeline train.

## 3) Output model

API chinh:
- `float hybrid_s3_predict_proba(const hybrid_s3_input_t *in);`
  - Tra ve xac suat fall trong [0, 1].
- `int hybrid_s3_predict_label(const hybrid_s3_input_t *in);`
  - Tra ve `1` (fall) neu `proba >= 0.495`, nguoc lai `0`.

## 4) Do chinh xac hien tai

Nguon metric: `hybrid_artifacts_esp32s3_quality/metrics.json`

Test set:
- Accuracy: `0.8495`
- Precision: `0.7182`
- Recall: `0.7633`
- F1: `0.7400`
- ROC-AUC: `0.9063`
- PR-AUC: `0.8049`
- FP: `124`, FN: `98`, TP: `316`, TN: `937`

Validation set:
- Accuracy: `0.8469`
- Precision: `0.7189`
- Recall: `0.6058`
- F1: `0.6575`
- ROC-AUC: `0.8366`

Train stage-2:
- Tong sample: `7,677`
- Fall: `2,238`
- Non-fall: `5,439`

## 5) Dung luong model

- File Python model (`.joblib`): ~`1.8 MB`
- File C export (`hybrid_s3.c`): ~`861 KB`
- Sau compile object (`gcc -Os`): ~`448 KB` (text+data)

Y nghia:
- Tren ESP32-S3, model da nhe hon nhieu so voi `.joblib`.
- Van can partition hop ly de flash app.

## 6) Yeu cau phan cung (khuyen nghi)

Toi thieu:
- ESP32-S3 (khuyen nghi 240MHz)
- Flash 4MB tro len
- Nguon on dinh (3.3V)

Khuyen nghi de build de dang:
- Dung `single app partition` (da set trong `sdkconfig.defaults`)
- Neu dung OTA, can tinh lai dung luong partition vi model C kha lon.

Tai nguyen runtime:
- Khong dung cap phat dong cho model.
- Bo nho tam cho vector transform: ~`83 * 4 bytes` ~`332 bytes` tren stack.

## 7) Model nay dung tot nhat khi nao

Model phu hop tot nhat khi:
- Du lieu IMU deo tay co dac trung giong du lieu train.
- Tan so lay mau va cach tao window/feature giong pipeline da train.
- Muc tieu la he thong canh bao fall thoi gian thuc tren edge.

Model kem on dinh hon khi:
- Domain du lieu khac manh so voi train data.
- Feature khong tinh dung chuan train.
- Ty le fall trong thuc te rat thap (can tune threshold de giam bao dong gia).

## 8) Cach goi nhanh trong firmware

```c
hybrid_s3_input_t in = {0};
// TODO: dien 81 numeric features vao in.num[]
in.cat[0] = 1; // WEDA

float p = hybrid_s3_predict_proba(&in);
int y = hybrid_s3_predict_label(&in);
```

Neu can uu tien precision hon, co the tang threshold trong logic app
(vi du 0.55 hoac 0.60) de giam false positive.
