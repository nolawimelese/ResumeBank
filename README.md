# ResumeBank

A personal & local tool for managing resume components as a reusable database, then assembling tailored resumes from them.

## Overview

ResumeBank stores reusable resume components (Experience, Projects, Leadership), and dynamically assembles them into resumes. Each tailored resume is saved as a preset, which is a specific selection and ordering of components.

## Tech Stack

Framework: Django

Database: SQLite

PDF: Jinja2 renders a `.tex` template, compiled with `pdflatex` (requires a TeX distribution such as MiKTeX or TeX Live on PATH)

## Roadmap

<details>

<summary>Foundations</summary>

- [x] Set up venv
- [x] Build Django App (`bank`, `presets`, `compiler`)
- Define database schema and models
  - [ ] Profile + Link
  - [ ] Education + Coursework
  - [ ] Component + Bullet
  - [ ] Skill
  - [ ] ResumePreset + PresetComponent / PresetBullet / PresetSkill
  - [ ] Resume (compile history)
- [ ] Set up SQLite and some test data
- Set up pages
  - [ ] Component manager (Components, Skills, Education, Profile)
  - [ ] Resume Builder (includes clone-preset button)
- Compile pipeline
  - [ ] Jake's Resume `.tex.j2` template
  - [ ] Jinja2 render -> pdflatex -> pypdf page count
  - [ ] Compile view, PDF download, history

  </details>
