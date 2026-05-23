const CLASS_CODE_MAP = {
    'LH26B2DL': 'VB2',
    'LLT50DLCĐ': 'CĐ',
    'LLT50DLTC': 'TC',
    'LHK50DL': 'VLVH',
};

let classMapEnabled = false;
let activeScheduleFilter = 'all';

function showToast(message, type = 'success') {
    const toast = document.getElementById('toast');
    if (!toast) return;

    toast.textContent = message;
    toast.className = `toast show ${type}`;

    setTimeout(() => {
        toast.className = 'toast';
    }, 3000);
}

function statusClass(value) {
    return value.toLowerCase().trim().replace(/\s+/g, '-');
}

function formatClassFilterLabel(className) {
    const mappedName = CLASS_CODE_MAP[className];
    return mappedName ? `${className} (${mappedName})` : className;
}

function getSubjectRow(id) {
    return document.querySelector(`tr[data-id="${id}"]`);
}

function getAllClassBadges() {
    return Array.from(document.querySelectorAll('.badge-class'));
}

function bindBadgeOriginalText() {
    getAllClassBadges().forEach((badge) => {
        if (!badge.dataset.originalClass) {
            badge.dataset.originalClass = badge.textContent.trim();
        }
    });
}

function updateAllClassBadges() {
    getAllClassBadges().forEach((badge) => {
        const original = badge.dataset.originalClass || badge.textContent.trim();
        badge.textContent = classMapEnabled ? (CLASS_CODE_MAP[original] || original) : original;
    });
}

function toggleClassMap() {
    classMapEnabled = !classMapEnabled;
    updateAllClassBadges();
    const button = document.getElementById('btn-toggle-class-map');
    if (button) {
        button.textContent = classMapEnabled ? 'Hiển thị mã đầy đủ' : 'Chuyển mã lớp';
    }
}

function collectRowPayload(id) {
    const row = getSubjectRow(id);
    const status = row.querySelector('.status-select');
    const time = row.querySelector('.time-editor');
    const room = row.querySelector('.room-editor');

    return {
        id,
        trang_thai: status ? status.value : undefined,
        thoi_gian: time ? time.value : undefined,
        phong_hoc: room ? room.value : undefined,
    };
}

function updateRowStatusClass(id, newStatus) {
    const row = getSubjectRow(id);
    if (!row) return;

    const lowClassCount = row.dataset.lowClassCount === 'true';
    const newStatusClass = `status-${statusClass(newStatus)}`;

    // Do not overwrite row.className (it may remove other classes that affect layout)
    // Remove existing status-* classes
    row.classList.forEach((cls) => {
        if (cls.startsWith('status-')) row.classList.remove(cls);
    });

    row.classList.add('subject-row');
    if (lowClassCount) row.classList.add('low-class-count');
    else row.classList.remove('low-class-count');

    row.classList.add(newStatusClass);
}

function getRowStatus(row) {
    const className = Array.from(row.classList).find((cls) => cls.startsWith('status-'));
    if (!className) return '';
    return className.replace(/^status-/, '').replace(/-/g, ' ').trim();
}

function getStatusPriority(status) {
    const normalized = status.trim();
    if (normalized === 'Chưa học') return 0;
    if (normalized === 'Học bù') return 1;
    if (normalized === 'Đã học') return 2;
    return 1;
}

function findInsertBeforeRow(tbody, status) {
    const targetPriority = getStatusPriority(status);
    for (const row of tbody.querySelectorAll('tr[data-id]')) {
        const rowStatus = getRowStatus(row);
        if (getStatusPriority(rowStatus) > targetPriority) {
            return row;
        }
    }
    return null;
}

function reorderRowByStatus(id, status) {
    const row = getSubjectRow(id);
    if (!row) {
        console.warn('Row not found for reorderRowByStatus', id);
        return;
    }

    const tbody = row.parentElement;
    if (!tbody) {
        console.warn('Table body not found for row', id);
        return;
    }

    const insertBefore = findInsertBeforeRow(tbody, status);
    if (insertBefore) {
        tbody.insertBefore(row, insertBefore);
    } else {
        tbody.appendChild(row);
    }
}

function normalizeFilterText(value) {
    return String(value || '').trim().toLowerCase();
}

function startOfDay(date) {
    return new Date(date.getFullYear(), date.getMonth(), date.getDate());
}

function startOfWeek(date) {
    const day = date.getDay() || 7;
    const start = startOfDay(date);
    start.setDate(start.getDate() - day + 1);
    return start;
}

function getRowScheduleDates(row) {
    const rawTime = row.querySelector('.schedule-list')?.dataset.rawTime
        || row.querySelector('.time-editor')?.value
        || '';
    const dates = [];
    const datePattern = /(\d{2})\/(\d{2})\/(\d{4})/g;
    let match;

    while ((match = datePattern.exec(rawTime)) !== null) {
        const day = Number(match[1]);
        const month = Number(match[2]) - 1;
        const year = Number(match[3]);
        dates.push(new Date(year, month, day));
    }

    return dates;
}

function rowMatchesScheduleFilter(row, scheduleFilter) {
    if (scheduleFilter === 'all') return true;

    const today = startOfDay(new Date());
    const dates = getRowScheduleDates(row).map(startOfDay);
    if (!dates.length) return false;

    if (scheduleFilter === 'today') {
        return dates.some((date) => date.getTime() === today.getTime());
    }

    if (scheduleFilter === 'week') {
        const weekStart = startOfWeek(today);
        const weekEnd = new Date(weekStart);
        weekEnd.setDate(weekEnd.getDate() + 6);
        return dates.some((date) => date >= weekStart && date <= weekEnd);
    }

    if (scheduleFilter === 'upcoming') {
        return dates.some((date) => date >= today);
    }

    return true;
}

function rowMatchesSearch(row, searchText) {
    if (!searchText) return true;
    const haystack = normalizeFilterText([
        row.dataset.id,
        row.dataset.subject,
        row.dataset.teacher,
        row.dataset.classList,
        row.textContent,
    ].join(' '));
    return haystack.includes(searchText);
}

function rowMatchesFilters(row, classFilter, subjectFilter, teacherFilter, searchText, scheduleFilter) {
    const rowClasses = normalizeFilterText(row.dataset.classList);
    const rowSubject = normalizeFilterText(row.dataset.subject);
    const rowTeacher = normalizeFilterText(row.dataset.teacher);

    if (!rowMatchesSearch(row, searchText)) {
        return false;
    }
    if (!rowMatchesScheduleFilter(row, scheduleFilter)) {
        return false;
    }
    if (classFilter && !rowClasses.split(',').map((cls) => cls.trim()).includes(classFilter)) {
        return false;
    }
    if (subjectFilter && rowSubject !== subjectFilter) {
        return false;
    }
    if (teacherFilter && rowTeacher !== teacherFilter) {
        return false;
    }
    return true;
}

function initSelectOptions(attribute, elementId, defaultText) {
    const values = new Set();
    document.querySelectorAll('tbody tr[data-id]').forEach((row) => {
        const raw = row.dataset[attribute] || '';
        raw.split(',').forEach((item) => {
            const trimmed = item.trim();
            if (trimmed) values.add(trimmed);
        });
    });

    const select = document.getElementById(elementId);
    if (!select) return;

    Array.from(values)
        .sort((a, b) => a.localeCompare(b, 'vi'))
        .forEach((value) => {
            const option = document.createElement('option');
            option.value = normalizeFilterText(value);
            option.textContent = value;
            select.appendChild(option);
        });
}

function applyFilters() {
    const searchText = normalizeFilterText(document.getElementById('filter-search')?.value);
    const classFilter = normalizeFilterText(document.getElementById('filter-class')?.value);
    const subjectFilter = normalizeFilterText(document.getElementById('filter-subject')?.value);
    const teacherFilter = normalizeFilterText(document.getElementById('filter-teacher')?.value);

    document.querySelectorAll('tbody tr[data-id]').forEach((row) => {
        row.style.display = rowMatchesFilters(
            row,
            classFilter,
            subjectFilter,
            teacherFilter,
            searchText,
            activeScheduleFilter,
        ) ? '' : 'none';
    });
}

function buildExportUrl() {
    const params = new URLSearchParams();
    const classFilter = document.getElementById('filter-class')?.value || '';
    const subjectFilter = document.getElementById('filter-subject')?.value || '';
    const teacherFilter = document.getElementById('filter-teacher')?.value || '';
    const searchText = document.getElementById('filter-search')?.value || '';

    if (classFilter) params.set('class', classFilter);
    if (subjectFilter) params.set('subject', subjectFilter);
    if (teacherFilter) params.set('teacher', teacherFilter);
    if (searchText) params.set('q', searchText);
    if (activeScheduleFilter !== 'all') params.set('range', activeScheduleFilter);

    const query = params.toString();
    return query ? `/api/export.xlsx?${query}` : '/api/export.xlsx';
}

function exportExcel() {
    window.location.href = buildExportUrl();
}

function initClassFilterOptions() {
    const classSet = new Set();
    document.querySelectorAll('tbody tr[data-id]').forEach((row) => {
        row.dataset.classList.split(',').forEach((cls) => {
            const trimmed = cls.trim();
            if (trimmed) classSet.add(trimmed);
        });
    });

    const select = document.getElementById('filter-class');
    if (!select) return;

    Array.from(classSet)
        .sort((a, b) => a.localeCompare(b, 'vi'))
        .forEach((className) => {
            const option = document.createElement('option');
            option.value = normalizeFilterText(className);
            option.textContent = formatClassFilterLabel(className);
            select.appendChild(option);
        });
}

function saveRow(id, successMessage = 'Đã lưu cập nhật') {
    const payload = collectRowPayload(id);
    const row = getSubjectRow(id);
    const oldStatus = row ? row.querySelector('.status-select')?.value : null;

    return fetch('/api/update', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(payload),
    })
        .then((res) => {
            if (!res.ok) {
                throw new Error('HTTP error');
            }
            return res.json();
        })
        .then((data) => {
            if (data.success) {
                if (row && payload.trang_thai) {
                    updateRowStatusClass(id, payload.trang_thai);
                    reorderRowByStatus(id, payload.trang_thai);
                }
                showToast(successMessage);
            } else {
                if (row && oldStatus) {
                    const select = row.querySelector('.status-select');
                    if (select) select.value = oldStatus;
                }
                showToast(data.message || 'Không thể lưu cập nhật', 'error');
            }
        })
        .catch(() => {
            if (row && oldStatus) {
                const select = row.querySelector('.status-select');
                if (select) select.value = oldStatus;
            }
            showToast('Lỗi mạng', 'error');
        });
}

function resetRow(id) {
    return fetch('/api/reset', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ id }),
    })
        .then(res => res.json().then(data => ({ ok: res.ok, data })))
        .then(({ ok, data }) => {
            if (ok && data.success) {
                const row = getSubjectRow(id);
                if (!row) return;

                const status = row.querySelector('.status-select');
                const time = row.querySelector('.time-editor');
                const room = row.querySelector('.room-editor');

                if (status) {
                    status.value = data.subject.trang_thai;
                }
                if (time) {
                    time.value = data.subject.thoi_gian;
                }
                if (room) {
                    room.value = data.subject.phong_hoc;
                }

                updateRowStatusClass(id, data.subject.trang_thai);
                reorderRowByStatus(id, data.subject.trang_thai);
                showToast('Đã reset lịch gốc');
            } else {
                showToast(data.message || 'Không thể reset', 'error');
            }
        })
        .catch(() => showToast('Lỗi mạng', 'error'));
}

function updateStatus(id, newStatus) {
    saveRow(id, 'Đã cập nhật trạng thái');
}

document.querySelectorAll('.btn-save-row').forEach(button => {
    button.addEventListener('click', () => {
        saveRow(button.dataset.id);
    });
});

document.querySelectorAll('.btn-reset-row').forEach(button => {
    button.addEventListener('click', () => {
        resetRow(button.dataset.id);
    });
});

const scrapeButton = document.getElementById('btn-scrape');
if (scrapeButton) {
    scrapeButton.addEventListener('click', () => {
        const originalText = scrapeButton.innerHTML;
        scrapeButton.innerHTML = 'Đang chạy...';
        scrapeButton.disabled = true;

        fetch('/api/scrape', { method: 'POST' })
            .then(res => res.json())
            .then(data => {
                showToast(data.message, data.success === false ? 'error' : 'success');
                setTimeout(() => {
                    scrapeButton.innerHTML = originalText;
                    scrapeButton.disabled = false;
                }, 3000);
            })
            .catch(() => {
                showToast('Lỗi khi chạy scraper', 'error');
                scrapeButton.innerHTML = originalText;
                scrapeButton.disabled = false;
            });
    });
}

const clearFiltersButton = document.getElementById('btn-clear-filters');
if (clearFiltersButton) {
    clearFiltersButton.addEventListener('click', () => {
        const searchFilter = document.getElementById('filter-search');
        const classFilter = document.getElementById('filter-class');
        const subjectFilter = document.getElementById('filter-subject');
        const teacherFilter = document.getElementById('filter-teacher');

        if (searchFilter) searchFilter.value = '';
        if (classFilter) classFilter.value = '';
        if (subjectFilter) subjectFilter.value = '';
        if (teacherFilter) teacherFilter.value = '';
        activeScheduleFilter = 'all';
        document.querySelectorAll('.quick-filter-btn').forEach((button) => {
            button.classList.toggle('active', button.dataset.scheduleFilter === 'all');
        });
        applyFilters();
    });
}

const filterSearch = document.getElementById('filter-search');
const filterClass = document.getElementById('filter-class');
const filterSubject = document.getElementById('filter-subject');
const filterTeacher = document.getElementById('filter-teacher');

if (filterSearch) filterSearch.addEventListener('input', applyFilters);
if (filterClass) filterClass.addEventListener('change', applyFilters);
if (filterSubject) filterSubject.addEventListener('change', applyFilters);
if (filterTeacher) filterTeacher.addEventListener('change', applyFilters);

document.querySelectorAll('.quick-filter-btn').forEach((button) => {
    button.addEventListener('click', () => {
        activeScheduleFilter = button.dataset.scheduleFilter || 'all';
        document.querySelectorAll('.quick-filter-btn').forEach((item) => {
            item.classList.toggle('active', item === button);
        });
        applyFilters();
    });
});

const classToggleButton = document.getElementById('btn-toggle-class-map');
if (classToggleButton) {
    classToggleButton.addEventListener('click', toggleClassMap);
}

const exportExcelButton = document.getElementById('btn-export-excel');
if (exportExcelButton) {
    exportExcelButton.addEventListener('click', exportExcel);
}

bindBadgeOriginalText();
initClassFilterOptions();
initSelectOptions('subject', 'filter-subject');
initSelectOptions('teacher', 'filter-teacher');
applyFilters();

const syncButton = document.getElementById('btn-sync');
if (syncButton) {
    syncButton.addEventListener('click', () => {
        const originalText = syncButton.innerHTML;
        syncButton.innerHTML = 'Đang sync...';
        syncButton.disabled = true;

        fetch('/api/sync', { method: 'POST' })
            .then(res => res.json())
            .then(data => {
                showToast(data.message, data.success === false ? 'error' : 'success');
            })
            .catch(() => showToast('Lỗi mạng', 'error'))
            .finally(() => {
                syncButton.innerHTML = originalText;
                syncButton.disabled = false;
            });
    });
}
