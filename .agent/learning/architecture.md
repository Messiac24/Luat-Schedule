---

### Hệ thống Scraper & Admin Đồng bộ Gsheet
- **Ngày**: 2026-05-20
- **Task**: Xây dựng tool cào dữ liệu lịch học DLU Online và cho phép Admin cập nhật trạng thái/giờ học bù.
- **Chi tiết**: Dùng kiến trúc 3 thành phần: Playwright (Scraper) để lấy dữ liệu tĩnh, Flask (Web Admin) để chỉnh sửa các trường động (trạng thái, thời gian), Google Sheets API để đồng bộ cho người dùng xem chung. Storage local là file JSON đóng vai trò Source of Truth (ghi đè data tĩnh, giữ data động của admin).
- **Files liên quan**: `schedule-tool/scraper.py`, `schedule-tool/app.py`, `schedule-tool/sheets.py`
