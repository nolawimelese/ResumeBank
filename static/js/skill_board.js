// Skills board (bank/_skill_board.html): each group is a list of editable rows plus a blank "add" row.
// Editing a name saves on change (blur / Enter), the add row is a plain hx-post form, and the ⠿ handle drags a
// row to reorder or regroup it. Every POST swaps the whole #skill-board, so all handlers here are delegated on
// document and survive the swap, and focus is carried across the swap so typing is never interrupted.
(function () {
    function board() { return document.getElementById('skill-board'); }

    function post(url, values) {
        return htmx.ajax('POST', url, {source: board(), target: '#skill-board', swap: 'outerHTML', values: values});
    }

    // The inputs of one group's list, in order: every skill name, then the add row.
    function inputsOf(el) {
        var list = el.closest('.skill-list');
        return list ? Array.from(list.querySelectorAll('input.skill-name, .skill-add input[name=names]')) : [];
    }

    // ---- Rename: the name is always an input; a change saves it, blank reverts ----
    document.addEventListener('change', function (e) {
        var input = e.target.closest && e.target.closest('#skill-board input.skill-name');
        if (!input) return;
        var name = input.value.trim();
        if (!name || name === input.dataset.original) {
            input.value = input.dataset.original;
            return;
        }
        post(input.closest('.skill-row').dataset.renameUrl, {name: name});
    });

    // ---- Keyboard: Enter / ↑ / ↓ move between rows, Esc reverts, Backspace in an empty add row goes up ----
    document.addEventListener('keydown', function (e) {
        var input = e.target.closest && e.target.closest('#skill-board input.skill-name, #skill-board .skill-add input[name=names]');
        if (!input) return;
        var isName = input.classList.contains('skill-name');
        var inputs = inputsOf(input), i = inputs.indexOf(input);
        if (e.key === 'ArrowUp' && i > 0) {
            e.preventDefault(); inputs[i - 1].focus();
        } else if (e.key === 'ArrowDown' && i < inputs.length - 1) {
            e.preventDefault(); inputs[i + 1].focus();
        } else if (isName && e.key === 'Enter') {
            e.preventDefault(); inputs[i + 1].focus();  // blurring fires change, which saves
        } else if (isName && e.key === 'Escape') {
            input.value = input.dataset.original;
            input.blur();
        } else if (!isName && e.key === 'Backspace' && !input.value && i > 0) {
            e.preventDefault(); inputs[i - 1].focus();
        }
    });

    // ---- Add: pasted lines become comma-separated (a text input would drop the newlines) ----
    document.addEventListener('paste', function (e) {
        var input = e.target.closest && e.target.closest('#skill-board .skill-add input[name=names]');
        if (!input) return;
        var text = (e.clipboardData || window.clipboardData).getData('text');
        if (!/[\r\n]/.test(text)) return;
        e.preventDefault();
        input.setRangeText(text.split(/\r?\n/).map(function (s) { return s.trim(); }).filter(Boolean).join(', '),
            input.selectionStart, input.selectionEnd, 'end');
    });

    // ---- Focus across swaps: note which row has focus just before the new board goes in, then restore it ----
    // Captured at swap time (not request time) because a blur-save fires before focus reaches the next row.
    var refocus = null;
    document.addEventListener('htmx:beforeSwap', function (e) {
        if (!e.detail.target || e.detail.target.id !== 'skill-board') return;
        var el = document.activeElement;
        refocus = null;
        if (!el || !el.closest('#skill-board')) return;
        if (el.matches('input.skill-name')) {
            refocus = {id: el.closest('.skill-row').dataset.id, value: el.value,
                       start: el.selectionStart, end: el.selectionEnd};
        } else if (el.matches('.skill-add input[name=names]')) {
            refocus = {group: el.closest('.skill-list').dataset.group};
        }
    });
    document.addEventListener('htmx:afterSettle', function () {
        if (!refocus) return;
        var r = refocus, input;
        refocus = null;
        if (r.id) {
            input = document.querySelector('#skill-board .skill-row[data-id="' + r.id + '"] input.skill-name');
            if (!input) return;
            input.value = r.value;  // keep what's being typed if the swap landed mid-edit
            input.focus();
            input.setSelectionRange(r.start, r.end);
        } else {
            input = document.querySelector('#skill-board .skill-list[data-group="' + r.group + '"] .skill-add input[name=names]');
            if (input) input.focus();
        }
    });

    // ---- Drag: the ⠿ handle drags its row; dropping POSTs the target group's new order ----
    var dragging = null, home = null, dropped = false;

    function rowsOf(list) {
        return Array.from(list.querySelectorAll(':scope > .skill-row:not(.add)'));
    }

    document.addEventListener('dragstart', function (e) {
        var handle = e.target.closest && e.target.closest('#skill-board .handle');
        if (!handle) return;
        var row = handle.closest('.skill-row');
        dragging = row;
        home = {parent: row.parentNode, next: row.nextSibling};
        dropped = false;
        e.dataTransfer.effectAllowed = 'move';
        e.dataTransfer.setData('text/plain', row.dataset.id);
        var r = row.getBoundingClientRect();
        e.dataTransfer.setDragImage(row, e.clientX - r.left, e.clientY - r.top);
        setTimeout(function () { row.classList.add('dragging'); }, 0);  // after the browser snapshots the drag image
    });

    // The row the dragged one should go before, given the pointer's height; none means "at the end".
    function rowAfter(list, y) {
        return rowsOf(list).filter(function (r) { return r !== dragging; }).find(function (r) {
            var b = r.getBoundingClientRect();
            return y < b.top + b.height / 2;
        });
    }

    document.addEventListener('dragover', function (e) {
        if (!dragging) return;
        var card = e.target.closest && e.target.closest('#skill-board .skill-card');
        var list = card && card.querySelector('.skill-list');
        if (!list) return;
        e.preventDefault();
        e.dataTransfer.dropEffect = 'move';
        document.querySelectorAll('#skill-board .skill-list.drop-target').forEach(function (l) {
            if (l !== list) l.classList.remove('drop-target');
        });
        list.classList.add('drop-target');
        var before = rowAfter(list, e.clientY) || list.querySelector(':scope > .skill-row.add');
        if (dragging.nextSibling !== before) list.insertBefore(dragging, before);
    });

    document.addEventListener('drop', function (e) {
        if (!dragging) return;
        var list = dragging.parentNode;
        if (!list.closest('#skill-board')) return;
        e.preventDefault();
        dropped = true;
        if (list === home.parent && dragging.nextSibling === home.next) return;
        var ids = rowsOf(list).map(function (r) { return r.dataset.id; });
        post(board().dataset.moveUrl, {pk: dragging.dataset.id, group: list.dataset.group, ids: ids});
    });

    document.addEventListener('dragend', function () {
        if (!dragging) return;
        dragging.classList.remove('dragging');
        document.querySelectorAll('#skill-board .skill-list.drop-target').forEach(function (l) { l.classList.remove('drop-target'); });
        if (!dropped) home.parent.insertBefore(dragging, home.next);  // dropped outside a group: put it back
        dragging = home = null;
    });
})();
