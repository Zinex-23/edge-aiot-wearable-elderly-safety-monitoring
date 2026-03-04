import argparse
import csv
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple


LABEL_DIRS = ("FALL", "non-FALL")
SUPPORTED_EXTS = {".csv", ".txt"}

CANONICAL_COLUMNS = [
    "label",
    "dataset",
    "source_relpath",
    "source_filename",
    "row_in_file",
    "source_format",
    "subject_id",
    "activity_id",
    "trial_id",
    "sensor_type",
    "timestamp_raw",
    "timestamp_unit",
    "timestamp_iso_utc",
    "timestamp_epoch_sec",
    "time_rel_sec",
    "acc_x",
    "acc_y",
    "acc_z",
    "gyro_x",
    "gyro_y",
    "gyro_z",
    "ori_w",
    "ori_x",
    "ori_y",
    "ori_z",
    "droll",
    "dpitch",
    "dyaw",
    "heart",
    "luminosity",
    "wrist_ang_x",
    "wrist_ang_y",
    "wrist_ang_z",
    "fenix_c1",
    "fenix_c2",
    "fenix_c3",
    "fenix_c4",
    "fenix_c5",
    "is_fall_raw",
    "raw_1",
    "raw_2",
    "raw_3",
]

FILE_STATS_COLUMNS = [
    "source_relpath",
    "label",
    "dataset",
    "source_format",
    "sensor_type",
    "rows_written",
    "rows_skipped",
    "parse_errors",
]


@dataclass
class FileStats:
    source_relpath: str
    label: str
    dataset: str
    source_format: str
    sensor_type: str
    rows_written: int = 0
    rows_skipped: int = 0
    parse_errors: int = 0

    def to_row(self) -> Dict[str, str]:
        return {
            "source_relpath": self.source_relpath,
            "label": self.label,
            "dataset": self.dataset,
            "source_format": self.source_format,
            "sensor_type": self.sensor_type,
            "rows_written": str(self.rows_written),
            "rows_skipped": str(self.rows_skipped),
            "parse_errors": str(self.parse_errors),
        }


def parse_args() -> argparse.Namespace:
    script_dir = Path(__file__).resolve().parent
    default_input = script_dir / "archive" / "total_data"
    default_output = default_input / "normalized"
    parser = argparse.ArgumentParser(description="Normalize all FALL/non-FALL data into one schema.")
    parser.add_argument("--input-root", type=str, default=str(default_input))
    parser.add_argument("--output-dir", type=str, default=str(default_output))
    return parser.parse_args()


def format_number(value: Optional[float]) -> str:
    if value is None:
        return ""
    if value != value:
        return ""
    return f"{value:.15g}"


def parse_float(text: str) -> Optional[float]:
    try:
        return float(text.strip())
    except Exception:
        return None


def parse_int(text: str) -> Optional[int]:
    try:
        return int(float(text.strip()))
    except Exception:
        return None


def normalize_header_cells(cells: Iterable[str]) -> List[str]:
    out: List[str] = []
    seen = Counter()
    for idx, cell in enumerate(cells, start=1):
        name = cell.strip().lstrip("\ufeff").lower()
        name = name.replace(" ", "_")
        name = re.sub(r"[^0-9a-z_]+", "_", name).strip("_")
        if not name:
            name = f"col_{idx}"
        seen[name] += 1
        if seen[name] > 1:
            name = f"{name}_{seen[name]}"
        out.append(name)
    return out


def extract_subject_id(relpath: Path) -> str:
    text = str(relpath)
    m1 = re.search(r"subject_(\d+)", text, flags=re.IGNORECASE)
    if m1:
        return m1.group(1)
    m2 = re.search(r"/sub(\d+)/", text.replace("\\", "/"), flags=re.IGNORECASE)
    if m2:
        return m2.group(1)
    return ""


def make_base_row(
    template: Dict[str, str],
    label: str,
    dataset: str,
    relpath: Path,
    row_in_file: int,
    source_format: str,
    subject_id: str,
    activity_id: str,
    trial_id: str,
    sensor_type: str,
) -> Dict[str, str]:
    row = template.copy()
    row["label"] = label
    row["dataset"] = dataset
    row["source_relpath"] = str(relpath)
    row["source_filename"] = relpath.name
    row["row_in_file"] = str(row_in_file)
    row["source_format"] = source_format
    row["subject_id"] = subject_id
    row["activity_id"] = activity_id
    row["trial_id"] = trial_id
    row["sensor_type"] = sensor_type
    return row


def parse_mobi_file(
    path: Path,
    relpath: Path,
    label: str,
    dataset: str,
    writer: csv.DictWriter,
    template: Dict[str, str],
) -> FileStats:
    subject_id = extract_subject_id(relpath)
    activity_id = relpath.parts[-2] if len(relpath.parts) >= 2 else ""
    trial_id = ""
    sensor_type = "mobi_unknown"

    sensor_match = re.search(r"_(acc|gyro|ori)_", path.name, flags=re.IGNORECASE)
    if sensor_match:
        sensor_type = f"mobi_{sensor_match.group(1).lower()}"

    trial_match = re.search(r"_(\d+)_(\d+)\.txt$", path.name, flags=re.IGNORECASE)
    if trial_match:
        trial_id = trial_match.group(2)

    stats = FileStats(str(relpath), label, dataset, "mobi_txt", sensor_type)
    data_started = False
    first_ts: Optional[float] = None
    row_in_file = 0

    with path.open("r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            s = line.strip()
            if not s:
                continue
            if not data_started:
                if s.upper() == "@DATA":
                    data_started = True
                continue
            if s.startswith("#"):
                continue

            parts = [p.strip() for p in s.split(",")]
            if len(parts) < 4:
                stats.rows_skipped += 1
                continue

            ts_val = parse_float(parts[0])
            x_val = parse_float(parts[1])
            y_val = parse_float(parts[2])
            z_val = parse_float(parts[3])
            if ts_val is None or x_val is None or y_val is None or z_val is None:
                stats.parse_errors += 1
                continue

            row_in_file += 1
            row = make_base_row(
                template=template,
                label=label,
                dataset=dataset,
                relpath=relpath,
                row_in_file=row_in_file,
                source_format="mobi_txt",
                subject_id=subject_id,
                activity_id=activity_id,
                trial_id=trial_id,
                sensor_type=sensor_type,
            )
            row["timestamp_raw"] = parts[0]
            row["timestamp_unit"] = "ns"
            if first_ts is None:
                first_ts = ts_val
            row["time_rel_sec"] = format_number((ts_val - first_ts) / 1e9)

            if sensor_type == "mobi_acc":
                row["acc_x"] = format_number(x_val)
                row["acc_y"] = format_number(y_val)
                row["acc_z"] = format_number(z_val)
            elif sensor_type == "mobi_gyro":
                row["gyro_x"] = format_number(x_val)
                row["gyro_y"] = format_number(y_val)
                row["gyro_z"] = format_number(z_val)
            else:
                row["ori_x"] = format_number(x_val)
                row["ori_y"] = format_number(y_val)
                row["ori_z"] = format_number(z_val)

            writer.writerow(row)
            stats.rows_written += 1

    return stats


def parse_hr_imu_file(
    path: Path,
    relpath: Path,
    label: str,
    dataset: str,
    writer: csv.DictWriter,
    template: Dict[str, str],
) -> FileStats:
    subject_id = extract_subject_id(relpath)
    activity_id = relpath.parts[-2] if len(relpath.parts) >= 2 else ""
    trial_id = path.stem
    source_format = "hr_imu_txt" if path.suffix.lower() == ".txt" else "hr_imu_csv"
    sensor_type = "imu_fusion"
    delimiter = "\t" if path.suffix.lower() == ".txt" else ","
    stats = FileStats(str(relpath), label, dataset, source_format, sensor_type)
    first_epoch: Optional[float] = None
    first_dt: Optional[datetime] = None

    with path.open("r", encoding="utf-8", errors="ignore", newline="") as f:
        reader = csv.reader(f, delimiter=delimiter)
        header_raw = next(reader, None)
        if not header_raw:
            return stats
        header = normalize_header_cells(header_raw)
        index = {name: idx for idx, name in enumerate(header)}

        row_in_file = 0
        for raw_row in reader:
            if not raw_row or not any(cell.strip() for cell in raw_row):
                continue
            row_in_file += 1

            row = make_base_row(
                template=template,
                label=label,
                dataset=dataset,
                relpath=relpath,
                row_in_file=row_in_file,
                source_format=source_format,
                subject_id=subject_id,
                activity_id=activity_id,
                trial_id=trial_id,
                sensor_type=sensor_type,
            )

            def get_val(name: str) -> str:
                idx = index.get(name)
                if idx is None or idx >= len(raw_row):
                    return ""
                return raw_row[idx].strip()

            # Signals
            for src_name, dst_name in [
                ("ax", "acc_x"),
                ("ay", "acc_y"),
                ("az", "acc_z"),
                ("w", "ori_w"),
                ("x", "ori_x"),
                ("y", "ori_y"),
                ("z", "ori_z"),
                ("droll", "droll"),
                ("dpitch", "dpitch"),
                ("dyaw", "dyaw"),
                ("heart", "heart"),
            ]:
                v = get_val(src_name)
                if v:
                    row[dst_name] = v

            # Parse datetime from either year/month/day/hour/minute/second or time_1..time_6.
            y = parse_int(get_val("year"))
            mo = parse_int(get_val("month"))
            d = parse_int(get_val("day"))
            h = parse_int(get_val("hour"))
            mi = parse_int(get_val("minute"))
            secf = parse_float(get_val("second"))

            if any(v is None for v in (y, mo, d, h, mi, secf)):
                y = parse_int(get_val("time_1"))
                mo = parse_int(get_val("time_2"))
                d = parse_int(get_val("time_3"))
                h = parse_int(get_val("time_4"))
                mi = parse_int(get_val("time_5"))
                secf = parse_float(get_val("time_6"))

            if not any(v is None for v in (y, mo, d, h, mi, secf)):
                sec_int = int(secf)
                micro = int(round((secf - sec_int) * 1_000_000))
                try:
                    dt = datetime(y, mo, d, h, mi, sec_int, micro, tzinfo=timezone.utc)
                    epoch = dt.timestamp()
                    row["timestamp_unit"] = "datetime"
                    row["timestamp_raw"] = f"{y:04d}-{mo:02d}-{d:02d} {h:02d}:{mi:02d}:{secf:09.6f}"
                    row["timestamp_iso_utc"] = dt.isoformat().replace("+00:00", "Z")
                    row["timestamp_epoch_sec"] = format_number(epoch)
                    if first_epoch is None:
                        first_epoch = epoch
                    if first_dt is None:
                        first_dt = dt
                    row["time_rel_sec"] = format_number((dt - first_dt).total_seconds())
                except Exception:
                    stats.parse_errors += 1

            writer.writerow(row)
            stats.rows_written += 1

    return stats


def parse_wrist_file(
    path: Path,
    relpath: Path,
    label: str,
    dataset: str,
    writer: csv.DictWriter,
    template: Dict[str, str],
) -> FileStats:
    stats = FileStats(str(relpath), label, dataset, "wrist_csv", "wrist_fusion")
    first_epoch: Optional[float] = None

    with path.open("r", encoding="utf-8", errors="ignore", newline="") as f:
        reader = csv.DictReader(f)
        row_in_file = 0
        for src in reader:
            row_in_file += 1
            subject_id = (src.get("subject_id") or "").strip()
            activity_id = (src.get("activity_id") or "").strip()
            trial_id = (src.get("trial_id") or "").strip()

            row = make_base_row(
                template=template,
                label=label,
                dataset=dataset,
                relpath=relpath,
                row_in_file=row_in_file,
                source_format="wrist_csv",
                subject_id=subject_id,
                activity_id=activity_id,
                trial_id=trial_id,
                sensor_type="wrist_fusion",
            )

            row["is_fall_raw"] = (src.get("is_fall") or "").strip()
            row["timestamp_raw"] = (src.get("time") or "").strip()
            row["timestamp_unit"] = "datetime_sec"
            row["acc_x"] = (src.get("WRST_ACC_X") or "").strip()
            row["acc_y"] = (src.get("WRST_ACC_Y") or "").strip()
            row["acc_z"] = (src.get("WRST_ACC_Z") or "").strip()
            row["wrist_ang_x"] = (src.get("WRST_ANG_X") or "").strip()
            row["wrist_ang_y"] = (src.get("WRST_ANG_Y") or "").strip()
            row["wrist_ang_z"] = (src.get("WRST_ANG_Z") or "").strip()
            row["luminosity"] = (src.get("WRST_LUMINOSITY") or "").strip()

            raw_time = row["timestamp_raw"]
            if raw_time:
                try:
                    dt = datetime.strptime(raw_time, "%d-%b-%Y %H:%M:%S").replace(tzinfo=timezone.utc)
                    epoch = dt.timestamp()
                    row["timestamp_iso_utc"] = dt.isoformat().replace("+00:00", "Z")
                    row["timestamp_epoch_sec"] = format_number(epoch)
                    if first_epoch is None:
                        first_epoch = epoch
                    row["time_rel_sec"] = format_number(epoch - first_epoch)
                except Exception:
                    stats.parse_errors += 1

            writer.writerow(row)
            stats.rows_written += 1

    return stats


def parse_fenix_file(
    path: Path,
    relpath: Path,
    label: str,
    dataset: str,
    writer: csv.DictWriter,
    template: Dict[str, str],
) -> FileStats:
    subject_id = extract_subject_id(relpath)
    activity_id = relpath.parts[-2] if len(relpath.parts) >= 2 else ""
    trial_id = path.stem
    stats = FileStats(str(relpath), label, dataset, "fenix_csv", "fenix_acc_unknown")

    with path.open("r", encoding="utf-8", errors="ignore", newline="") as f:
        reader = csv.reader(f)
        row_in_file = 0
        for raw in reader:
            if not raw or not any(cell.strip() for cell in raw):
                continue
            if len(raw) < 5:
                stats.rows_skipped += 1
                continue
            row_in_file += 1

            row = make_base_row(
                template=template,
                label=label,
                dataset=dataset,
                relpath=relpath,
                row_in_file=row_in_file,
                source_format="fenix_csv",
                subject_id=subject_id,
                activity_id=activity_id,
                trial_id=trial_id,
                sensor_type="fenix_acc_unknown",
            )
            row["fenix_c1"] = raw[0].strip()
            row["fenix_c2"] = raw[1].strip()
            row["fenix_c3"] = raw[2].strip()
            row["fenix_c4"] = raw[3].strip()
            row["fenix_c5"] = raw[4].strip()
            writer.writerow(row)
            stats.rows_written += 1

    return stats


def parse_generic_file(
    path: Path,
    relpath: Path,
    label: str,
    dataset: str,
    writer: csv.DictWriter,
    template: Dict[str, str],
) -> FileStats:
    subject_id = extract_subject_id(relpath)
    activity_id = relpath.parts[-2] if len(relpath.parts) >= 2 else ""
    trial_id = path.stem
    source_format = "generic_txt" if path.suffix.lower() == ".txt" else "generic_csv"
    stats = FileStats(str(relpath), label, dataset, source_format, "generic")

    delimiter = "\t" if path.suffix.lower() == ".txt" else ","
    with path.open("r", encoding="utf-8", errors="ignore", newline="") as f:
        reader = csv.reader(f, delimiter=delimiter)
        row_in_file = 0
        for raw in reader:
            if not raw or not any(cell.strip() for cell in raw):
                continue
            row_in_file += 1
            row = make_base_row(
                template=template,
                label=label,
                dataset=dataset,
                relpath=relpath,
                row_in_file=row_in_file,
                source_format=source_format,
                subject_id=subject_id,
                activity_id=activity_id,
                trial_id=trial_id,
                sensor_type="generic",
            )
            if len(raw) > 0:
                row["raw_1"] = raw[0].strip()
            if len(raw) > 1:
                row["raw_2"] = raw[1].strip()
            if len(raw) > 2:
                row["raw_3"] = raw[2].strip()
            writer.writerow(row)
            stats.rows_written += 1

    return stats


def iter_input_files(input_root: Path) -> List[Path]:
    files: List[Path] = []
    for label in LABEL_DIRS:
        label_dir = input_root / label
        if not label_dir.is_dir():
            continue
        for p in label_dir.rglob("*"):
            if not p.is_file():
                continue
            if p.suffix.lower() not in SUPPORTED_EXTS:
                continue
            files.append(p)
    return sorted(files)


def choose_parser(dataset: str, path: Path):
    if dataset.startswith("MobiAct_Dataset") or dataset.startswith("MobiFall_Dataset"):
        return parse_mobi_file
    if dataset.startswith("HR_IMU_falldetection_dataset-master"):
        return parse_hr_imu_file
    if dataset == "wrist_data":
        return parse_wrist_file
    if dataset == "fenix.ur.edu.pl":
        return parse_fenix_file
    return parse_generic_file


def write_report(
    report_path: Path,
    output_csv_path: Path,
    total_rows: int,
    file_stats: List[FileStats],
    rows_by_label: Counter,
    rows_by_dataset: Counter,
    rows_by_sensor: Counter,
    parse_errors: int,
) -> None:
    files_by_format = Counter(fs.source_format for fs in file_stats)
    files_by_sensor = Counter(fs.sensor_type for fs in file_stats)
    files_with_errors = [fs for fs in file_stats if fs.parse_errors > 0 or fs.rows_skipped > 0]

    with report_path.open("w", encoding="utf-8") as f:
        f.write("NORMALIZATION REPORT\n")
        f.write(f"Output file: {output_csv_path}\n")
        f.write(f"Total source files: {len(file_stats)}\n")
        f.write(f"Total normalized rows: {total_rows}\n")
        f.write(f"Total parse errors: {parse_errors}\n\n")

        f.write("Rows by label\n")
        for label, count in sorted(rows_by_label.items()):
            f.write(f"- {label}: {count}\n")
        f.write("\n")

        f.write("Rows by dataset\n")
        for ds, count in rows_by_dataset.most_common():
            f.write(f"- {ds}: {count}\n")
        f.write("\n")

        f.write("Rows by sensor_type\n")
        for sensor, count in rows_by_sensor.most_common():
            f.write(f"- {sensor}: {count}\n")
        f.write("\n")

        f.write("Files by source_format\n")
        for fmt, count in files_by_format.most_common():
            f.write(f"- {fmt}: {count}\n")
        f.write("\n")

        f.write("Files by sensor_type\n")
        for sensor, count in files_by_sensor.most_common():
            f.write(f"- {sensor}: {count}\n")
        f.write("\n")

        f.write(f"Files with skips/errors: {len(files_with_errors)}\n")
        for fs in files_with_errors[:30]:
            f.write(
                f"- {fs.source_relpath}: written={fs.rows_written}, skipped={fs.rows_skipped}, parse_errors={fs.parse_errors}\n"
            )
        if len(files_with_errors) > 30:
            f.write(f"- ... and {len(files_with_errors) - 30} more\n")


def main() -> None:
    args = parse_args()
    input_root = Path(args.input_root).resolve()
    output_dir = Path(args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    output_csv_path = output_dir / "normalized_all.csv"
    file_stats_path = output_dir / "normalized_file_stats.csv"
    report_path = output_dir / "normalization_report.txt"

    files = iter_input_files(input_root)
    template = {k: "" for k in CANONICAL_COLUMNS}
    file_stats: List[FileStats] = []

    rows_by_label: Counter = Counter()
    rows_by_dataset: Counter = Counter()
    rows_by_sensor: Counter = Counter()
    total_rows = 0
    total_parse_errors = 0

    with output_csv_path.open("w", encoding="utf-8", newline="") as f_out:
        writer = csv.DictWriter(f_out, fieldnames=CANONICAL_COLUMNS)
        writer.writeheader()

        for path in files:
            relpath = path.relative_to(input_root)
            if len(relpath.parts) < 2:
                continue
            label = relpath.parts[0]
            dataset = relpath.parts[1]
            parser = choose_parser(dataset=dataset, path=path)
            stats = parser(
                path=path,
                relpath=relpath,
                label=label,
                dataset=dataset,
                writer=writer,
                template=template,
            )
            file_stats.append(stats)
            total_rows += stats.rows_written
            total_parse_errors += stats.parse_errors
            rows_by_label[label] += stats.rows_written
            rows_by_dataset[dataset] += stats.rows_written
            rows_by_sensor[stats.sensor_type] += stats.rows_written

    with file_stats_path.open("w", encoding="utf-8", newline="") as f_stats:
        writer = csv.DictWriter(f_stats, fieldnames=FILE_STATS_COLUMNS)
        writer.writeheader()
        for fs in file_stats:
            writer.writerow(fs.to_row())

    write_report(
        report_path=report_path,
        output_csv_path=output_csv_path,
        total_rows=total_rows,
        file_stats=file_stats,
        rows_by_label=rows_by_label,
        rows_by_dataset=rows_by_dataset,
        rows_by_sensor=rows_by_sensor,
        parse_errors=total_parse_errors,
    )

    print(f"Normalized rows: {total_rows}")
    print(f"Source files processed: {len(file_stats)}")
    print(f"Output CSV: {output_csv_path}")
    print(f"File stats: {file_stats_path}")
    print(f"Report: {report_path}")


if __name__ == "__main__":
    main()
