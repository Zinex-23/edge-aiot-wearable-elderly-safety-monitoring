from flask import Flask, request
import os
import pandas as pd
from datetime import datetime

app = Flask(**name**)

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

@app.route('/upload', methods=['POST'])
def upload_csv():
try:
# Lấy tên file từ header ESP32
filename = request.headers.get("X-Filename")

```
    if not filename:
        filename = f"esp32_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"

    csv_path = os.path.join(UPLOAD_FOLDER, filename)

    # Nhận raw data từ ESP32
    with open(csv_path, "wb") as f:
        f.write(request.data)

    print(f"Received CSV: {csv_path}")

    # Convert sang Excel
    excel_path = csv_path.replace(".csv", ".xlsx")
    df = pd.read_csv(csv_path)
    df.to_excel(excel_path, index=False)

    print(f"Converted to Excel: {excel_path}")

    return {
        "status": "ok",
        "csv": csv_path,
        "excel": excel_path
    }

except Exception as e:
    print("Error:", e)
    return {"status": "error", "message": str(e)}, 500
```

if **name** == '**main**':
app.run(host='0.0.0.0', port=3000)
