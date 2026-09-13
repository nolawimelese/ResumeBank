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
| `bank` | `/` | Source data: `Profile`+`Link`, `Education`+`Coursework`, `Component`+`Bullet`, `Skill` |
| `presets` | `/presets/` | `ResumePreset` and its join tables `PresetComponent` / `PresetBullet` / `PresetSkill` |
| `compiler` | `/compile/` | `Resume` — immutable compile-history rows; will own the Jinja2 → pdflatex → pypdf pipeline |

Current state: models, migrations, and admin registrations exist; each app's `views.py`/`urls.py` is a single placeholder `index`. The README roadmap lists what is next (component manager pages, resume builder, compile pipeline).

### Data model decisions (read these before touching models)

- **`Component` is one table** for Experience / Project / Leadership / Honor / Certification, distinguished by `category`. Do not add per-category models. Honor/Certification store their single date in `start_date`; for other categories a null `end_date` means "Present".
- **`Profile` is a singleton** (`save()` forces `pk=1`; fetch with `Profile.load()`). `ProfileAdmin.has_add_permission` enforces it in admin.
- **Presets hold references, not copies.** A `ResumePreset` stores no id lists; membership is entirely the three join tables, each with an `order` field and a uniqueness constraint per (preset, row). Editing a bank row therefore propagates to every preset. `PresetBullet` points at `PresetComponent` (not the preset) so a bullet can only be selected under a component that is itself in the preset.
- **`order` is not unique** — just sort by it. Section order is fixed by the LaTeX template; `order` only sorts within a section/group.
- **Delete-with-warning is a query**, not a scan: `component.presetcomponent_set.exists()`, `skill.presetskill_set.exists()`, `bullet.presetbullet_set.exists()` (the join tables deliberately use default reverse accessors from the bank side, and `related_name` only from the preset side).
- **`Resume` rows are history.** `preset` is `SET_NULL` with `preset_name` snapshotted; `page_count`/`over_limit` are computed at compile time. Files go to `media/resumes/<resume_id>/` via `resume_upload_path`, so the row must be saved (pk assigned) before files are attached.

### Planned implementation conventions (from `docs/`)

- **Builder UI**: one plain HTML form per preset — every component/bullet/skill row is a checkbox plus an order number input. The view parses `comp_<id>` / `bullet_<id>` / `skill_<id>` and their `_order` siblings from `request.POST` and rewrites the join tables in one transaction. No Django formsets; reach for HTMX before any frontend framework.
- **LaTeX rendering**: Jinja2 environment with LaTeX-safe delimiters (`\BLOCK{...}`, `\VAR{...}`, `\#{...}`) rendering `templates/latex/jakes.tex.j2` (Jake's Resume). A `latex_escape` filter must be applied to every user string (`& % $ # _ { } ~ ^ \`). Bullet text supports exactly one markup: `**bold**` → `\textbf{}`. Escape first, then convert the markup.
- **Compile**: `subprocess.run(["pdflatex", "-interaction=nonstopmode", "-halt-on-error", "resume.tex"], cwd=tmpdir, timeout=60)` in a temp dir, then copy `.pdf`/`.tex` into media. Runs inline in the view — no task queue. Page count via `pypdf`.
