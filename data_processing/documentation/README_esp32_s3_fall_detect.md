# ESP32-S3 Fall Detection Demo (ESP-IDF)

Project nay da tich hop model da export ra C:
- `components/hybrid_model/hybrid_s3.c`
- `components/hybrid_model/include/hybrid_s3.h`

`main/main.c` hien dang chay du lieu demo (non-fall/fall) de ban test nhanh qua UART.

## 1) Build

```bash
cd esp32_s3_fall_detect
idf.py set-target esp32s3
idf.py build
```

## 2) Flash + Monitor

```bash
idf.py -p /dev/ttyUSB0 flash monitor
```

Neu may ban ra `/dev/ttyACM0` thi doi lai port.

## 3) Cac log can thay

Ban se thay log:
- thong tin model (so trees, gate feature, threshold)
- moi chu ky 1 giay in `gate`, `prob`, `pred`
- neu `pred=1` se in `FALL ALERT`

## 4) Tich hop du lieu IMU that

Ban can thay the 2 ham trong `main/main.c`:
- `fill_demo_non_fall(...)`
- `fill_demo_fall(...)`

bang pipeline thuc:
1. Thu thap cua so IMU.
2. Tinh dung bo 81 features theo thu tu trong:
   - `components/hybrid_model/hybrid_s3_feature_map.json`
3. Gan `in.cat[0]`:
   - `0` = `UP`
   - `1` = `WEDA`
4. Goi:
   - `hybrid_s3_predict_proba(&in)` hoac
   - `hybrid_s3_predict_label(&in)`

## 5) Luu y bo nho

File model C kha lon, nen project da dat `single app` partition trong `sdkconfig.defaults`.
