document.addEventListener('DOMContentLoaded', function() {
    var currentPath = window.location.pathname;
    var links = document.querySelectorAll('.nav-link');
    links.forEach(function(link) {
        if (link.getAttribute('href') === currentPath) {
            link.style.color = 'var(--text)';
            link.style.background = 'var(--border)';
        }
    });
});
