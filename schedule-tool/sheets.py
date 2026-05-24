import json
import os

import gspread
from dotenv import load_dotenv
from google.oauth2.service_account import Credentials

load_dotenv()

GOOGLE_SHEETS_ID = os.getenv("GOOGLE_SHEETS_ID")
GOOGLE_SERVICE_ACCOUNT_JSON = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON")
DATA_FILE = "data.json"

SCOPES = [
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


def sheets_enabled():
    return bool(
        GOOGLE_SHEETS_ID
        and (GOOGLE_SERVICE_ACCOUNT_JSON or os.path.exists("credentials.json"))
    )


def get_credentials():
    if GOOGLE_SERVICE_ACCOUNT_JSON:
        credentials_info = json.loads(GOOGLE_SERVICE_ACCOUNT_JSON)
        return Credentials.from_service_account_info(credentials_info, scopes=SCOPES)
    return Credentials.from_service_account_file("credentials.json", scopes=SCOPES)


def get_sheet():
    client = gspread.authorize(get_credentials())
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
    ]


def load_local_data():
    if not os.path.exists(DATA_FILE):
        return {"subjects": [], "last_updated": ""}
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def load_from_sheets():
    if not sheets_enabled():
        return None

    rows = get_sheet().get_all_values()
    subjects = [
        row_to_subject(i, row)
        for i, row in enumerate(rows[1:], 1)
        if len(row) > 1 and row[1]
    ]
    if not subjects:
        return None
    return {"subjects": subjects, "last_updated": "Google Sheets"}


def sync_to_sheets(data=None):
    if not GOOGLE_SHEETS_ID:
        print("Vui lòng cấu hình GOOGLE_SHEETS_ID trong .env")
        return False

    try:
        data = data or load_local_data()
        subjects = data.get("subjects", [])
        if not subjects:
            print("Không có môn học nào để sync.")
            return False

        if not sheets_enabled():
            print("Google Sheets credentials chưa được cấu hình.")
            return False

        sheet = get_sheet()
        rows = [SHEET_HEADERS]
        rows.extend(subject_to_row(subject) for subject in subjects)

        sheet.clear()
        sheet.update("A1", rows)
        sheet.format(
            "A1:L1",
            {
                "textFormat": {"bold": True},
                "backgroundColor": {"red": 0.9, "green": 0.9, "blue": 0.9},
            },
        )
        print(f"Đã sync {len(subjects)} môn học lên Google Sheets thành công!")
        return True

    except Exception as e:
        print(f"Lỗi khi sync lên Sheets: {e}")
        return False


if __name__ == "__main__":
    sync_to_sheets()
