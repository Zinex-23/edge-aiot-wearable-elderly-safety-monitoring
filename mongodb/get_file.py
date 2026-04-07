from pathlib import Path

from flask import Flask, abort, jsonify, send_from_directory
from werkzeug.utils import secure_filename


app = Flask(__name__)

BASE_DIR = Path(__file__).resolve().parent
UPLOAD_FOLDER = BASE_DIR / "uploads"
ALLOWED_EXTENSIONS = {".csv", ".xlsx"}

UPLOAD_FOLDER.mkdir(parents=True, exist_ok=True)


def is_allowed_file(path: Path) -> bool:
    return path.is_file() and path.suffix.lower() in ALLOWED_EXTENSIONS


def get_uploaded_files() -> list[Path]:
    files = [path for path in UPLOAD_FOLDER.iterdir() if is_allowed_file(path)]
    files.sort(key=lambda path: path.stat().st_mtime, reverse=True)
    return files


def resolve_safe_file(filename: str) -> Path:
    safe_name = secure_filename(filename)
    if not safe_name or safe_name != filename:
        abort(400, description="Filename khong hop le.")

    file_path = UPLOAD_FOLDER / safe_name
    if not is_allowed_file(file_path):
        abort(404, description="Khong tim thay file.")

    return file_path


@app.route("/files", methods=["GET"])
def list_files():
    try:
        files = get_uploaded_files()
        return jsonify(
            {
                "status": "ok",
                "count": len(files),
                "files": [
                    {
                        "name": file_path.name,
                        "size_bytes": file_path.stat().st_size,
                        "modified_at": int(file_path.stat().st_mtime),
                    }
                    for file_path in files
                ],
            }
        )
    except Exception as exc:
        return (
            jsonify(
                {
                    "status": "error",
                    "message": f"Khong the doc danh sach file: {exc}",
                }
            ),
            500,
        )


@app.route("/download/<path:filename>", methods=["GET"])
def download_file(filename: str):
    file_path = resolve_safe_file(filename)
    return send_from_directory(
        directory=str(UPLOAD_FOLDER),
        path=file_path.name,
        as_attachment=True,
    )


@app.route("/latest", methods=["GET"])
def download_latest():
    try:
        files = get_uploaded_files()
        if not files:
            abort(404, description="Chua co file nao trong uploads.")

        latest_file = files[0]
        return send_from_directory(
            directory=str(UPLOAD_FOLDER),
            path=latest_file.name,
            as_attachment=True,
        )
    except FileNotFoundError:
        abort(404, description="Thu muc uploads khong ton tai.")


@app.errorhandler(400)
def handle_bad_request(error):
    return jsonify({"status": "error", "message": error.description}), 400


@app.errorhandler(404)
def handle_not_found(error):
    return jsonify({"status": "error", "message": error.description}), 404


@app.errorhandler(500)
def handle_server_error(error):
    return (
        jsonify(
            {
                "status": "error",
                "message": "Loi server noi bo.",
            }
        ),
        500,
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=3000, debug=False)
