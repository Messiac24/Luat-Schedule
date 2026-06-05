from flask import Flask, render_template, request, jsonify, redirect, session, url_for, send_file, Response, make_response
import json
import os
import threading
from io import BytesIO
from datetime import datetime, timedelta, timezone
from functools import wraps
from dotenv import load_dotenv
import gspread
import xlsxwriter
from google.oauth2.service_account import Credentials

from sheets import sync_to_sheets

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "dev-secret-change-me")
DATA_FILE = "data.json"
GOOGLE_SHEETS_ID = os.getenv("GOOGLE_SHEETS_ID")
GOOGLE_SERVICE_ACCOUNT_JSON = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD") or (
    None if os.getenv("VERCEL") else "admin"
)
ALLOWED_STATUSES = {"Chưa học", "Đã học", "Học bù"}
MAX_TIME_LENGTH = 5000
MAX_ROOM_LENGTH = 1000
VIETNAM_TZ = timezone(timedelta(hours=7))
DEFAULT_SEMESTER = "Học kỳ I"

SHEET_SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

SHEET_HEADERS = [
    "STT",
    "MÃ HP",
    "TÊN HỌC PHẦN",
    "TC",
    "GIẢNG VIÊN",
    "PHÒNG HỌC",
    "THỜI GIAN",
    "THỜI GIAN GỐC",
    "LỚP HỌC",
    "TRẠNG THÁI",
    "UPDATED_AT",
    "LAST_SCRAPED",
    "HỌC KỲ",
]

EXPORT_HEADERS = [
    "STT",
    "Mã HP",
    "Tên học phần",
    "TC",
    "Giảng viên",
    "Phòng học",
    "Thời gian",
    "Lớp học",
    "Trạng thái",
]


def sheets_enabled():
    return bool(
        GOOGLE_SHEETS_ID
        and (GOOGLE_SERVICE_ACCOUNT_JSON or os.path.exists("credentials.json"))
    )


def is_vercel_runtime():
    return bool(os.getenv("VERCEL"))


def get_sheet():
    if GOOGLE_SERVICE_ACCOUNT_JSON:
        credentials_info = json.loads(GOOGLE_SERVICE_ACCOUNT_JSON)
        credentials = Credentials.from_service_account_info(
            credentials_info, scopes=SHEET_SCOPES
        )
    else:
        credentials = Credentials.from_service_account_file(
            "credentials.json", scopes=SHEET_SCOPES
        )

    client = gspread.authorize(credentials)
    return client.open_by_key(GOOGLE_SHEETS_ID).sheet1


def row_to_subject(index, row):
    padded = row + [""] * (len(SHEET_HEADERS) - len(row))
    classes = normalize_class_list(padded[8].split(","))
    ma_hp = padded[1].strip()
    return {
        "stt": padded[0] or index,
        "id": ma_hp,
        "ma_hp": ma_hp,
        "ten_hoc_phan": padded[2],
        "tc": padded[3],
        "giang_vien": padded[4],
        "phong_hoc": padded[5],
        "thoi_gian": padded[6],
        "thoi_gian_goc": padded[7] or padded[6],
        "lop_hoc": classes,
        "trang_thai": padded[9] or "Chưa học",
        "updated_at": padded[10] or "",
        "last_scraped": padded[11] or "",
        "hoc_ky": padded[12] or DEFAULT_SEMESTER,
    }


def subject_to_row(subject):
    return [
        subject.get("stt", ""),
        subject.get("ma_hp", ""),
        subject.get("ten_hoc_phan", ""),
        subject.get("tc", ""),
        subject.get("giang_vien", ""),
        subject.get("phong_hoc", ""),
        subject.get("thoi_gian", ""),
        subject.get("thoi_gian_goc", subject.get("thoi_gian", "")),
        ", ".join(normalize_class_list(subject.get("lop_hoc", []))),
        subject.get("trang_thai", "Chưa học"),
        subject.get("updated_at", ""),
        subject.get("last_scraped", ""),
        subject.get("hoc_ky", DEFAULT_SEMESTER),
    ]


def normalize_class_name(value):
    return " ".join(str(value).strip().replace("\u00d0", "\u0110").split())


def normalize_class_list(values):
    normalized = []
    for value in values:
        class_name = normalize_class_name(value)
        if class_name and class_name not in normalized:
            normalized.append(class_name)
    return normalized


def normalize_filter_text(value):
    return " ".join(str(value or "").strip().lower().split())


def now_vietnam_iso():
    return datetime.now(VIETNAM_TZ).isoformat()


def validate_optional_text(value, max_length, field_name):
    if value is None:
        return None, None
    if not isinstance(value, str):
        return None, f"{field_name} must be text"
    if len(value) > max_length:
        return None, f"{field_name} is too long"
    return value, None


def filter_export_subjects(
    subjects,
    class_filter="",
    semester_filter="",
    subject_filter="",
    teacher_filter="",
):
    class_filter = normalize_filter_text(class_filter)
    semester_filter = normalize_filter_text(semester_filter)
    subject_filter = normalize_filter_text(subject_filter)
    teacher_filter = normalize_filter_text(teacher_filter)
    filtered = []

    for subject in subjects:
        classes = [
            normalize_filter_text(class_name)
            for class_name in normalize_class_list(subject.get("lop_hoc", []))
        ]
        semester = normalize_filter_text(subject.get("hoc_ky", DEFAULT_SEMESTER))
        subject_name = normalize_filter_text(subject.get("ten_hoc_phan", ""))
        teacher = normalize_filter_text(subject.get("giang_vien", ""))

        if class_filter and class_filter not in classes:
            continue
        if semester_filter and semester_filter != semester:
            continue
        if subject_filter and subject_filter != subject_name:
            continue
        if teacher_filter and teacher_filter != teacher:
            continue
        filtered.append(subject)

    return filtered


def export_subject_to_row(index, subject):
    return [
        index,
        subject.get("ma_hp", ""),
        subject.get("ten_hoc_phan", ""),
        subject.get("tc", ""),
        subject.get("giang_vien", ""),
        subject.get("phong_hoc", ""),
        subject.get("thoi_gian", ""),
        ", ".join(normalize_class_list(subject.get("lop_hoc", []))),
        subject.get("trang_thai", ""),
    ]


def build_export_xlsx(subjects):
    rows = [EXPORT_HEADERS]
    rows.extend(export_subject_to_row(index, subject) for index, subject in enumerate(subjects, 1))

    output = BytesIO()
    workbook = xlsxwriter.Workbook(output, {"in_memory": True, "strings_to_urls": False})
    worksheet = workbook.add_worksheet("Lich hoc")
    header_format = workbook.add_format(
        {
            "bold": True,
            "font_color": "white",
            "bg_color": "#111827",
            "border": 1,
            "align": "center",
            "valign": "vcenter",
        }
    )
    body_format = workbook.add_format(
        {"border": 1, "valign": "top", "text_wrap": True}
    )

    widths = [8, 14, 36, 8, 24, 18, 48, 28, 18]
    for col_index, width in enumerate(widths):
        worksheet.set_column(col_index, col_index, width)

    for row_index, row in enumerate(rows):
        for col_index, value in enumerate(row):
            cell_format = header_format if row_index == 0 else body_format
            worksheet.write(row_index, col_index, value, cell_format)

    worksheet.freeze_panes(1, 0)
    worksheet.autofilter(0, 0, max(len(rows) - 1, 0), len(EXPORT_HEADERS) - 1)
    workbook.close()
    output.seek(0)
    return output.getvalue()


def latest_subject_updated_at(subjects):
    latest = datetime.min
    for subject in subjects:
        for field_name in ("last_scraped", "updated_at"):
            updated_at = parse_updated_at(subject.get(field_name, ""))
            if updated_at > latest:
                latest = updated_at
    return latest.isoformat() if latest != datetime.min else ""


def cache_local_data(data):
    if is_vercel_runtime():
        return True

    try:
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print(f"Error caching data to local file: {e}")
        return False


def load_data():
    if sheets_enabled():
        try:
            rows = get_sheet().get_all_values()
            subjects = [
                row_to_subject(i, row)
                for i, row in enumerate(rows[1:], 1)
                if len(row) > 1 and row[1]
            ]
            data = {
                "subjects": subjects,
                "last_updated": latest_subject_updated_at(subjects),
            }
            cache_local_data(data)
            return data
        except Exception as e:
            print(f"Error loading Google Sheets data: {e}")

    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"subjects": [], "last_updated": ""}


def save_data(data):
    data["last_updated"] = now_vietnam_iso()
    if sheets_enabled():
        try:
            sheet = get_sheet()
            rows = [SHEET_HEADERS]
            rows.extend(subject_to_row(subject) for subject in data.get("subjects", []))
            sheet.clear()
            sheet.update("A1", rows)
            cache_local_data(data)
            return True
        except Exception as e:
            print(f"Error updating Google Sheets: {e}")
            return False

    return cache_local_data(data)


def render_no_store_template(template_name, **context):
    response = make_response(render_template(template_name, **context))
    response.headers["Cache-Control"] = "no-store, max-age=0"
    return response


def prepare_data_for_view():
    data = load_data()
    subjects = data.get("subjects", [])
    for original_index, subject in enumerate(subjects):
        subject["lop_hoc"] = normalize_class_list(subject.get("lop_hoc", []))
        subject["hoc_ky"] = subject.get("hoc_ky") or DEFAULT_SEMESTER
        subject["_view_index"] = original_index
        subject["schedule_entries"] = parse_schedule_time(subject.get("thoi_gian", ""))
        subject["schedule_sort_value"] = schedule_sort_value(
            subject.get("thoi_gian", "")
        )
        subject["is_low_class_count"] = len(subject.get("lop_hoc", [])) <= 2
    data["subjects"] = sorted(subjects, key=subject_view_sort_key)
    return data


def parse_updated_at(value):
    try:
        parsed = datetime.fromisoformat(value)
        if parsed.tzinfo:
            return parsed.astimezone(VIETNAM_TZ).replace(tzinfo=None)
        return parsed
    except Exception:
        return datetime.min


def subject_view_sort_key(subject):
    status = subject.get("trang_thai", "").strip().lower()
    status_priority = {
        "chưa học": 0,
        "học bù": 1,
        "đã học": 2,
    }
    if status == "chưa học":
        return (
            0,
            parse_schedule_sort_value(subject.get("schedule_sort_value", "")),
            subject.get("_view_index", 0),
        )
    return (
        status_priority.get(status, 1),
        parse_updated_at(subject.get("updated_at", "")),
        subject.get("_view_index", 0),
    )


def admin_required_json(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("admin_logged_in"):
            return jsonify({"success": False, "message": "Unauthorized"}), 401
        return view(*args, **kwargs)

    return wrapped


def parse_schedule_time(value):
    entries = []
    current_entry = None

    for raw_line in (value or "").splitlines():
        line = raw_line.strip()
        if not line:
            continue

        if line.startswith("-"):
            period = line.lstrip("-").strip()
            if current_entry is None:
                current_entry = {"date": "", "periods": []}
                entries.append(current_entry)
            current_entry["periods"].append(period)
            continue

        date_text = line
        period_text = ""
        if " - " in line:
            date_text, period_text = line.split(" - ", 1)

        current_entry = {"date": date_text.strip(), "periods": []}
        if period_text:
            current_entry["periods"].append(period_text.strip())
        entries.append(current_entry)

    for entry in entries:
        entry["periods"] = compact_periods(entry["periods"])

    return entries


def schedule_sort_value(value):
    for entry in parse_schedule_time(value):
        date_text = entry.get("date", "").split("(", 1)[0].strip()
        try:
            return datetime.strptime(date_text, "%d/%m/%Y").strftime("%Y-%m-%d")
        except ValueError:
            continue
    return ""


def parse_schedule_sort_value(value):
    try:
        return datetime.strptime(value, "%Y-%m-%d")
    except ValueError:
        return datetime.max


def clean_period_label(period):
    label = period.replace("(Trực tiếp)", "")
    label = label.replace("(Trực tuyến)", "")
    return " ".join(label.split())


def compact_periods(periods):
    cleaned = []
    for period in periods:
        label = clean_period_label(period)
        if label and label not in cleaned:
            cleaned.append(label)

    has_morning = "Sáng" in cleaned
    has_afternoon = "Chiều" in cleaned
    if has_morning and has_afternoon:
        compacted = ["Sáng - Chiều"]
        compacted.extend(label for label in cleaned if label not in {"Sáng", "Chiều"})
        return compacted

    return cleaned


@app.route("/")
def index():
    return render_no_store_template(
        "index.html",
        data=prepare_data_for_view(),
        is_admin=False,
        can_edit=False,
        view_mode="view",
        sheets_enabled=sheets_enabled(),
        is_vercel=is_vercel_runtime(),
    )


@app.route("/manifest.webmanifest")
def manifest():
    with open(os.path.join(app.static_folder, "manifest.webmanifest"), encoding="utf-8") as f:
        return Response(f.read(), mimetype="application/manifest+json")


@app.route("/service-worker.js")
def service_worker():
    with open(os.path.join(app.static_folder, "service-worker.js"), encoding="utf-8") as f:
        response = Response(f.read(), mimetype="application/javascript")
    response.headers["Cache-Control"] = "no-cache"
    return response


@app.route("/admin")
def admin():
    if not session.get("admin_logged_in"):
        return redirect(url_for("login"))
    view_mode = request.args.get("mode", "edit")
    can_edit = view_mode != "view"
    return render_no_store_template(
        "index.html",
        data=prepare_data_for_view(),
        is_admin=True,
        can_edit=can_edit,
        view_mode=view_mode,
        sheets_enabled=sheets_enabled(),
        is_vercel=is_vercel_runtime(),
    )


@app.route("/api/export.xlsx")
def export_excel():
    data = prepare_data_for_view()
    subjects = filter_export_subjects(
        data.get("subjects", []),
        class_filter=request.args.get("class", ""),
        semester_filter=request.args.get("semester", ""),
        subject_filter=request.args.get("subject", ""),
        teacher_filter=request.args.get("teacher", ""),
    )
    workbook = BytesIO(build_export_xlsx(subjects))
    today = datetime.now(VIETNAM_TZ).strftime("%Y%m%d")
    return send_file(
        workbook,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        as_attachment=True,
        download_name=f"lich-hoc-{today}.xlsx",
    )


@app.route("/login", methods=["GET", "POST"])
def login():
    error = ""
    if request.method == "POST":
        if not ADMIN_PASSWORD:
            error = "Admin password is not configured."
        elif request.form.get("password") == ADMIN_PASSWORD:
            session["admin_logged_in"] = True
            return redirect(url_for("admin"))
        else:
            error = "Sai mật khẩu."
    return render_template("login.html", error=error)


@app.route("/logout", methods=["POST"])
def logout():
    session.clear()
    return redirect(url_for("index"))


@app.route("/api/update", methods=["POST"])
@admin_required_json
def update_subject():
    update_data = request.get_json(silent=True) or {}
    subj_id = str(update_data.get("id", "")).strip()
    new_status = update_data.get("trang_thai")
    new_time = update_data.get("thoi_gian")
    new_room = update_data.get("phong_hoc")

    if not subj_id:
        return jsonify({"success": False, "message": "Missing ID"}), 400

    if new_status is not None:
        new_status = str(new_status).strip()
        if new_status not in ALLOWED_STATUSES:
            return jsonify({"success": False, "message": "Invalid status"}), 400

    new_time, time_error = validate_optional_text(
        new_time, MAX_TIME_LENGTH, "thoi_gian"
    )
    if time_error:
        return jsonify({"success": False, "message": time_error}), 400

    new_room, room_error = validate_optional_text(
        new_room, MAX_ROOM_LENGTH, "phong_hoc"
    )
    if room_error:
        return jsonify({"success": False, "message": room_error}), 400

    data = load_data()
    subjects = data.get("subjects", [])

    found = False
    for subj in subjects:
        if subj.get("id") == subj_id:
            if new_status:
                subj["trang_thai"] = new_status
            if new_time is not None:
                subj["thoi_gian"] = new_time
            if new_room is not None:
                subj["phong_hoc"] = new_room
            subj["updated_at"] = now_vietnam_iso()
            found = True
            break

    if found:
        if not save_data(data):
            return jsonify({"success": False, "message": "Unable to save data"}), 500
        return jsonify({"success": True, "subject": subj})
    else:
        return jsonify({"success": False, "message": "Subject not found"}), 404


@app.route("/api/reset", methods=["POST"])
@admin_required_json
def reset_subject():
    request_data = request.get_json(silent=True) or {}
    subj_id = str(request_data.get("id", "")).strip()
    if not subj_id:
        return jsonify({"success": False, "message": "Missing ID"}), 400

    data = load_data()
    subjects = data.get("subjects", [])
    found = False

    for subj in subjects:
        if subj.get("id") == subj_id:
            subj["thoi_gian"] = subj.get("thoi_gian_goc", subj.get("thoi_gian", ""))
            subj["trang_thai"] = "Chưa học"
            subj["updated_at"] = now_vietnam_iso()
            found = True
            reset_subject = subj
            break

    if found:
        if not save_data(data):
            return jsonify({"success": False, "message": "Unable to save data"}), 500
        return jsonify(
            {
                "success": True,
                "subject": {
                    "id": reset_subject.get("id"),
                    "thoi_gian": reset_subject.get("thoi_gian"),
                    "trang_thai": reset_subject.get("trang_thai"),
                    "phong_hoc": reset_subject.get("phong_hoc", ""),
                    "updated_at": reset_subject.get("updated_at", ""),
                },
            }
        )
    else:
        return jsonify({"success": False, "message": "Subject not found"}), 404


@app.route("/api/scrape", methods=["POST"])
@admin_required_json
def run_scrape():
    if is_vercel_runtime():
        return jsonify(
            {
                "success": False,
                "message": "Scraper should run outside Vercel. Update data from admin or run the scraper locally.",
            }
        ), 400

    from scraper import scrape_dlu

    # Run in background to avoid blocking
    def background_task():
        scrape_dlu()

    thread = threading.Thread(target=background_task)
    thread.start()
    return jsonify(
        {
            "success": True,
            "message": "Scraper is running in background. Please refresh in a few minutes.",
        }
    )


@app.route("/api/sync", methods=["POST"])
@admin_required_json
def run_sync():
    if not sheets_enabled():
        return (
            jsonify(
                {
                    "success": False,
                    "message": "Google Sheets chưa được cấu hình hoặc cấu hình chưa hợp lệ.",
                }
            ),
            400,
        )

    success = sync_to_sheets()
    if success:
        return jsonify(
            {"success": True, "message": "Đã đồng bộ lên Google Sheets thành công."}
        )
    else:
        return jsonify(
            {"success": False, "message": "Không thể đồng bộ. Kiểm tra log server."}
        )


if __name__ == "__main__":
    debug_mode = True
    if os.getenv("WERKZEUG_RUN_MAIN") == "true" or not debug_mode:
        from auto_scrape import start_background_scheduler

        start_background_scheduler()
    app.run(debug=debug_mode, port=5001)
