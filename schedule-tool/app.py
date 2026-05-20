from flask import Flask, render_template, request, jsonify, redirect, session, url_for
import json
import os
import threading
from functools import wraps
from dotenv import load_dotenv
import gspread
from google.oauth2.service_account import Credentials

# Import from other scripts
from scraper import scrape_dlu
from sheets import sync_to_sheets

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "dev-secret-change-me")
DATA_FILE = "data.json"
GOOGLE_SHEETS_ID = os.getenv("GOOGLE_SHEETS_ID")
GOOGLE_SERVICE_ACCOUNT_JSON = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD") or (None if os.getenv("VERCEL") else "admin")

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
    "LỚP HỌC",
    "TRẠNG THÁI",
]

def sheets_enabled():
    return bool(GOOGLE_SHEETS_ID and (GOOGLE_SERVICE_ACCOUNT_JSON or os.path.exists("credentials.json")))

def get_sheet():
    if GOOGLE_SERVICE_ACCOUNT_JSON:
        credentials_info = json.loads(GOOGLE_SERVICE_ACCOUNT_JSON)
        credentials = Credentials.from_service_account_info(credentials_info, scopes=SHEET_SCOPES)
    else:
        credentials = Credentials.from_service_account_file("credentials.json", scopes=SHEET_SCOPES)

    client = gspread.authorize(credentials)
    return client.open_by_key(GOOGLE_SHEETS_ID).sheet1

def row_to_subject(index, row):
    padded = row + [""] * (len(SHEET_HEADERS) - len(row))
    classes = normalize_class_list(padded[7].split(","))
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
        "thoi_gian_goc": padded[6],
        "lop_hoc": classes,
        "trang_thai": padded[8] or "Chưa học",
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
        ", ".join(normalize_class_list(subject.get("lop_hoc", []))),
        subject.get("trang_thai", "Chưa học"),
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

def load_data():
    if sheets_enabled():
        try:
            rows = get_sheet().get_all_values()
            subjects = [row_to_subject(i, row) for i, row in enumerate(rows[1:], 1) if len(row) > 1 and row[1]]
            data = {"subjects": subjects, "last_updated": "Google Sheets"}
            # Đồng bộ ngược về database local để cập nhật cache
            try:
                with open(DATA_FILE, "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
            except Exception as e:
                print(f"Error caching Google Sheets data to local: {e}")
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
    # LUÔN LUÔN lưu dữ liệu vào database local trước (Source of Truth)
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    # Nếu có Google Sheets thì đồng bộ thêm lên Sheets
    if sheets_enabled():
        try:
            sheet = get_sheet()
            rows = [SHEET_HEADERS]
            rows.extend(subject_to_row(subject) for subject in data.get("subjects", []))
            sheet.clear()
            sheet.update("A1", rows)
        except Exception as e:
            print(f"Error updating Google Sheets: {e}")

def prepare_data_for_view():
    data = load_data()
    subjects = data.get("subjects", [])
    for original_index, subject in enumerate(subjects):
        subject["lop_hoc"] = normalize_class_list(subject.get("lop_hoc", []))
        subject["_view_index"] = original_index
        subject["schedule_entries"] = parse_schedule_time(subject.get("thoi_gian", ""))
        subject["is_low_class_count"] = len(subject.get("lop_hoc", [])) <= 2
    data["subjects"] = sorted(subjects, key=subject_view_sort_key)
    return data

def subject_view_sort_key(subject):
    status = subject.get("trang_thai", "").strip().lower()
    is_done = status == "đã học"
    return (0 if is_done else 1, subject.get("_view_index", 0))

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
    return render_template("index.html", data=prepare_data_for_view(), is_admin=False)

@app.route("/admin")
def admin():
    if not session.get("admin_logged_in"):
        return redirect(url_for("login"))
    return render_template("index.html", data=prepare_data_for_view(), is_admin=True)

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
    update_data = request.json
    subj_id = update_data.get("id")
    new_status = update_data.get("trang_thai")
    new_time = update_data.get("thoi_gian")
    new_room = update_data.get("phong_hoc")
    
    if not subj_id:
        return jsonify({"success": False, "message": "Missing ID"})
        
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
            found = True
            break
            
    if found:
        save_data(data)
        return jsonify({"success": True})
    else:
        return jsonify({"success": False, "message": "Subject not found"})

@app.route("/api/scrape", methods=["POST"])
@admin_required_json
def run_scrape():
    if os.getenv("VERCEL"):
        return jsonify({
            "success": False,
            "message": "Scraper should run outside Vercel. Update data from admin or run the scraper locally."
        }), 400

    # Run in background to avoid blocking
    def background_task():
        scrape_dlu()
        
    thread = threading.Thread(target=background_task)
    thread.start()
    return jsonify({"success": True, "message": "Scraper is running in background. Please refresh in a few minutes."})

@app.route("/api/sync", methods=["POST"])
@admin_required_json
def run_sync():
    if sheets_enabled():
        return jsonify({"success": True, "message": "Data is already stored in Google Sheets."})

    success = sync_to_sheets()
    if success:
        return jsonify({"success": True, "message": "Synced to Google Sheets successfully."})
    else:
        return jsonify({"success": False, "message": "Failed to sync. Check console logs."})

if __name__ == "__main__":
    app.run(debug=True, port=5001)
