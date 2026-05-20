# DLU Schedule Tracker

Hệ thống theo dõi lịch học DLU tự động bằng Python (Playwright + Flask) và đồng bộ Google Sheets.

## Cấu trúc
- `scraper.py`: Dùng Playwright tự động đăng nhập và cào dữ liệu từ DLU, merge với dữ liệu cũ (giữ lại các chỉnh sửa của Admin).
- `app.py`: Giao diện Admin bằng Flask cho phép cập nhật trạng thái môn học (Chưa học, Đã học, Học bù).
- `sheets.py`: Đồng bộ dữ liệu lên Google Sheets.

## Cài đặt

1. Yêu cầu hệ thống:
   - Python 3.8+
   - Trình duyệt Chrome/Edge hoặc cài đặt Playwright Chromium

2. Cài đặt thư viện:
   ```cmd
   cd schedule-tool
   pip install -r requirements.txt
   playwright install chromium
   ```

3. Cấu hình Credentials:
   - Đổi tên file `.env.example` thành `.env`
   - Điền thông tin đăng nhập DLU và Google Sheets ID.
   - Thêm file `credentials.json` (Google Service Account key) vào thư mục `schedule-tool`.

## Hướng dẫn sử dụng

### Deploy public web + admin
Ứng dụng có 2 khu vực:
- `/`: trang công khai cho người dùng xem lịch, không cần tài khoản.
- `/admin`: trang quản trị để cập nhật trạng thái/thời gian/phòng học.

Khi deploy lên Vercel, đặt root directory là `schedule-tool` và cấu hình env:
- `ADMIN_PASSWORD`: mật khẩu đăng nhập admin.
- `SECRET_KEY`: chuỗi bí mật cho Flask session.
- `GOOGLE_SHEETS_ID`: ID Google Sheet dùng làm storage bền.
- `GOOGLE_SERVICE_ACCOUNT_JSON`: nội dung JSON của Google Service Account key.

Lưu ý: không dùng `data.json` làm storage chính trên Vercel vì filesystem của serverless function không bền. Nếu cần scrape tự động, chạy scraper ở máy local/GitHub Actions/VPS rồi cập nhật Google Sheets.

### 1. Chạy Web Admin (Local)
Mở terminal và chạy lệnh:
```cmd
python app.py
```
Sau đó truy cập: `http://localhost:5000`

Tại đây bạn có thể:
- Xem bảng lịch học
- Sửa trạng thái (Chưa học, Đã học, Học bù)
- Nhấn "Lưu" để sửa thời gian nếu môn đó là "Học bù"
- Nhấn "Scrape Mới" để cào lại lịch ngay lập tức (chạy ngầm).
- Nhấn "Sync Lên Google Sheets" để đẩy dữ liệu.

### 2. Thiết lập chạy tự động (Windows Task Scheduler)
Để cào dữ liệu tự động mỗi 2-3 ngày, bạn có thể tạo một Task Scheduler gọi file bat:

Tạo file `run_scraper.bat`:
```bat
@echo off
cd /d "D:\01_Projects\luat_dlu_prj\schedule-tool"
python scraper.py
python sheets.py
```

Mở Task Scheduler (Windows), tạo một Basic Task để chạy file `run_scraper.bat` mỗi 2 hoặc 3 ngày.
