import os
import json
import sys
import time
import requests as req_lib
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright
from sheets import load_from_sheets


def configure_utf8_output(stdout=None, stderr=None):
    stdout = stdout or sys.stdout
    stderr = stderr or sys.stderr
    for stream in (stdout, stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")


configure_utf8_output()

# Load environment variables
load_dotenv()

USERNAME = os.getenv("DLU_USERNAME")
PASSWORD = os.getenv("DLU_PASSWORD")
TARGET_CLASSES_STR = os.getenv("TARGET_CLASSES", "")
TARGET_CLASSES = [c.strip() for c in TARGET_CLASSES_STR.split(",") if c.strip()]

DATA_FILE = "data.json"
VIETNAM_TZ = timezone(timedelta(hours=7))


def now_vietnam_iso():
    return datetime.now(VIETNAM_TZ).isoformat()


def normalize_class_name(value):
    return " ".join(str(value).strip().replace("\u00d0", "\u0110").split())


def normalize_class_list(values):
    normalized = []
    for value in values:
        class_name = normalize_class_name(value)
        if class_name and class_name not in normalized:
            normalized.append(class_name)
    return normalized


def extract_start_period(value):
    digits = "".join(ch for ch in str(value) if ch.isdigit())
    return int(digits) if digits else 0


def is_weekend_daytime_entry(item):
    day_of_week = item.get("DayOfWeek", 0)
    start_period = extract_start_period(item.get("BeginTime", ""))
    return day_of_week in {6, 7} and start_period in {1, 7}


def filter_weekend_daytime_entries(entries):
    return [item for item in entries if is_weekend_daytime_entry(item)]


def load_local_data():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading {DATA_FILE}: {e}")
    return {"subjects": [], "last_updated": ""}


def load_existing_data():
    try:
        sheets_data = load_from_sheets()
        if sheets_data:
            return sheets_data
    except Exception as e:
        print(f"Không thể đọc dữ liệu hiện tại từ Google Sheets: {e}")
    return load_local_data()


def save_local_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def merge_data(existing_data, new_subjects):
    """Merge new scraped data with existing data, preserving admin edits."""
    existing_map = {item["id"]: item for item in existing_data.get("subjects", [])}
    merged_subjects = []
    now_iso = now_vietnam_iso()

    for new_subj in new_subjects:
        subj_id = new_subj["id"]
        if subj_id in existing_map:
            existing_subj = existing_map[subj_id]
            existing_subj["stt"] = new_subj["stt"]
            existing_subj["ten_hoc_phan"] = new_subj["ten_hoc_phan"]
            existing_subj["tc"] = new_subj["tc"]
            existing_subj["giang_vien"] = new_subj["giang_vien"]
            existing_subj["thoi_gian_goc"] = new_subj["thoi_gian_goc"]
            existing_subj["lop_hoc"] = new_subj["lop_hoc"]
            existing_subj["last_scraped"] = new_subj["last_scraped"]
            existing_subj["updated_at"] = (
                existing_subj.get("updated_at") or now_iso
            )
            # Preserve admin-managed fields: status, active time, and room edits.
            merged_subjects.append(existing_subj)
        else:
            new_subj["updated_at"] = now_iso
            merged_subjects.append(new_subj)

    return {"subjects": merged_subjects, "last_updated": now_iso}


def scrape_dlu():
    if not USERNAME or not PASSWORD:
        print("Vui lòng cấu hình DLU_USERNAME và DLU_PASSWORD trong .env")
        return False

    if not TARGET_CLASSES:
        print("Vui lòng cấu hình TARGET_CLASSES trong .env")
        return False

    print(f"Đang chạy scraper vào lúc {now_vietnam_iso()}")
    print(f"Lớp cần lấy: {TARGET_CLASSES}")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        try:
            # === BƯỚC 1: Đăng nhập ===
            print("Đang truy cập trang đăng nhập...")
            page.goto("https://online.dlu.edu.vn/login")
            page.wait_for_selector(
                "input[type='text'], input[name='username'], input[placeholder*='Mã']",
                timeout=10000,
            )

            page.fill("input[type='text'], input[name='username']", USERNAME)
            page.fill("input[type='password']", PASSWORD)

            print("Đang đăng nhập...")
            page.click("button[type='submit'], button:has-text('Đăng nhập')")
            page.wait_for_url("**/student**", timeout=15000)
            print("Đăng nhập thành công!")

            # === BƯỚC 2: Vào trang lịch học ===
            print("Đang chuyển đến trang lịch học...")
            page.goto("https://online.dlu.edu.vn/student/schedules")
            page.wait_for_timeout(3000)

            # === BƯỚC 3: Bắt auth headers từ API request đầu tiên ===
            captured_headers = {}

            def capture_request(request):
                if "portal-api.dlu.edu.vn" in request.url:
                    captured_headers.update(dict(request.headers))

            page.on("request", capture_request)

            # Click tab "Thời khóa biểu theo lớp" để trigger API call
            print("Đang mở tab 'Thời khóa biểu theo lớp'...")
            tab = page.locator("button:has-text('Thời khóa biểu theo lớp')")
            if tab.count() > 0:
                tab.click()
                page.wait_for_timeout(3000)

            if not captured_headers:
                print("LỖI: Không bắt được headers từ API request. Không thể tiếp tục.")
                return False

            print(f"Bắt được auth headers: {list(captured_headers.keys())}")

            # === BƯỚC 4: Dùng Python requests với headers đã bắt ===
            session = req_lib.Session()
            session.headers.update(captured_headers)

            # Lấy cookies từ cả 2 domain
            all_cookies = page.context.cookies(
                ["https://online.dlu.edu.vn", "https://portal-api.dlu.edu.vn"]
            )
            for cookie in all_cookies:
                session.cookies.set(
                    cookie["name"], cookie["value"], domain=cookie.get("domain", "")
                )
            print(f"Có {len(all_cookies)} cookies.")

            # === BƯỚC 5: Lấy danh sách tuần và dữ liệu cho nhiều học kỳ ===
            semesters = [
                ("2024-2025", "HK02"),
                ("2024-2025", "HK03"),
                ("2025-2026", "HK01"),
                ("2025-2026", "HK02"),
                ("2025-2026", "HK03"),
            ]

            all_raw_data = []
            api_base = "https://portal-api.dlu.edu.vn"

            for namhoc, hocky in semesters:
                print(f"\n--- Đang xử lý Học kỳ {hocky} Năm học {namhoc} ---")
                weeks_url = (
                    f"{api_base}/api/student/WeekSchedule?namhoc={namhoc}&hocky={hocky}"
                )

                try:
                    weeks_resp = session.get(weeks_url, timeout=15)
                    if weeks_resp.status_code != 200:
                        print(
                            f"LỖI: Không lấy được tuần cho {namhoc} {hocky}. Status: {weeks_resp.status_code}"
                        )
                        continue

                    weeks_data = weeks_resp.json()
                    unique_weeks = sorted(set(w["Week"] for w in weeks_data))
                    print(f"Có {len(unique_weeks)} tuần.")

                    for class_id in TARGET_CLASSES:
                        print(f"  Đang lấy lịch lớp {class_id}...")
                        class_count = 0

                        for week_num in unique_weeks:
                            url = f"{api_base}/api/student/DrawingClassSchedule?ClassStudentID={class_id}&namhoc={namhoc}&hocky={hocky}&tuan={week_num}"
                            try:
                                resp = session.get(url, timeout=10)
                                if resp.status_code == 200:
                                    data = resp.json()
                                    if (
                                        data
                                        and isinstance(data, list)
                                        and len(data) > 0
                                    ):
                                        for item in data:
                                            item["_class_id"] = class_id
                                            item["_week"] = week_num
                                            all_raw_data.append(item)
                                            class_count += 1
                                elif resp.status_code == 401:
                                    print(
                                        f"    LỖI 401 ở tuần {week_num} - auth hết hạn!"
                                    )
                                    return False
                            except req_lib.exceptions.Timeout:
                                pass
                            except Exception as e:
                                pass

                        print(f"    -> {class_count} entries")
                except Exception as e:
                    print(f"Lỗi khi xử lý HK {hocky} {namhoc}: {e}")

            print(f"\nTổng raw data: {len(all_raw_data)} entries.")

            with open("api_dump.json", "w", encoding="utf-8") as f:
                json.dump(all_raw_data, f, ensure_ascii=False, indent=2)
            print("Đã lưu raw data vào api_dump.json")

            # === BƯỚC 7: Chỉ giữ Thứ 7/Chủ Nhật, ca Sáng/Chiều ===
            all_raw_data = filter_weekend_daytime_entries(all_raw_data)
            print(
                f"Sau khi lọc chỉ giữ Thứ 7/Chủ Nhật ca Sáng/Chiều: {len(all_raw_data)} entries."
            )

            # === BƯỚC 8: Transform thành format data.json ===
            import re

            scrape_started_at = now_vietnam_iso()
            subjects_map = {}
            for item in all_raw_data:
                raw_html = item.get("TKHHienThi", "")

                # Extract Ma HP
                ma_hp_match = (
                    re.search(r"\(([\w\d]+)\)", raw_html.split("<br/>")[0])
                    if raw_html
                    else None
                )
                ma_hp = (
                    ma_hp_match.group(1)
                    if ma_hp_match
                    else item.get("ScheduleStudyUnitID", "")
                )

                if not ma_hp:
                    continue

                # Tính số tín chỉ từ "Đã học: X/Y tiết"
                tc = 0
                da_hoc_match = (
                    re.search(r"Đã học: \d+/(\d+) tiết", raw_html) if raw_html else None
                )
                if da_hoc_match:
                    total_tiet = int(da_hoc_match.group(1))
                    tc = total_tiet // 15

                # Trích xuất danh sách lớp từ HTML nếu có, hoặc dùng lớp đang lấy
                lop_hoc = normalize_class_list(item.get("ClassName", "").split(","))

                # Bỏ qua các môn GDTC và GDQP
                ten_hp = item.get("CurriculumName", "")
                if "Giáo dục thể chất" in ten_hp or "Giáo dục Quốc phòng" in ten_hp:
                    continue

                cid = normalize_class_name(item.get("_class_id", ""))
                if cid and cid not in lop_hoc:
                    lop_hoc.append(cid)

                day_int = item.get("DayOfWeek", 0)
                day_map = {
                    1: "Thứ Hai",
                    2: "Thứ Ba",
                    3: "Thứ Tư",
                    4: "Thứ Năm",
                    5: "Thứ Sáu",
                    6: "Thứ Bảy",
                    7: "Chủ Nhật",
                }
                day = day_map.get(day_int, item.get("Thu", ""))

                ngay = item.get("Ngay", "")

                start = str(extract_start_period(item.get("BeginTime", "")))
                end = str(item.get("EndTime", "")).strip()

                session_name = f"Tiết {start}-{end}"
                if start == "1":
                    session_name = "Sáng"
                elif start == "7":
                    session_name = "Chiều"

                room_str = item.get("RoomID", "")
                mode = "Trực tuyến" if "Online" in room_str else "Trực tiếp"

                date_key = f"{ngay} ({day})" if ngay else ""
                period_str = f"{session_name} ({mode})"

                if ma_hp not in subjects_map:
                    subjects_map[ma_hp] = {
                        "id": ma_hp,
                        "ma_hp": ma_hp,
                        "ten_hoc_phan": item.get("CurriculumName", ""),
                        "tc": tc,
                        "giang_vien": item.get("FullName", ""),
                        "phong_hoc": "",
                        "thoi_gian": "",
                        "thoi_gian_goc": "",
                        "lop_hoc": lop_hoc,
                        "trang_thai": "Chưa học",
                        "last_scraped": scrape_started_at,
                        "_schedule_data": {},
                        "_seen_rooms": set(),
                    }

                subj = subjects_map[ma_hp]
                for l in lop_hoc:
                    if l not in subj["lop_hoc"]:
                        subj["lop_hoc"].append(l)

                if date_key:
                    if date_key not in subj["_schedule_data"]:
                        subj["_schedule_data"][date_key] = []
                    if period_str not in subj["_schedule_data"][date_key]:
                        subj["_schedule_data"][date_key].append(period_str)

                if room_str and room_str not in subj["_seen_rooms"]:
                    subj["_seen_rooms"].add(room_str)
                    if subj["phong_hoc"]:
                        subj["phong_hoc"] += f"\n{room_str}"
                    else:
                        subj["phong_hoc"] = room_str

            # Render grouped time strings
            def parse_date_key(date_key):
                """Extract date from '18/04/2026 (Thứ Bảy)' for sorting."""
                try:
                    date_part = date_key.split(" (")[0].strip()
                    return datetime.strptime(date_part, "%d/%m/%Y")
                except (ValueError, IndexError):
                    return datetime.max

            for subj in subjects_map.values():
                lines = []
                sorted_dates = sorted(
                    subj["_schedule_data"].items(), key=lambda x: parse_date_key(x[0])
                )
                for date_key, periods in sorted_dates:
                    if len(periods) == 1:
                        lines.append(f"{date_key} - {periods[0]}")
                    else:
                        lines.append(f"{date_key}")
                        for p in periods:
                            lines.append(f"  - {p}")

                subj["thoi_gian"] = "\n".join(lines)
                subj["thoi_gian_goc"] = subj["thoi_gian"]

                subj.pop("_schedule_data", None)
                subj.pop("_seen_rooms", None)

            subjects_list = list(subjects_map.values())
            for i, subj in enumerate(subjects_list, 1):
                subj["stt"] = i

            print(f"Đã transform thành {len(subjects_list)} môn học.")

            # Merge và lưu
            existing_data = load_existing_data()
            merged_data = merge_data(existing_data, subjects_list)
            save_local_data(merged_data)

            print(f"Đã lưu {len(subjects_list)} môn học vào data.json")

            # Tự động đồng bộ lên Google Sheets nếu được cấu hình
            try:
                from sheets import sync_to_sheets

                print("Đang đồng bộ dữ liệu sau khi cào lên Google Sheets...")
                sync_to_sheets(merged_data)
            except Exception as e:
                print(f"Không thể tự động đồng bộ lên Google Sheets: {e}")

            print("Scrape hoàn tất!")
            return True

        except Exception as e:
            print(f"LỖI: {e}")
            import traceback

            traceback.print_exc()
            return False

        finally:
            browser.close()


if __name__ == "__main__":
    scrape_dlu()
