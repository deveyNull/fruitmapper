// Common JavaScript functionality can be added here
document.addEventListener('DOMContentLoaded', function() {
    // Handle logout
    const logoutForm = document.querySelector('form[action="/logout"]');
    if (logoutForm) {
        logoutForm.addEventListener('submit', function(e) {
            e.preventDefault();
            fetch('/logout', {
                method: 'POST',
                credentials: 'same-origin'
            }).then(() => {
                window.location.href = '/';
            });
        });
    }
});