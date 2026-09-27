/*
 * Live preview for the Component and Education editors: redraws the entry the
 * way Jake's template (templates/latex/jakes.tex.j2) lays it out, from the
 * unsaved form. HTML approximation only; the PDF is the source of truth for
 * line breaks.
 *
 * The helpers below mirror compiler/services.py (fmt_date, date_range,
 * date_or_range, bullet_markup) and the template's per-category headings and
 * Education block. Change them together.
 *
 * Also shows only the date fields the category uses (Component.SINGLE_DATE):
 * honors/certs have one date, projects hide the end date behind a link.
 * Tech stack is projects-only (Component.save() clears it otherwise), and so
 * is In progress for certifications; ticking it hides (but keeps) the date.
 */
(function () {
    var form = document.querySelector('form.edit-form');
    var sheet = document.getElementById('component-preview');
    if (!form || !sheet) return;
    var isEducation = !!form.elements['school'];

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

    // date_or_range: projects show just the start unless an end is set.
    function dateOrRange(start, end) {
        return fmtDate(end) ? dateRange(start, end) : fmtDate(start);
    }

    // bullet_markup: escape first, then **bold** (non-greedy, single line).
    function bulletHtml(text) {
        return escapeHtml(text).replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
    }

    function val(name) {
        var el = form.elements[name];
        return el ? el.value.trim() : '';
    }

    function checked(name) {
        var el = form.elements[name];
        return !!(el && el.checked);
    }

    function row(left, right, cls) {
        return '<div class="rs-row' + (cls ? ' ' + cls : '') + '"><span>' + left + '</span><span>' + right + '</span></div>';
    }

    function titleWith(title, extra) {
        var html = '<strong>' + escapeHtml(title) + '</strong>';
        if (extra) html += ' | <em>' + escapeHtml(extra) + '</em>';
        return html;
    }

    // Inline formset rows by their text field (bullet `text`, course `name`).
    function inlineRows(field) {
        var rows = [];
        form.querySelectorAll('[name$="-' + field + '"]').forEach(function (input, index) {
            var prefix = input.name.slice(0, -field.length);
            var del = form.elements[prefix + 'DELETE'];
            var text = input.value.trim();
            if (!text || (del && del.checked)) return;
            var order = parseInt(val(prefix + 'order'), 10);
            rows.push({ text: text, order: isNaN(order) ? 0 : order, index: index });
        });
        // order_by('order', 'id'): unsaved rows come last in the form, so row index stands in for id.
        rows.sort(function (a, b) { return a.order - b.order || a.index - b.index; });
        return rows;
    }

    // Education block: resumeSubheading {school}{location}{degree, GPA}{date_range},
    // then a Relevant Coursework item. The PDF shows GPA only with the preset's
    // include_gpa and only the courses a preset picks; here we show all of both.
    function renderEducation() {
        var html = '<h3 class="rs-section">Education</h3>';
        var degree = escapeHtml(val('degree'));
        var gpa = parseFloat(val('gpa'));
        if (!isNaN(gpa)) degree += ', GPA: ' + gpa.toFixed(2);
        html += row('<strong>' + escapeHtml(val('school')) + '</strong>', escapeHtml(val('location')));
        html += row('<em>' + degree + '</em>', '<em>' + dateRange(val('start_date'), val('end_date')) + '</em>', 'rs-small');
        var courses = inlineRows('name');
        if (courses.length) {
            html += '<ul class="rs-bullets"><li><strong>Relevant Coursework</strong>: ' + courses.map(function (c) {
                return escapeHtml(c.text);
            }).join(', ') + '</li></ul>';
        }
        sheet.innerHTML = html;
    }

    function render() {
        if (isEducation) return renderEducation();
        var category = val('category');
        var title = val('title');
        var org = val('organization');
        var html = '<h3 class="rs-section">' + (SECTION_TITLES[category] || '') + '</h3>';

        if (category === 'project') {
            html += row(titleWith(title, val('tech_stack')), dateOrRange(val('start_date'), val('end_date')), 'rs-small');
        } else if (category === 'certification' || category === 'honor') {
            var when = category === 'certification' && checked('in_progress') ? 'In Progress' : fmtDate(val('start_date'));
            html += row(titleWith(title, org), when, 'rs-small');
        } else {
            html += row('<strong>' + escapeHtml(title) + '</strong>', dateRange(val('start_date'), val('end_date')));
            html += row('<em>' + escapeHtml(org) + '</em>', '<em>' + escapeHtml(val('location')) + '</em>', 'rs-small');
        }

        var items = inlineRows('text');
        if (items.length) {
            html += '<ul class="rs-bullets">' + items.map(function (b) {
                return '<li>' + bulletHtml(b.text) + '</li>';
            }).join('') + '</ul>';
        }
        sheet.innerHTML = html;
    }

    var startRow = form.querySelector('[data-field="start_date"]');
    var endRow = form.querySelector('[data-field="end_date"]');
    var techRow = form.querySelector('[data-field="tech_stack"]');
    var progressRow = form.querySelector('[data-field="in_progress"]');
    var addEnd = document.getElementById('add-end-date');
    var endExpanded = false;

    function syncFields() {
        if (isEducation) return;
        var category = val('category');
        var project = category === 'project';
        if (techRow) {
            if (!project) form.elements['tech_stack'].value = '';
            techRow.hidden = !project;
        }
        var cert = category === 'certification';
        if (progressRow) {
            if (!cert) form.elements['in_progress'].checked = false;
            progressRow.hidden = !cert;
        }
        if (!startRow || !endRow) return;
        startRow.hidden = cert && checked('in_progress');
        var single = category === 'honor' || category === 'certification';
        if (single) form.elements['end_date'].value = '';
        var showEnd = !single && (!project || endExpanded || val('end_date') !== '');
        endRow.hidden = !showEnd;
        if (addEnd) addEnd.hidden = !project || showEnd;
        startRow.querySelector('label').textContent = single || (project && !showEnd) ? 'Date' : 'Start date';
    }

    if (addEnd) {
        addEnd.querySelector('a').addEventListener('click', function (e) {
            e.preventDefault();
            endExpanded = true;
            syncFields();
            form.elements['end_date'].focus();
        });
    }

    form.addEventListener('input', render);
    form.addEventListener('change', function (e) {
        if (e.target.name === 'category' || e.target.name === 'in_progress') syncFields();
        render();
    });
    syncFields();
    render();
})();
