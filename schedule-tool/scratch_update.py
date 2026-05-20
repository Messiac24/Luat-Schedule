import json
import re
from datetime import datetime

with open('api_dump.json', 'r', encoding='utf-8') as f:
    all_raw_data = json.load(f)

# Lọc bỏ Thứ 2-6, chỉ giữ Thứ 7 + CN
all_raw_data = [item for item in all_raw_data if item.get('DayOfWeek', 0) >= 6]
print(f'Sau khi lọc: {len(all_raw_data)} entries cuối tuần.')

subjects_map = {}
for item in all_raw_data:
    raw_html = item.get('TKHHienThi', '')
    ma_hp_match = re.search(r'\(([\w\d]+)\)', raw_html.split('<br/>')[0]) if raw_html else None
    ma_hp = ma_hp_match.group(1) if ma_hp_match else item.get('ScheduleStudyUnitID', '')
    if not ma_hp: continue
    
    tc = 0
    da_hoc_match = re.search(r'Đã học: \d+/(\d+) tiết', raw_html) if raw_html else None
    if da_hoc_match: tc = int(da_hoc_match.group(1)) // 15
    
    lop_hoc = []
    lop_match = re.search(r'Lớp: ([^<]+)', raw_html) if raw_html else None
    if lop_match: lop_hoc = [l.strip() for l in lop_match.group(1).split(',')]
    cid = item.get('_class_id', '')
    if cid and cid not in lop_hoc: lop_hoc.append(cid)
    
    day_int = item.get('DayOfWeek', 0)
    day_map = {
        1: 'Thứ Hai',
        2: 'Thứ Ba',
        3: 'Thứ Tư',
        4: 'Thứ Năm',
        5: 'Thứ Sáu',
        6: 'Thứ Bảy',
        7: 'Chủ Nhật'
    }
    day = day_map.get(day_int, item.get('Thu', ''))
    
    ngay = item.get('Ngay', '')
    
    start = str(item.get('BeginTime', '')).replace('Tiết:', '').strip()
    end = str(item.get('EndTime', '')).strip()
    
    start_int = int(start) if start.isdigit() else 0
    if start_int >= 11:
        continue
        
    session_name = f"Tiết {start}-{end}"
    if start == "1":
        session_name = "Sáng"
    elif start == "7":
        session_name = "Chiều"
        
    room_str = item.get('RoomID', '')
    mode = 'Trực tuyến' if 'Online' in room_str else 'Trực tiếp'
    
    date_key = f"{ngay} ({day})" if ngay else ""
    period_str = f"{session_name} ({mode})"
    
    if ma_hp not in subjects_map:
        subjects_map[ma_hp] = {
            'id': ma_hp, 'ma_hp': ma_hp,
            'ten_hoc_phan': item.get('CurriculumName', ''),
            'tc': tc, 'giang_vien': item.get('FullName', ''),
            'phong_hoc': "",
            'thoi_gian': "", 'thoi_gian_goc': "",
            'lop_hoc': lop_hoc, 'trang_thai': 'Chưa học',
            'last_scraped': datetime.now().isoformat(),
            '_schedule_data': {},
            '_seen_rooms': set()
        }
    
    subj = subjects_map[ma_hp]
    for l in lop_hoc:
        if l not in subj['lop_hoc']: subj['lop_hoc'].append(l)
    
    if date_key:
        if date_key not in subj["_schedule_data"]:
            subj["_schedule_data"][date_key] = []
        if period_str not in subj["_schedule_data"][date_key]:
            subj["_schedule_data"][date_key].append(period_str)
            
    if room_str and room_str not in subj['_seen_rooms']:
        subj['_seen_rooms'].add(room_str)
        if subj['phong_hoc']:
            subj['phong_hoc'] += f'\n{room_str}'
        else:
            subj['phong_hoc'] = room_str

def parse_date_key(date_key):
    """Extract date from '18/04/2026 (Thứ Bảy)' for sorting."""
    try:
        date_part = date_key.split(" (")[0].strip()
        return datetime.strptime(date_part, "%d/%m/%Y")
    except (ValueError, IndexError):
        return datetime.max

for subj in subjects_map.values():
    lines = []
    sorted_dates = sorted(subj["_schedule_data"].items(), key=lambda x: parse_date_key(x[0]))
    for date_key, periods in sorted_dates:
        if len(periods) == 1:
            lines.append(f"{date_key} - {periods[0]}")
        else:
            lines.append(f"{date_key}")
            for p in periods:
                lines.append(f"  - {p}")
    
    subj["thoi_gian"] = "\n".join(lines)
    subj["thoi_gian_goc"] = subj["thoi_gian"]
    
    subj.pop('_schedule_data', None)
    subj.pop('_seen_rooms', None)

subjects_list = list(subjects_map.values())

existing_status = {}
try:
    with open('data.json', 'r', encoding='utf-8') as f:
        old_data = json.load(f)
        for s in old_data.get('subjects', []):
            existing_status[s['id']] = s.get('trang_thai', 'Chưa học')
except Exception:
    pass

for i, subj in enumerate(subjects_list, 1): 
    subj['stt'] = i
    if subj['id'] in existing_status:
        subj['trang_thai'] = existing_status[subj['id']]

with open('data.json', 'w', encoding='utf-8') as f:
    json.dump({'subjects': subjects_list, 'last_updated': datetime.now().isoformat()}, f, ensure_ascii=False, indent=2)

print(f'Đã lưu {len(subjects_list)} môn học vào data.json (chỉ cuối tuần)')
