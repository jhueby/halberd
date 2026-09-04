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
    if (!e.detail.target) return;

    if (e.detail.target.id === 'cleanup-result') {
        handleCleanupResponse(e);
        return;
    }

    if (e.detail.target.id !== 'update-lib-result') return;

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

function handleCleanupResponse(e) {
    var target = e.detail.target;
    target.style.display = 'block';

    if (!e.detail.successful) {
        target.innerHTML = '<span style="color:var(--red)">Cleanup failed. Check server logs.</span>';
        return;
    }

    try {
        var data = JSON.parse(e.detail.xhr.responseText);
        var statusColors = {
            'cleaned': 'var(--green)',
            'failed': 'var(--red)',
            'skipped': 'var(--accent)',
            'no-cleanup': 'var(--text-muted)'
        };
        var statusIcons = {
            'cleaned': '✓',
            'failed': '✗',
            'skipped': '○',
            'no-cleanup': '—'
        };

        var rows = '';
        (data.actions || []).forEach(function(a) {
            if (a.status === 'no-cleanup') return;
            var color = statusColors[a.status] || 'var(--text)';
            var icon = statusIcons[a.status] || '?';
            rows += '<div style="display:flex;gap:0.75rem;padding:0.25rem 0;font-size:0.8rem">' +
                '<span style="color:' + color + ';width:1rem;text-align:center">' + icon + '</span>' +
                '<code style="min-width:6rem">' + a.technique_id + '</code>' +
                '<span>' + a.test_name + '</span>' +
                '<span style="color:' + color + ';margin-left:auto">' + a.status + '</span>' +
                '</div>';
        });

        var artifactHtml = '';
        if (data.artifacts && data.artifacts.length > 0) {
            artifactHtml = '<div style="margin-top:0.75rem;color:var(--yellow);font-weight:600">Residual artifacts:</div>';
            data.artifacts.forEach(function(art) {
                art.found.forEach(function(f) {
                    artifactHtml += '<div style="font-size:0.8rem;color:var(--red);padding-left:1rem">' + f + '</div>';
                });
            });
        }

        var html = '<div style="font-weight:600;margin-bottom:0.5rem;color:' +
            (data.status === 'cleaned' ? 'var(--green)' : 'var(--accent)') + '">' +
            (data.status === 'cleaned' ? 'Remediation complete' : 'Cleanup check') + '</div>' +
            (rows ? '<div>' + rows + '</div>' : '') +
            artifactHtml +
            '<div style="margin-top:0.5rem;color:var(--text-muted);font-size:0.8rem">' + data.summary + '</div>';

        target.innerHTML = html;
    } catch (err) {
        target.innerHTML = '<span style="color:var(--red)">Unexpected response.</span>';
    }
}
