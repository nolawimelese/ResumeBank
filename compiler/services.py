"""
The compile pipeline: preset -> .tex (Jinja2) -> .pdf (pdflatex) -> page count (pypdf).

Two entry points share the same render/compile code so the live preview in
the workspace and the "save to history" action can never drift apart:

    compile_preview(preset)     writes media/previews/<preset_id>/resume.pdf, no DB row
    compile_to_history(preset)  creates a Resume row with the pdf/tex attached

Jinja2 is configured with LaTeX-safe delimiters (\\BLOCK{}, \\VAR{}, \\#{}) so
template syntax never collides with LaTeX braces. Every user string goes
through `latex_escape`; bullet text additionally goes through `bullet_markup`
(escape first, then `**bold**` -> \\textbf{}).
"""
import re
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path

from django.conf import settings
from django.core.files.base import ContentFile
from jinja2 import Environment, FileSystemLoader
from pypdf import PdfReader

from bank.models import Component, Education, Profile, Skill

from .models import Resume

LATEX_DIR = settings.BASE_DIR / 'templates' / 'latex'
PREVIEW_DIR = Path(settings.MEDIA_ROOT) / 'previews'
PDFLATEX_TIMEOUT = 60

# A single regex pass so the backslash replacement is never itself re-escaped.
_ESCAPES = {
    '\\': r'\textbackslash{}',
    '&': r'\&',
    '%': r'\%',
    '$': r'\$',
    '#': r'\#',
    '_': r'\_',
    '{': r'\{',
    '}': r'\}',
    '~': r'\textasciitilde{}',
    '^': r'\textasciicircum{}',
}
_ESCAPE_RE = re.compile('|'.join(re.escape(c) for c in _ESCAPES))
_BOLD_RE = re.compile(r'\*\*(.+?)\*\*')
_URL_SCHEME_RE = re.compile(r'^https?://(www\.)?')

# Section headings as Jake's template prints them; Component.Category labels are singular.
SECTION_TITLES = {
    Component.Category.EXPERIENCE: 'Experience',
    Component.Category.PROJECT: 'Projects',
    Component.Category.LEADERSHIP: 'Leadership',
    Component.Category.HONOR: 'Honors',
    Component.Category.CERTIFICATION: 'Certifications',
}


def latex_escape(value):
    if value is None:
        return ''
    return _ESCAPE_RE.sub(lambda m: _ESCAPES[m.group()], str(value))


def bullet_markup(value):
    """Escape first, then convert `**bold**`; the emitted \\textbf must not itself be escaped."""
    return _BOLD_RE.sub(r'\\textbf{\1}', latex_escape(value))


def fmt_date(d):
    """'Jun. 2025' the way Jake's template writes dates; May needs no period."""
    if d is None:
        return ''
    mon = d.strftime('%b')
    return f'{mon} {d.year}' if mon == 'May' else f'{mon}. {d.year}'


def date_range(start, end):
    """Null end means Present (Honor/Certification pass only start, see Component)."""
    if start is None:
        return ''
    return f'{fmt_date(start)} -- {fmt_date(end) if end else "Present"}'


def jinja_env():
    env = Environment(
        loader=FileSystemLoader(LATEX_DIR),
        block_start_string=r'\BLOCK{', block_end_string='}',
        variable_start_string=r'\VAR{', variable_end_string='}',
        comment_start_string=r'\#{', comment_end_string='}',
        trim_blocks=True, lstrip_blocks=True, autoescape=False,
    )
    env.filters['latex'] = latex_escape
    env.filters['bullet'] = bullet_markup
    env.filters['date'] = fmt_date
    env.filters['date_range'] = date_range
    return env


def header_parts(profile, links):
    """The `phone | email | links | location` line, already LaTeX-escaped."""
    parts = []
    if profile.phone:
        parts.append(latex_escape(profile.phone))
    if profile.email:
        parts.append(f'\\href{{mailto:{profile.email}}}{{\\underline{{{latex_escape(profile.email)}}}}}')
    for link in links:
        display = _URL_SCHEME_RE.sub('', link.url).rstrip('/')
        parts.append(f'\\href{{{link.url}}}{{\\underline{{{latex_escape(display)}}}}}')
    if profile.location:
        parts.append(latex_escape(profile.location))
    return parts


def resolve_preset(preset):
    """Everything the template needs, fetched in a handful of queries."""
    profile = Profile.load()
    links = list(profile.links.all())

    preset_components = (
        preset.preset_components.select_related('component')
        .prefetch_related('preset_bullets__bullet')
        .order_by('order', 'id')
    )
    by_category = {c: [] for c in Component.Category}
    for pc in preset_components:
        by_category[pc.component.category].append({
            'component': pc.component,
            'bullets': [pb.bullet for pb in pc.preset_bullets.all()],
        })
    sections = [
        {'category': cat, 'label': SECTION_TITLES[cat], 'entries': by_category[cat]}
        for cat in Component.Category
    ]

    preset_skills = preset.preset_skills.select_related('skill').order_by('order', 'id')
    by_group = {g: [] for g in Skill.Group}
    for ps in preset_skills:
        by_group[ps.skill.group].append(ps.skill.name)
    skill_groups = [{'label': g.label, 'names': by_group[g]} for g in Skill.Group if by_group[g]]

    return {
        'preset': preset,
        'profile': profile,
        'header_parts': header_parts(profile, links),
        'educations': list(Education.objects.prefetch_related('coursework')),
        'sections': sections,
        'skill_groups': skill_groups,
    }


def render_tex(preset):
    template = jinja_env().get_template(f'{preset.template}.tex.j2')
    return template.render(**resolve_preset(preset))


@dataclass
class CompileResult:
    ok: bool
    tex: str
    log: str = ''
    pdf: bytes | None = None
    page_count: int | None = None
    error: str = ''
    # Filled in by compile_preview.
    pdf_url: str = ''
    version: int = 0

    @property
    def log_tail(self):
        return '\n'.join(self.log.splitlines()[-40:])


class CompileError(Exception):
    def __init__(self, result):
        super().__init__(result.error)
        self.result = result


def compile_tex(tex):
    """Run pdflatex on `tex` in a temp dir; LaTeX failures come back as ok=False, not exceptions."""
    with tempfile.TemporaryDirectory() as tmp:
        tmpdir = Path(tmp)
        (tmpdir / 'resume.tex').write_text(tex, encoding='utf-8')
        try:
            subprocess.run(
                ['pdflatex', '-interaction=nonstopmode', '-halt-on-error', 'resume.tex'],
                cwd=tmpdir, capture_output=True, timeout=PDFLATEX_TIMEOUT,
            )
        except FileNotFoundError:
            return CompileResult(ok=False, tex=tex, error='pdflatex not found on PATH')
        except subprocess.TimeoutExpired:
            return CompileResult(ok=False, tex=tex, error=f'pdflatex timed out after {PDFLATEX_TIMEOUT}s')

        log_path = tmpdir / 'resume.log'
        log = log_path.read_text(encoding='utf-8', errors='replace') if log_path.exists() else ''
        pdf_path = tmpdir / 'resume.pdf'
        if not pdf_path.exists():
            error = next((line for line in log.splitlines() if line.startswith('!')), 'pdflatex failed')
            return CompileResult(ok=False, tex=tex, log=log, error=error)

        pdf = pdf_path.read_bytes()
        page_count = len(PdfReader(BytesIO(pdf)).pages)
        return CompileResult(ok=True, tex=tex, log=log, pdf=pdf, page_count=page_count)


def compile_preset(preset):
    return compile_tex(render_tex(preset))


def compile_preview(preset):
    """Compile for the workspace pane. Overwrites media/previews/<id>/; keeps the last good PDF on failure."""
    result = compile_preset(preset)
    out = PREVIEW_DIR / str(preset.pk)
    out.mkdir(parents=True, exist_ok=True)
    (out / 'resume.tex').write_text(result.tex, encoding='utf-8')
    pdf_path = out / 'resume.pdf'
    if result.ok:
        pdf_path.write_bytes(result.pdf)
    if pdf_path.exists():
        result.pdf_url = f'{settings.MEDIA_URL}previews/{preset.pk}/resume.pdf'
        result.version = pdf_path.stat().st_mtime_ns
    return result


def compile_to_history(preset):
    """Full compile that records a Resume row. Raises CompileError, leaving no row behind."""
    result = compile_preset(preset)
    if not result.ok:
        raise CompileError(result)
    # Saved first so resume_upload_path has a pk to build the directory from.
    resume = Resume.objects.create(
        preset=preset,
        preset_name=preset.name,
        page_count=result.page_count,
        over_limit=result.page_count > preset.page_limit,
    )
    resume.pdf_file.save('resume.pdf', ContentFile(result.pdf), save=False)
    resume.tex_file.save('resume.tex', ContentFile(result.tex.encode('utf-8')), save=False)
    resume.save()
    return resume


def delete_preview(preset_id):
    shutil.rmtree(PREVIEW_DIR / str(preset_id), ignore_errors=True)
