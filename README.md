# ResumeBank

A personal & local tool for managing resume components as a reusable database, then assembling tailored resumes from them.

## Overview

ResumeBank stores reusable resume components (Experience, Projects, Leadership), and dynamically assembles them into resumes. Each tailored resume is saved as a preset, which is a specific selection and ordering of components.

## Tech Stack

Framework: Django

Database: SQLite

PDF: Jinja2 renders a `.tex` template, compiled with `pdflatex` (requires a TeX distribution such as MiKTeX or TeX Live on PATH)

## Pages

| URL                 | Page                                                                                   |
| ------------------- | -------------------------------------------------------------------------------------- |
| `/`                 | Component Manager: profile, education, components + bullets, skills                    |
| `/presets/`         | Resumes: one row per preset, with create / clone / delete                              |
| `/presets/<id>/`    | Workspace: pick and order pieces on the left, the compiled PDF re-renders on the right |
| `/compile/history/` | Every "Save to history" compile, with PDF and `.tex` downloads                         |

## Setup

```
python -m venv .venv
.venv\Scripts\activate        # source .venv/bin/activate on macOS/Linux
pip install -r requirements.txt
python manage.py migrate
python manage.py seed           # loads test data; safe to re-run, wipes and reloads
python manage.py runserver
```

`seed` fills the bank with a sample profile, education, components with bullets, skills, and three presets (`General`, `Backend Internship`, `ML Research`). Run `python manage.py createsuperuser` to browse it all in `/admin`.

## Roadmap

<details>

<summary>Foundations</summary>

- [x] Set up venv
- [x] Build Django Apps (`bank`, `presets`, `compiler`)
- Define database schema and models
  - [x] Profile + Link
  - [x] Education + Coursework
  - [x] Component + Bullet
  - [x] Skill
  - [x] ResumePreset + PresetComponent / PresetBullet / PresetSkill
  - [x] Resume (compile history)
- [x] Set up SQLite and some test data
- Set up pages
  - [x] Component manager (Components, Skills, Education, Profile)
  - [x] Resumes list (create / clone / delete presets)
  - [x] Workspace: structure form on the left, live PDF preview on the right (auto-save + recompile via HTMX)
  - [x] Compile history page with PDF / .tex downloads
- Compile pipeline
  - [x] Jake's Resume `.tex.j2` template
  - [x] Jinja2 render -> pdflatex -> pypdf page count
  - [x] Preview compile (no history row) and "Save to history" compile

- [x] Working app!

</details>

<details>

<summary>Polishes</summary>

We're gonna work top down to make sure every part of the process is straight

- [x] Header config
  - [x] toggles
    - [x] config for location, contact
    - [x] professional links
- [x] Switch ordering system from numbers to arrows
- [x] Education selection per preset
  - [x] Add Degree dropdown selection ex. PhD, MS, MEng, B.S., B.A.
- [x] Add preview to component editing
- [x] Add checkbox for "in progress" certifications

on hold

- [x] Make honors display below Education

</details>
