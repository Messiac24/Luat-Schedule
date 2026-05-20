import os
import json
import gspread
from google.oauth2.service_account import Credentials
from dotenv import load_dotenv

load_dotenv()

GOOGLE_SHEETS_ID = os.getenv("GOOGLE_SHEETS_ID")
DATA_FILE = "data.json"

SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive'
]

def sync_to_sheets():
    if not GOOGLE_SHEETS_ID:
        print("Vui lòng cấu hình GOOGLE_SHEETS_ID trong .env")
        return False
        
    try:
        # Load local data
        if not os.path.exists(DATA_FILE):
            print("Không tìm thấy data.json, chưa có dữ liệu để sync.")
            return False
            
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            
        subjects = data.get("subjects", [])
        
        if not subjects:
            print("Không có môn học nào để sync.")
            return False
            
        # Auth Google Sheets
        if not os.path.exists("credentials.json"):
            print("Lỗi: Không tìm thấy credentials.json. Vui lòng thêm file này.")
            return False
            
        credentials = Credentials.from_service_account_file(
            "credentials.json", scopes=SCOPES
        )
        
        client = gspread.authorize(credentials)
        
        # Mở Sheet
        sheet = client.open_by_key(GOOGLE_SHEETS_ID).sheet1
        
        # Xóa dữ liệu cũ
        sheet.clear()
        
        # Prepare data cho Sheets
        headers = ["STT", "MÃ HP", "TÊN HỌC PHẦN", "TC", "GIẢNG VIÊN", "PHÒNG HỌC", "THỜI GIAN", "LỚP HỌC", "TRẠNG THÁI"]
        rows = [headers]
        
        for subj in subjects:
            row = [
                subj.get("stt", ""),
                subj.get("ma_hp", ""),
                subj.get("ten_hoc_phan", ""),
                subj.get("tc", ""),
                subj.get("giang_vien", ""),
                subj.get("phong_hoc", ""),
                subj.get("thoi_gian", ""),
                ", ".join(subj.get("lop_hoc", [])),
                subj.get("trang_thai", "Chưa học")
            ]
            rows.append(row)
            
        # Push data
        sheet.update('A1', rows)
        
        # Format headers
        sheet.format('A1:I1', {
            "textFormat": {"bold": True},
            "backgroundColor": {"red": 0.9, "green": 0.9, "blue": 0.9}
        })
        
        print(f"Đã sync {len(subjects)} môn học lên Google Sheets thành công!")
        return True
        
    except Exception as e:
        print(f"Lỗi khi sync lên Sheets: {e}")
        return False

if __name__ == "__main__":
    sync_to_sheets()
