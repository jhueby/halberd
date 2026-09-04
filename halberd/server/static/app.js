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

document.body.addEventListener('htmx:afterRequest', function(e) {
    if (!e.detail.target || e.detail.target.id !== 'update-lib-result') return;

    var target = e.detail.target;
    target.style.display = 'block';

    if (!e.detail.successful) {
        target.innerHTML = '<span style="color:var(--red)">Update failed. Check your network connection.</span>';
        return;
    }

    try {
        var data = JSON.parse(e.detail.xhr.responseText);
        var html = '';

        if (data.status === 'up_to_date') {
            html = '<span style="color:var(--green)">Library is up to date.</span>';
        } else {
            var items = [];
            (data.new_atomics || []).forEach(function(f) { items.push('<span style="color:var(--green)">+ ' + f + '</span>'); });
            (data.updated_atomics || []).forEach(function(f) { items.push('<span style="color:var(--yellow)">~ ' + f + '</span>'); });
            (data.new_chains || []).forEach(function(f) { items.push('<span style="color:var(--green)">+ ' + f + '</span>'); });
            (data.updated_chains || []).forEach(function(f) { items.push('<span style="color:var(--yellow)">~ ' + f + '</span>'); });
            html = '<div style="color:var(--green);font-weight:600;margin-bottom:0.5rem">Library updated</div>' +
                   '<div>' + items.join('<br>') + '</div>' +
                   '<div style="margin-top:0.5rem;color:var(--text-muted)">' + data.summary + '</div>' +
                   '<div style="margin-top:0.5rem"><a href="javascript:location.reload()" style="color:var(--accent)">Reload page</a> to see changes</div>';
        }
        target.innerHTML = html;
    } catch (err) {
        target.innerHTML = '<span style="color:var(--red)">Unexpected response.</span>';
    }
});
