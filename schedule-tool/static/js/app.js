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

function getSubjectRow(id) {
    return document.querySelector(`tr[data-id="${id}"]`);
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

function moveDoneRowToTop(id, status) {
    if (status.trim() !== 'Đã học') return;

    const row = getSubjectRow(id);

    const tbody = row ? row.parentElement : null;
    if (!row || !tbody) return;

    tbody.prepend(row);
}

function saveRow(id, successMessage = 'Đã lưu cập nhật') {
    const payload = collectRowPayload(id);
    updateRowStatusClass(id, payload.trang_thai || '');

    return fetch('/api/update', {

        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(payload),
    })
        .then(res => res.json().then(data => ({ ok: res.ok, data })))
        .then(({ ok, data }) => {
            if (ok && data.success) {
                moveDoneRowToTop(id, payload.trang_thai || '');
                showToast(successMessage);
            } else {
                showToast(data.message || 'Không thể lưu cập nhật', 'error');
            }
        })
        .catch(() => showToast('Lỗi mạng', 'error'));
}

function updateStatus(id, newStatus) {
    updateRowStatusClass(id, newStatus);
    saveRow(id, 'Đã cập nhật trạng thái');
}

document.querySelectorAll('.btn-save-row').forEach(button => {
    button.addEventListener('click', () => {
        saveRow(button.dataset.id);
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
