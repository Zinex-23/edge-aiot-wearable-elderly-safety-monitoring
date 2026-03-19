# data_processing

Folder nay da duoc don dep de chi giu cac thanh phan lien quan den ESP32-S3.

## Cau truc

- `code_train/`
  - Script tao dataset, train hybrid binary, train multiclass, va export model.
- `data/`
  - Dataset `WEDA 50Hz split 622`, `5-label`, `6-label`.
- `model/`
  - Model/artifact lien quan den ESP32-S3.
  - Bao gom hybrid binary, multiclass compact cho ESP32-S3, `espidf_export/`, va project `esp32_s3_fall_detect/`.
- `compare/`
  - Cac bang `.csv` so sanh model.
- `documentation/`
  - Tai lieu phan tich va huong dan cho ESP32-S3.

## Da loai bo

- `venv/`
- Cac artifact `ESP32-C3`
- Grid search / search safe / search targeted
- Cac artifact trung gian khong phuc vu ESP32-S3
- Cac model RandomForest da label khong phu hop de deploy truc tiep len ESP32-S3
