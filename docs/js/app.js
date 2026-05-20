function showToast(message, type = 'success') {
    const toast = document.getElementById('toast');
    if (!toast) return;

    toast.textContent = message;
    toast.className = `toast show ${type}`;

    setTimeout(() => {
        toast.className = 'toast';
    }, 3000);
}

// Landing page ready
document.addEventListener('DOMContentLoaded', () => {
    console.log('Luật Schedule Landing Page loaded');
    
    const accessBtn = document.getElementById('access-app');
    if (accessBtn) {
        accessBtn.addEventListener('click', () => {
            window.location.href = 'https://luat-schedule-production.up.railway.app/';
        });
    }
});
