"""
Preset pages. The workspace is the Overleaf-style page: structure form on the
left (auto-saved through `save`), live PDF on the right (served by
compiler.views.preview). Section order is fixed by the LaTeX template, so the
form only lets the user pick rows and order them within a section.
"""
import re

from django.contrib import messages
from django.db import transaction
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from bank.models import Bullet, Component, Coursework, Education, Skill
from compiler.services import SECTION_TITLES, delete_preview

from .models import PresetBullet, PresetComponent, PresetCoursework, PresetSkill, ResumePreset

_KEY_RE = re.compile(r'^(comp|bullet|skill|course)_(\d+)$')


def preset_list(request):
    presets = ResumePreset.objects.prefetch_related('resumes')
    return render(request, 'presets/list.html', {'presets': presets})


@require_POST
def create(request):
    name = request.POST.get('name', '').strip()
    if not name:
        messages.error(request, 'Give the preset a name.')
        return redirect('presets:list')
    if ResumePreset.objects.filter(name=name).exists():
        messages.error(request, f'A preset named "{name}" already exists.')
        return redirect('presets:list')
    preset = ResumePreset.objects.create(name=name)
    return redirect('presets:workspace', pk=preset.pk)


def workspace(request, pk):
    preset = get_object_or_404(ResumePreset, pk=pk)
    return render(request, 'presets/workspace.html', {
        'preset': preset,
        'educations': _education_groups(preset),
        'sections': _component_sections(preset),
        'skill_groups': _skill_groups(preset),
    })


def _education_groups(preset):
    """Every Education (always rendered) with its courses, annotated with this preset's picks and order."""
    picked = {pc.coursework_id: pc.order for pc in preset.preset_coursework.all()}
    return [
        {
            'education': edu,
            'entries': [
                {'course': c, 'checked': c.pk in picked, 'order': picked.get(c.pk, c.order)}
                for c in edu.coursework.all()
            ],
        }
        for edu in Education.objects.prefetch_related('coursework')
    ]


def _component_sections(preset):
    """Every bank Component with its bullets, annotated with this preset's picks and order."""
    picked = {pc.component_id: pc for pc in preset.preset_components.prefetch_related('preset_bullets')}
    by_category = {c: [] for c in Component.Category}
    for component in Component.objects.prefetch_related('bullets'):
        pc = picked.get(component.pk)
        bullet_picks = {pb.bullet_id: pb.order for pb in pc.preset_bullets.all()} if pc else {}
        by_category[component.category].append({
            'component': component,
            'checked': pc is not None,
            'order': pc.order if pc else 0,
            'bullets': [
                {'bullet': b, 'checked': b.pk in bullet_picks, 'order': bullet_picks.get(b.pk, b.order)}
                for b in component.bullets.all()
            ],
        })
    return [
        {'label': SECTION_TITLES[cat], 'entries': entries}
        for cat, entries in by_category.items() if entries
    ]


def _skill_groups(preset):
    picked = {ps.skill_id: ps.order for ps in preset.preset_skills.all()}
    by_group = {g: [] for g in Skill.Group}
    for skill in Skill.objects.all():
        by_group[skill.group].append({
            'skill': skill,
            'checked': skill.pk in picked,
            'order': picked.get(skill.pk, skill.order),
        })
    return [{'label': g.label, 'entries': entries} for g, entries in by_group.items() if entries]


def _parse_picks(post):
    """{'comp': {id: order}, 'bullet': {...}, 'skill': {...}, 'course': {...}} from checked boxes and their _order siblings."""
    picks = {'comp': {}, 'bullet': {}, 'skill': {}, 'course': {}}
    for key in post:
        m = _KEY_RE.match(key)
        if m:
            kind, row_id = m.group(1), int(m.group(2))
            picks[kind][row_id] = _to_int(post.get(f'{key}_order'), 0)
    return picks


def _to_int(value, default):
    try:
        return max(0, int(value))
    except (TypeError, ValueError):
        return default


@require_POST
def save(request, pk):
    """Rewrite the preset from the workspace form. Returns the save-status fragment;
    HX-Trigger tells the preview pane to recompile."""
    preset = get_object_or_404(ResumePreset, pk=pk)
    post = request.POST
    error = ''

    name = post.get('name', '').strip()
    if name and name != preset.name:
        if ResumePreset.objects.filter(name=name).exclude(pk=pk).exists():
            error = f'A preset named "{name}" already exists.'
        else:
            preset.name = name

    with transaction.atomic():
        preset.include_gpa = 'include_gpa' in post
        preset.page_limit = max(1, _to_int(post.get('page_limit'), preset.page_limit))
        preset.save()
        _rewrite_joins(preset, _parse_picks(post))

    if not request.headers.get('HX-Request'):
        if error:
            messages.error(request, error)
        return redirect('presets:workspace', pk=pk)
    response = render(request, 'presets/_save_status.html', {'preset': preset, 'error': error})
    response['HX-Trigger'] = 'preset-saved'
    return response


def _rewrite_joins(preset, picks):
    """Replace the four join tables. Bullets are only kept under a component that is itself picked."""
    valid_components = set(Component.objects.filter(pk__in=picks['comp']).values_list('pk', flat=True))
    preset.preset_components.all().delete()  # cascades to PresetBullet
    preset_components = {
        cid: PresetComponent(preset=preset, component_id=cid, order=order)
        for cid, order in picks['comp'].items() if cid in valid_components
    }
    PresetComponent.objects.bulk_create(preset_components.values())

    bullet_parents = dict(Bullet.objects.filter(pk__in=picks['bullet']).values_list('pk', 'component_id'))
    PresetBullet.objects.bulk_create([
        PresetBullet(preset_component=preset_components[bullet_parents[bid]], bullet_id=bid, order=order)
        for bid, order in picks['bullet'].items()
        if bullet_parents.get(bid) in preset_components
    ])

    valid_skills = set(Skill.objects.filter(pk__in=picks['skill']).values_list('pk', flat=True))
    preset.preset_skills.all().delete()
    PresetSkill.objects.bulk_create([
        PresetSkill(preset=preset, skill_id=sid, order=order)
        for sid, order in picks['skill'].items() if sid in valid_skills
    ])

    valid_courses = set(Coursework.objects.filter(pk__in=picks['course']).values_list('pk', flat=True))
    preset.preset_coursework.all().delete()
    PresetCoursework.objects.bulk_create([
        PresetCoursework(preset=preset, coursework_id=cid, order=order)
        for cid, order in picks['course'].items() if cid in valid_courses
    ])


@require_POST
def clone(request, pk):
    """Duplicate the preset and its join rows (not the bank rows, which stay shared)."""
    source = get_object_or_404(ResumePreset, pk=pk)
    base = f'{source.name} (copy)'
    name, n = base, 2
    while ResumePreset.objects.filter(name=name).exists():
        name, n = f'{base} {n}', n + 1

    with transaction.atomic():
        preset = ResumePreset.objects.create(
            name=name, template=source.template, include_gpa=source.include_gpa,
            page_limit=source.page_limit,
        )
        for pc in source.preset_components.prefetch_related('preset_bullets'):
            new_pc = PresetComponent.objects.create(preset=preset, component_id=pc.component_id, order=pc.order)
            PresetBullet.objects.bulk_create([
                PresetBullet(preset_component=new_pc, bullet_id=pb.bullet_id, order=pb.order)
                for pb in pc.preset_bullets.all()
            ])
        PresetSkill.objects.bulk_create([
            PresetSkill(preset=preset, skill_id=ps.skill_id, order=ps.order)
            for ps in source.preset_skills.all()
        ])
        PresetCoursework.objects.bulk_create([
            PresetCoursework(preset=preset, coursework_id=pc.coursework_id, order=pc.order)
            for pc in source.preset_coursework.all()
        ])
    messages.success(request, f'Cloned "{source.name}" as "{preset.name}".')
    return redirect('presets:workspace', pk=preset.pk)


def delete(request, pk):
    preset = get_object_or_404(ResumePreset, pk=pk)
    if request.method == 'POST':
        delete_preview(preset.pk)
        preset.delete()  # Resume rows survive via SET_NULL + preset_name
        messages.success(request, f'Deleted "{preset.name}". Its compile history is kept.')
        return redirect('presets:list')
    return render(request, 'presets/confirm_delete.html', {'preset': preset})
