# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

ResumeBank is a single-user, local Django app. It stores reusable resume pieces (experience, projects, skills, education, header) in SQLite, lets the user assemble a **preset** (a selection + ordering of those pieces), and compiles the preset to PDF by rendering a Jinja2 `.tex` template and shelling out to `pdflatex`. The design docs live in `docs/` (`datamodel.md`, `features.md`, `techstack.md`) — note `docs/` is gitignored, so it exists only on the local machine.

## Commands

The venv is at `.venv/` (Windows; `.vscode/settings.json` points the interpreter at `.venv\Scripts\python.exe`). Use it for everything:

```
.venv\Scripts\activate
python manage.py runserver
python manage.py makemigrations && python manage.py migrate
python manage.py createsuperuser        # admin at /admin/ is the only data-entry UI so far
python manage.py test                   # all apps
python manage.py test bank              # one app
python manage.py test bank.tests.SomeTestCase.test_name   # one test
pip install -r requirements.txt
```

External prerequisite for the compile pipeline: a TeX distribution (MiKTeX / TeX Live) with `pdflatex` on PATH. MiKTeX auto-installs missing packages on first compile, which looks like a hang.

## Architecture

Three Django apps, one project package (`ResumeBank/`), project-level `templates/base.html` and `static/css/site.css`.

| App | URL prefix | Role |
|---|---|---|
| `bank` | `/` | Source data: `Profile`+`Link`, `Education`+`Coursework`, `Component`+`Bullet`, `Skill`. Standalone Component Manager CRUD (`bank/forms.py` ModelForms + one-level inline formsets). |
| `presets` | `/presets/` | `ResumePreset` and its join tables `PresetComponent` / `PresetBullet` / `PresetSkill` / `PresetCoursework`. Preset list and the **workspace** page. |
| `compiler` | `/compile/` | `Resume` — immutable compile-history rows. `compiler/services.py` owns the Jinja2 → pdflatex → pypdf pipeline; views are the preview / save-to-history endpoints the workspace calls, plus the history page. |

### Page model

The workspace (`/presets/<id>/`, `presets/templates/presets/workspace.html`) is Overleaf-style: the structure form on the left auto-saves, the real PDF on the right recompiles. Wiring, all HTMX (vendored at `static/js/htmx.min.js`):

1. Any `input` in `#structure` (debounced 500 ms) → `POST /presets/<id>/save/` → `presets.views.save` rewrites the join tables in one transaction and returns the `#save-status` fragment with an `HX-Trigger: preset-saved` header.
2. `#preview` listens for `preset-saved from:body` (and `load`) → `GET /compile/<id>/preview/` → `compiler.views.preview` runs `services.compile_preview`, which writes `media/previews/<id>/resume.pdf` (no `Resume` row) and returns the pane fragment (`compiler/_preview.html`: page-count strip + cache-busted `<iframe>`, or the LaTeX log tail on failure — the last good PDF stays visible).
3. "Save to history" → `POST /compile/<id>/` → `services.compile_to_history` creates the `Resume` row. LaTeX failure raises `CompileError` and leaves no row.

Preview and history compiles share `render_tex` / `compile_tex`, so they cannot drift. There is no compile cache: pdflatex runs on every preview (~0.5 s locally).

### Data model decisions (read these before touching models)

- **`Component` is one table** for Experience / Project / Leadership / Honor / Certification, distinguished by `category`. Do not add per-category models. Honor/Certification store their single date in `start_date`; for other categories a null `end_date` means "Present".
- **`Profile` is a singleton** (`save()` forces `pk=1`; fetch with `Profile.load()`). `ProfileAdmin.has_add_permission` enforces it in admin.
- **Presets hold references, not copies.** A `ResumePreset` stores no id lists; membership is entirely the four join tables, each with an `order` field and a uniqueness constraint per (preset, row). Editing a bank row therefore propagates to every preset. `PresetBullet` points at `PresetComponent` (not the preset) so a bullet can only be selected under a component that is itself in the preset. `PresetCoursework` points straight at the preset because every `Education` always renders; it only picks which courses go on that degree's "Relevant Coursework" line (no picks → no line). There is no `include_coursework` toggle any more.
- **`order` is not unique** — just sort by it. Section order is fixed by the LaTeX template; `order` only sorts within a section/group.
- **Delete-with-warning is a query**, not a scan: `component.presetcomponent_set.exists()`, `skill.presetskill_set.exists()`, `bullet.presetbullet_set.exists()`, `coursework.presetcoursework_set.exists()` (the join tables deliberately use default reverse accessors from the bank side, and `related_name` only from the preset side).
- **`Resume` rows are history.** `preset` is `SET_NULL` with `preset_name` snapshotted; `page_count`/`over_limit` are computed at compile time. Files go to `media/resumes/<resume_id>/` via `resume_upload_path`, so the row must be saved (pk assigned) before files are attached.

### Implementation conventions

- **Workspace form**: one plain HTML form per preset — every component/bullet/skill/course row is a checkbox plus an order number input, named `comp_<id>` / `bullet_<id>` / `skill_<id>` / `course_<id>` with `_order` siblings (`presets/templates/presets/_structure_form.html`). `presets.views.save` parses those and delete-and-recreates the join tables; a `bullet_*` whose parent `comp_*` is unchecked is dropped. No Django formsets there. The Component Manager does use formsets, but only one level deep (Component→Bullet, Education→Coursework, Profile→Link).
- **LaTeX rendering**: `compiler.services.jinja_env()` uses LaTeX-safe delimiters (`\BLOCK{...}`, `\VAR{...}`, `\#{...}`; note a Jinja comment ends at the first `}`) and renders `templates/latex/<preset.template>.tex.j2`. Apply the `latex` filter to every user string and `bullet` to bullet text (`**bold**` → `\textbf{}`; escape first, then markup). Section headings come from `services.SECTION_TITLES`; empty sections are skipped. Don't name a template dict key `items` — Jinja resolves it to `dict.items`.
- **Compile**: `services.compile_tex` runs `pdflatex -interaction=nonstopmode -halt-on-error` in a temp dir with a 60 s timeout and returns a `CompileResult` (never raises for LaTeX errors; `ok=False` + first `!` log line). Inline in the view, no task queue. Page count via `pypdf`. The template deliberately imports no `babel` / `fontawesome5` / `marvosym`: TinyTeX here lacks them and Jake's template never uses them.
- **HTMX conventions**: CSRF via `hx-headers` on `<body>` in `base.html`; fragments live in `_*.html` templates; the top-bar history slot only shows flash messages when rendered as the HTMX response (`show_messages`), because `base.html` already renders them on full pages.
