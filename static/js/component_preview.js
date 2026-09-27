/*
 * Live preview for the Component editor: redraws the entry the way Jake's
 * template (templates/latex/jakes.tex.j2) lays it out, from the unsaved form.
 * HTML approximation only; the PDF is the source of truth for line breaks.
 *
 * The helpers below mirror compiler/services.py (fmt_date, date_range,
 * bullet_markup) and the template's per-category headings. Change them together.
 */
(function () {
    var form = document.querySelector('form.edit-form');
    var sheet = document.getElementById('component-preview');
    if (!form || !sheet) return;

    // Section headings: SECTION_TITLES; honors render nested under Education.
    var SECTION_TITLES = {
        experience: 'Experience', project: 'Projects', leadership: 'Leadership',
        certification: 'Certifications', honor: 'Education',
    };
    var MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];

    function escapeHtml(s) {
        return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
    }

    // fmt_date: 'Jun. 2025'; May needs no period.
    function fmtDate(iso) {
        var m = /^(\d{4})-(\d{2})/.exec(iso || '');
        if (!m) return '';
        var mon = MONTHS[parseInt(m[2], 10) - 1];
        return mon === 'May' ? mon + ' ' + m[1] : mon + '. ' + m[1];
    }

    // date_range: null end means Present. LaTeX `--` is an en dash.
    function dateRange(start, end) {
        if (!fmtDate(start)) return '';
        return fmtDate(start) + ' – ' + (fmtDate(end) || 'Present');
    }

    // bullet_markup: escape first, then **bold** (non-greedy, single line).
    function bulletHtml(text) {
        return escapeHtml(text).replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
    }

    function val(name) {
        var el = form.elements[name];
        return el ? el.value.trim() : '';
    }

    function row(left, right, cls) {
        return '<div class="rs-row' + (cls ? ' ' + cls : '') + '"><span>' + left + '</span><span>' + right + '</span></div>';
    }

    function titleWith(title, extra) {
        var html = '<strong>' + escapeHtml(title) + '</strong>';
        if (extra) html += ' | <em>' + escapeHtml(extra) + '</em>';
        return html;
    }

    function bullets() {
        var rows = [];
        form.querySelectorAll('textarea[name$="-text"]').forEach(function (textarea, index) {
            var prefix = textarea.name.slice(0, -'text'.length);
            var del = form.elements[prefix + 'DELETE'];
            var text = textarea.value.trim();
            if (!text || (del && del.checked)) return;
            var order = parseInt(val(prefix + 'order'), 10);
            rows.push({ text: text, order: isNaN(order) ? 0 : order, index: index });
        });
        // order_by('order', 'id'): unsaved rows come last in the form, so row index stands in for id.
        rows.sort(function (a, b) { return a.order - b.order || a.index - b.index; });
        return rows;
    }

    function render() {
        var category = val('category');
        var title = val('title');
        var org = val('organization');
        var html = '<h3 class="rs-section">' + (SECTION_TITLES[category] || '') + '</h3>';

        if (category === 'project') {
            html += row(titleWith(title, val('tech_stack')), dateRange(val('start_date'), val('end_date')), 'rs-small');
        } else if (category === 'certification' || category === 'honor') {
            html += row(titleWith(title, org), fmtDate(val('start_date')), 'rs-small');
        } else {
            html += row('<strong>' + escapeHtml(title) + '</strong>', dateRange(val('start_date'), val('end_date')));
            html += row('<em>' + escapeHtml(org) + '</em>', '<em>' + escapeHtml(val('location')) + '</em>', 'rs-small');
        }

        var items = bullets();
        if (items.length) {
            html += '<ul class="rs-bullets">' + items.map(function (b) {
                return '<li>' + bulletHtml(b.text) + '</li>';
            }).join('') + '</ul>';
        }
        sheet.innerHTML = html;
    }

    form.addEventListener('input', render);
    form.addEventListener('change', render);
    render();
})();
