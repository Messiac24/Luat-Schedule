---

### Workflow kết hợp Scrape - Modify - Sync (Local to Google Sheets)
- **Ngày**: 2026-05-20
- **Task**: Cách tách biệt dữ liệu cào tự động và dữ liệu cập nhật thủ công.
- **Chi tiết**: Khi merge dữ liệu từ scraper vào local file: Lặp qua dữ liệu mới, nếu ID đã tồn tại thì CHỈ cập nhật thông tin gốc (tên, GV, phòng), giữ nguyên trường do Admin tự sửa (`trang_thai`, `thoi_gian`). Sau đó mới gọi hàm update Google Sheets. 
- **Files liên quan**: `schedule-tool/scraper.py` (hàm `merge_data`)
