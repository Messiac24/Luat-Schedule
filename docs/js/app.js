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
    
    // Handle all access app buttons
    const accessBtns = document.querySelectorAll('#access-app, .access-app-btn');
    accessBtns.forEach(btn => {
        btn.addEventListener('click', (e) => {
            e.preventDefault();
            window.location.href = 'https://luat-schedule-production.up.railway.app/';
        });
    });
});
