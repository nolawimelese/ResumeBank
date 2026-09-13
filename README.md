# ResumeBank

A personal & local tool for managing resume components as a reusable database, then assembling tailored resumes from them.

## Overview

ResumeBank stores reusable resume components (Experience, Projects, Leadership), and dynamically assembles them into resumes. Each tailored resume is saved as a preset, which is a specific selection and ordering of components.

## Tech Stack

Framework: Django

Database: SQLite

PDF: Jinja2 renders a `.tex` template, compiled with `pdflatex` (requires a TeX distribution such as MiKTeX or TeX Live on PATH)

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
  - [ ] Component manager (Components, Skills, Education, Profile)
  - [ ] Resume Builder (includes clone-preset button)
- Compile pipeline
  - [ ] Jake's Resume `.tex.j2` template
  - [ ] Jinja2 render -> pdflatex -> pypdf page count
  - [ ] Compile view, PDF download, history

  </details>
