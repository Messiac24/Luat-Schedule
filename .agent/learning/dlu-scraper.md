# DLU Schedule Scraper

> Tổng hợp kiến thức về việc cào dữ liệu lịch học từ online.dlu.edu.vn trong dự án.
> Cập nhật lần cuối: 2026-05-20

---

## Architecture

### Local JSON is the operational source of truth
- **Date**: 2026-05-20
- **Details**: `schedule-tool/data.json` is the shared persistence layer between scraper, Flask admin, and Google Sheets sync. `scraper.py` refreshes scraped/static fields, `app.py` edits admin-controlled fields through `/api/update`, and `sheets.py` exports the current JSON snapshot to Google Sheets.
- **Related files**: `schedule-tool/data.json`, `schedule-tool/scraper.py`, `schedule-tool/app.py`, `schedule-tool/sheets.py`

### Scripts depend on the schedule-tool working directory
- **Date**: 2026-05-20
- **Details**: `DATA_FILE = "data.json"` and `credentials.json` are relative paths. Run `python app.py`, `python scraper.py`, and `python sheets.py` from `schedule-tool/`; running from the repo root will read/write the wrong location or fail to find credentials.
- **Related files**: `schedule-tool/app.py`, `schedule-tool/scraper.py`, `schedule-tool/sheets.py`

### Web DLU dùng React SPA + API backend riêng biệt
- **Ngày**: 2026-05-20
- **Chi tiết**: Website `online.dlu.edu.vn` là React SPA (MUI components). Dữ liệu được fetch từ API backend tại domain khác: `portal-api.dlu.edu.vn`. Bảng hiển thị trên UI được render client-side từ JSON API, không phải server-rendered HTML.
- **Files liên quan**: `schedule-tool/scraper.py`

### API endpoints đã phát hiện
- **Ngày**: 2026-05-20
- **Chi tiết**:
  - `GET portal-api.dlu.edu.vn/api/student/WeekSchedule?namhoc=2025-2026&hocky=HK02` → Danh sách tuần học
  - `GET portal-api.dlu.edu.vn/api/student/DrawingClassSchedule?ClassStudentID={classId}&namhoc={namhoc}&hocky={hocky}&tuan={weekNum}` → Lịch học theo lớp và tuần
- **Files liên quan**: `schedule-tool/api_dump.json`

### Kiến trúc scraper: Playwright + API Interception lai Requests
- **Ngày**: 2026-05-20
- **Chi tiết**: Dùng Playwrightheadless browser để đăng nhập (cần session cookie), sau đó dùng requests Python với headers bắt được để gọi API thay vì intercepting toàn bộ UI để tối ưu tốc độ cào xuyên nhiều học kỳ (HK01, HK02, HK03 qua nhiều năm).
- **Files liên quan**: `schedule-tool/scraper.py`

### Gộp lịch học trùng ngày (Same-day Schedule Grouping)
- **Ngày**: 2026-05-20
- **Chi tiết**: Để tối ưu không gian hiển thị và tránh lặp ngày trên UI, scraper nhóm các ca học trong cùng một ngày của một môn học vào một nhóm. Nếu ngày đó chỉ học 1 ca, hiển thị định dạng `Ngày - Ca`. Nếu có nhiều ca học trong ngày, hiển thị `Ngày` ở dòng đầu và thụt lề các ca `- Ca 1`, `- Ca 2` ở các dòng tiếp theo bằng ký tự xuống dòng `\n`.
- **Files liên quan**: `schedule-tool/scraper.py`, `schedule-tool/scratch_update.py`

---

## Bugs & Solutions

### Room/time edit API exists but frontend only saves status
- **Date**: 2026-05-20
- **Problem**: `app.py` accepts `thoi_gian` and `phong_hoc` in `/api/update`, but `static/js/app.js` only calls the endpoint from `updateStatus()`. The `.editable-field` nodes are rendered as plain divs and do not enable or persist edits.
- **Root cause**: The backend update surface was broader than the current frontend event handlers.
- **Fix**: Add explicit edit/save handlers for `.time-input` and `.room-input`, set `contenteditable="true"` only while editing, then POST `{id, thoi_gian, phong_hoc}` to `/api/update`. Keep status updates as the separate lightweight path.
- **Related files**: `schedule-tool/app.py`, `schedule-tool/templates/index.html`, `schedule-tool/static/js/app.js`

### Background scrape request has no completion state
- **Date**: 2026-05-20
- **Problem**: `/api/scrape` starts a background thread and immediately returns success, so the UI cannot know whether scraping finished or failed.
- **Root cause**: The thread result is not stored anywhere and there is no status endpoint.
- **Fix**: Track scrape job state in memory or a small JSON field (`running`, `last_success`, `last_error`, `finished_at`) and expose it through an API endpoint that the UI can poll before refreshing.
- **Related files**: `schedule-tool/app.py`, `schedule-tool/static/js/app.js`

### UnicodeEncodeError với tiếng Việt trên Windows
- **Ngày**: 2026-05-20
- **Vấn đề**: `print()` gây lỗi `UnicodeEncodeError: 'charmap' codec can't encode` trên Windows terminal (cp1252)
- **Root cause**: Windows default codepage không hỗ trợ Unicode tiếng Việt
- **Fix**: Set `$env:PYTHONIOENCODING="utf-8"` trước khi chạy script, hoặc dùng `.venv\Scripts\python.exe` (Python 3.12 qua `uv`) thay vì system Python
- **Files liên quan**: `schedule-tool/scraper.py`

### API trả HTML thay vì JSON khi fetch từ online.dlu.edu.vn
- **Ngày**: 2026-05-20
- **Vấn đề**: Dùng relative path `/api/student/...` từ `online.dlu.edu.vn` trả về HTML (`<!doctype...`)
- **Root cause**: API backend ở domain khác (`portal-api.dlu.edu.vn`). Website SPA proxy requests qua React app, nhưng fetch trực tiếp trong `page.evaluate()` bị CORS
- **Fix**: Dùng `page.on("response", handler)` để intercept responses thay vì gọi API trực tiếp
- **Files liên quan**: `schedule-tool/scraper.py`

### Trang mặc định hiển thị "TKB theo phòng", không phải "TKB theo lớp"
- **Ngày**: 2026-05-20
- **Vấn đề**: Khi vào `/student/schedules`, tab mặc định là "Thời khóa biểu theo phòng" — bảng trống không có dữ liệu lớp
- **Root cause**: UI có 4 tabs, cần click sang tab "Thời khóa biểu theo lớp" rồi search tên lớp
- **Fix**: Lấy API endpoint từ DevTools và giả lập request API bằng Python requests với classID thay vì click UI.
- **Files liên quan**: `schedule-tool/scraper.py`

### Gộp chung lịch học đa ngày (Multiline Concatenation)
- **Ngày**: 2026-05-20
- **Vấn đề**: Một môn học có thể kéo dài nhiều ngày hoặc đổi phòng, scraper cũ chỉ lưu giá trị của ngày cuối cùng đè lên ngày trước.
- **Root cause**: Dictionary assignment đè dữ liệu (`subj['thoi_gian'] = new_time`).
- **Fix**: Dùng `\n` để nối chuỗi (append) nếu thời gian/phòng học mới chưa tồn tại trong chuỗi cũ, giúp hiển thị đa dòng trên UI.
- **Files liên quan**: `schedule-tool/scraper.py`

### Textarea xấu, không tự động co giãn chiều cao (Auto-expand)
- **Ngày**: 2026-05-20
- **Vấn đề**: Textarea có thanh kéo góc (grip) trông kém sang và không tự động tăng chiều cao để hiển thị hết nội dung nhiều dòng.
- **Root cause**: Hạn chế mặc định của CSS đối với thẻ `<textarea>`.
- **Fix**: Thay thế `<textarea>` bằng `<div contenteditable="true">` kết hợp `white-space: pre-line; word-break: break-word;`. Khi không edit, nó hiển thị như text thường. Khi edit, nó tự co giãn hoàn hảo.
- **Files liên quan**: `schedule-tool/templates/index.html`, `schedule-tool/static/css/style.css`

### Trùng lặp lớp học do ký tự Unicode Eth `Ð` vs `Đ`
- **Ngày**: 2026-05-20
- **Vấn đề**: Tên lớp học (ví dụ: `LLT50DLCÐ` và `LLT50DLCĐ`) bị trùng lặp hiển thị làm 2 nhãn khác nhau dù nhìn bề ngoài giống hệt nhau.
- **Root cause**: API của trường trả về ký tự đặc biệt Eth `Ð` (`\u00d0` của tiếng Iceland) thay vì chữ `Đ` tiếng Việt chuẩn (`\u0110`), làm máy tính nhận dạng thành hai chuỗi khác biệt.
- **Fix**: Thêm hàm `normalize_class_name` để thực hiện `.replace('\u00d0', '\u0110')` chuẩn hóa toàn bộ chữ `Ð` lỗi thành `Đ` tiếng Việt chuẩn trước khi phân loại nhóm.
- **Files liên quan**: `schedule-tool/scraper.py`, `schedule-tool/app.py`

### Hiển thị sai Thứ trong tuần do lỗi map DayOfWeek
- **Ngày**: 2026-05-20
- **Vấn đề**: Lịch học hiển thị sai thứ lùi lại 1 ngày so với thực tế (ví dụ: ngày 18/04/2026 là Thứ Bảy nhưng hiển thị thành `(Thứ 6)`, ngày 19/04/2026 là Chủ Nhật hiển thị thành `(Thứ 7)`).
- **Root cause**: Logic cũ giả định `DayOfWeek = 8` là Chủ Nhật và `2..7` là `Thứ {day}`. Tuy nhiên API DLU sử dụng chuẩn ISO (Thứ Hai = 1, Thứ Ba = 2, ..., Thứ Bảy = 6, Chủ Nhật = 7). Việc map sai lệch 1 ngày khiến Thứ Bảy (6) thành Thứ 6, và Chủ Nhật (7) thành Thứ 7.
- **Fix**: Sử dụng map bảng thứ đầy đủ `day_map = {1: 'Thứ Hai', ..., 6: 'Thứ Bảy', 7: 'Chủ Nhật'}` để tra cứu chính xác, hoặc ưu tiên lấy trực tiếp từ trường dữ liệu `"Thu"` do API trả về.
- **Files liên quan**: `schedule-tool/scraper.py`, `schedule-tool/scratch_update.py`

### Lọc bỏ lịch học tối cuối tuần và quy đổi tiết học thân thiện
- **Ngày**: 2026-05-20
- **Vấn đề**: Dữ liệu chứa cả ca tối cuối tuần không cần thiết (tiết 11-14) và hiển thị dạng "Tiết 1-4", "Tiết 7-10" gây rối mắt, khó đọc.
- **Root cause**: API trường trả về tất cả khung giờ và sử dụng số tiết thay vì tên ca học.
- **Fix**: Kiểm tra số tiết học bắt đầu (`BeginTime`). Nếu là ngày cuối tuần (Thứ 7, Chủ Nhật) và tiết bắt đầu >= 11 thì loại bỏ hoàn toàn. Đồng thời quy đổi tiết học: Tiết 1-4 đổi thành "Sáng", Tiết 7-10 đổi thành "Chiều" để giao diện thân thiện hơn.
- **Files liên quan**: `schedule-tool/scraper.py`, `schedule-tool/scratch_update.py`

### Lịch học hiển thị không đúng thứ tự thời gian (Chronological Sorting)
- **Ngày**: 2026-05-20
- **Vấn đề**: Lịch học hiển thị lộn xộn, ngày sau đứng trước ngày trước (ví dụ: Chủ Nhật hiện trước Thứ Bảy).
- **Root cause**: Dữ liệu từ API không đảm bảo thứ tự thời gian và Python dictionary chỉ giữ thứ tự chèn. Code xử lý nối chuỗi `_schedule_data` trước đây duyệt dictionary theo thứ tự ngẫu nhiên.
- **Fix**: Viết hàm `parse_date_key()` để trích xuất `dd/mm/yyyy` thành object `datetime`, sau đó dùng hàm `sorted()` để sắp xếp các khóa (keys) của dictionary theo thứ tự thời gian tăng dần trước khi nối chuỗi render.
- **Files liên quan**: `schedule-tool/scraper.py`, `schedule-tool/scratch_update.py`

### Mất dữ liệu trạng thái thủ công khi chạy script cập nhật (Overwrite edits)
- **Ngày**: 2026-05-20
- **Vấn đề**: Các trạng thái "Đã học" do admin chỉnh sửa bằng tay bị reset về "Chưa học" khi chạy lại file script lọc và cập nhật dữ liệu.
- **Root cause**: Script `scratch_update.py` tạo mới toàn bộ dữ liệu và ghi đè trực tiếp lên `data.json` mà không giữ lại các trường mà người dùng (admin) đang tự quản lý.
- **Fix**: Thêm logic "bảo lưu" (preserve state) trước khi lưu: đọc file `data.json` hiện tại, map các trạng thái `trang_thai` hiện hữu theo `id` môn học, sau đó apply ngược lại vào object dữ liệu mới trước khi dump ra file JSON.
- **Files liên quan**: `schedule-tool/scratch_update.py`

### Chữ trong ô phòng học bị rớt dòng và responsive kém
- **Ngày**: 2026-05-20
- **Vấn đề**: Các phòng học có tên dài bị rớt dòng chữ (ví dụ: "Phòng\n102") nhìn thiếu chuyên nghiệp, và layout bị co cụm trên các kích thước màn hình.
- **Root cause**: Container hẹp (`max-width: 1400px`) và các cột `.col-room`, `.col-time` thiếu `min-width` hợp lý để giữ dòng.
- **Fix**: Nới rộng container lên `1600px` với độ rộng linh hoạt `98%`, tinh chỉnh padding của bảng, đặt `min-width` phù hợp cho các cột phòng/thời gian để tránh rớt dòng chữ, kết hợp media queries giảm font-size và padding trên thiết bị nhỏ để responsive tốt hơn.
- **Files liên quan**: `schedule-tool/static/css/style.css`

---

## How-To

### Run the local admin workflow
- **Date**: 2026-05-20
- **Steps**:
  1. `cd schedule-tool`
  2. Ensure `.env` contains `DLU_USERNAME`, `DLU_PASSWORD`, `TARGET_CLASSES`, and `GOOGLE_SHEETS_ID`.
  3. Ensure `credentials.json` exists beside `sheets.py` for Google Sheets sync.
  4. Run `python app.py` and open `http://localhost:5000`.
  5. Use `Scrape Moi` to refresh `data.json`, then `Sync Len Google Sheets` to publish the current local snapshot.
- **Related files**: `schedule-tool/README.md`, `schedule-tool/app.py`, `schedule-tool/sheets.py`

### Preserve admin edits during scraper refreshes
- **Date**: 2026-05-20
- **Steps**:
  1. Use course code (`ma_hp` / `id`) as the merge key.
  2. Refresh scraped fields such as `stt`, `ten_hoc_phan`, `tc`, `giang_vien`, `phong_hoc`, `thoi_gian_goc`, `lop_hoc`, and `last_scraped`.
  3. Preserve admin-owned fields such as `trang_thai` and edited `thoi_gian`.
  4. Re-save the merged list to `data.json`, then sync to Sheets if publication is needed.
- **Related files**: `schedule-tool/scraper.py`

### Cách setup môi trường scraper
- **Ngày**: 2026-05-20
- **Bước thực hiện**:
  1. `uv venv --python 3.12` — tạo venv với Python 3.12
  2. `.\.venv\Scripts\activate` — kích hoạt venv
  3. `uv pip install -r requirements.txt` — cài dependencies
  4. `playwright install chromium` — cài Chromium cho Playwright
  5. Copy `.env.example` → `.env` và điền `DLU_USERNAME`, `DLU_PASSWORD`, `TARGET_CLASSES`
  6. `$env:PYTHONIOENCODING="utf-8"; python scraper.py` — chạy scraper
- **Files liên quan**: `schedule-tool/requirements.txt`, `schedule-tool/.env`

### Cách tương tác với MUI Autocomplete bằng Playwright
- **Ngày**: 2026-05-20
- **Bước thực hiện**:
  1. Tìm input: `page.locator("input[type='text']").nth(-1)`
  2. Click và fill: `input.click()` → `input.fill("LHK50DL")`
  3. Chờ dropdown: `page.wait_for_selector("li[role='option']", timeout=10000)`
  4. Click option đầu: `page.locator("li[role='option']").first.click()`
  5. Chờ data load: `page.wait_for_timeout(5000)`
- **Files liên quan**: `schedule-tool/scraper.py`

### Cách tạo editable field tự co giãn thay vì textarea
- **Ngày**: 2026-05-20
- **Bước thực hiện**:
  1. Dùng thẻ `div`: `<div class="editable-field" contenteditable="false">Text</div>`
  2. CSS: Thêm `white-space: pre-line` để nhận dạng ký tự `\n` (xuống dòng).
  3. CSS: Khi focus thì thêm viền `border-color` và `box-shadow` để giống thẻ input.
  4. JS: Khi cần sửa, gán `setAttribute('contenteditable', 'true')`. Khi lấy dữ liệu, dùng `.innerText` thay vì `.value`.
- **Files liên quan**: `schedule-tool/templates/index.html`, `schedule-tool/static/js/app.js`

---

## Patterns

### Flask endpoint pattern for local JSON mutations
- **Date**: 2026-05-20
- **Details**: Keep local JSON mutations narrow: load `data.json`, find a subject by `id`, update only fields present in the POST body, save the entire document, and return `{success, message?}`. This matches the current `/api/update` behavior and keeps admin edits explicit.
- **Related files**: `schedule-tool/app.py`

### Google Sheets export is replace-all, not incremental
- **Date**: 2026-05-20
- **Details**: `sheets.py` clears `sheet1` and writes the full `subjects` table every sync. Treat Google Sheets as a published view of `data.json`, not a bidirectional source. Any manual Sheet edits can be overwritten by the next sync.
- **Related files**: `schedule-tool/sheets.py`

### Response Interception Pattern với Playwright
- **Ngày**: 2026-05-20
- **Chi tiết**: Khi cần lấy dữ liệu từ SPA mà API bị CORS, dùng `page.on("response", handler)` để đón lõng responses. Handler kiểm tra URL pattern và parse JSON.
- **Ví dụ code**:
  ```python
  api_responses = []
  def handle_response(response):
      if "targetendpoint" in response.url.lower():
          try:
              data = response.json()
              api_responses.append({"url": response.url, "data": data})
          except:
              pass
  page.on("response", handle_response)
  # ... navigate through UI to trigger API calls ...
  ```
- **Files liên quan**: `schedule-tool/scraper.py`

### Dùng uv thay pip/venv trên Windows
- **Ngày**: 2026-05-20
- **Chi tiết**: `uv` tự động download Python version cần thiết nếu chưa có. Dùng `uv venv --python 3.12` thay `python -m venv`, `uv pip install` thay `pip install`. Nhanh hơn nhiều lần.
- **Files liên quan**: `schedule-tool/requirements.txt`

### Content-Editable Pattern cho Admin UI
- **Ngày**: 2026-05-20
- **Chi tiết**: Để UI nhìn Premium (như text bình thường nhưng có thể click để sửa), dùng pattern `contenteditable` với div thay vì textarea. Kết hợp với JS toggle thuộc tính `contenteditable` giữa `true` (khi bật chế độ edit) và `false` (chế độ readonly).
- **Files liên quan**: `schedule-tool/static/css/style.css`, `schedule-tool/static/js/app.js`
