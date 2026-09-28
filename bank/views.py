"""
Component Manager: standalone CRUD for the source data. Presets hold
references, so every edit here shows up in every preset on its next compile.
Delete pages warn using the join-table reverse accessors (a query, not a scan).
"""
import re

from django.contrib import messages
from django.db import transaction
from django.db.models import Count, Max
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from compiler.services import CATEGORY_TITLES

from .forms import (
    BulletFormSet, ComponentForm, CourseworkFormSet, EducationForm, LinkFormSet, ProfileForm,
)
from .models import Component, Education, Profile, Skill


def index(request):
    components = Component.objects.prefetch_related('bullets')
    by_category = {c: [] for c in Component.Category}
    for component in components:
        by_category[component.category].append(component)
    skills = Skill.objects.all()
    by_group = {g: [] for g in Skill.Group}
    for skill in skills:
        by_group[skill.group].append(skill)
    return render(request, 'bank/index.html', {
        'profile': Profile.load(),
        'educations': Education.objects.prefetch_related('coursework'),
        'sections': [(cat, CATEGORY_TITLES[cat], rows) for cat, rows in by_category.items()],
        'skill_groups': [(g.label, rows) for g, rows in by_group.items() if rows],
    })


def _edit(request, form_cls, formset_cls, instance, title, inline_title, delete_url=None, usage_accessor=None,
          preview=False):
    """Shared save loop for a ModelForm plus its one-level inline formset.

    usage_accessor names the reverse join accessor on the inline rows (e.g.
    'presetbullet_set') so the template can warn before a row is deleted.
    preview adds the live resume-entry pane (static/js/component_preview.js);
    the component and education editors use it."""
    if request.method == 'POST':
        form = form_cls(request.POST, instance=instance)
        formset = formset_cls(request.POST, instance=instance)
        if form.is_valid() and formset.is_valid():
            with transaction.atomic():
                obj = form.save()
                formset.instance = obj
                formset.save()
            messages.success(request, f'Saved {obj}.')
            return redirect('bank:index')
    else:
        form = form_cls(instance=instance)
        formset = formset_cls(instance=instance)
    for f in formset:
        f.uses = getattr(f.instance, usage_accessor).count() if usage_accessor and f.instance.pk else 0
    return render(request, 'bank/edit.html', {
        'form': form, 'formset': formset, 'title': title, 'inline_title': inline_title, 'delete_url': delete_url,
        'preview': preview,
    })


# ---- Profile (singleton) ----

def profile(request):
    return _edit(request, ProfileForm, LinkFormSet, Profile.load(), 'Profile', 'Links')


# ---- Education ----

def education_new(request):
    return _edit(request, EducationForm, CourseworkFormSet, Education(), 'New education', 'Coursework', preview=True)


def education_edit(request, pk):
    edu = get_object_or_404(Education, pk=pk)
    return _edit(request, EducationForm, CourseworkFormSet, edu, str(edu), 'Coursework',
                 delete_url=reverse('bank:education_delete', args=[pk]), preview=True)


def education_delete(request, pk):
    edu = get_object_or_404(Education, pk=pk)
    if request.method == 'POST':
        edu.delete()
        messages.success(request, f'Deleted {edu}.')
        return redirect('bank:index')
    return render(request, 'bank/confirm_delete.html', {'object': edu, 'uses': 0})


# ---- Components ----

def component_new(request):
    initial = Component(category=request.GET.get('category', Component.Category.EXPERIENCE))
    return _edit(request, ComponentForm, BulletFormSet, initial, 'New component', 'Bullets', preview=True)


def component_edit(request, pk):
    component = get_object_or_404(Component, pk=pk)
    return _edit(request, ComponentForm, BulletFormSet, component, str(component), 'Bullets',
                 delete_url=reverse('bank:component_delete', args=[pk]), usage_accessor='presetbullet_set', preview=True)


def component_delete(request, pk):
    component = get_object_or_404(Component, pk=pk)
    if request.method == 'POST':
        component.delete()
        messages.success(request, f'Deleted {component}.')
        return redirect('bank:index')
    return render(request, 'bank/confirm_delete.html', {
        'object': component,
        'uses': component.presetcomponent_set.count(),
    })


# ---- Skills: a board of row lists, one small POST per action ----
# Every endpoint re-renders the whole board fragment (it is tiny, and a move touches two groups).

def _board_context(note='', error=''):
    """Groups in PDF (enum) order, empty ones included so they can be added to."""
    skills = Skill.objects.annotate(uses=Count('presetskill')).order_by('order', 'id')
    by_group = {g: [] for g in Skill.Group}
    for skill in skills:
        by_group[skill.group].append(skill)
    return {
        'groups': [{'value': g.value, 'label': g.label, 'skills': rows} for g, rows in by_group.items()],
        'note': note,
        'error': error,
    }


def _render_board(request, note='', error=''):
    return render(request, 'bank/_skill_board.html', _board_context(note, error))


def _name_taken(group, name, exclude_pk=None):
    return Skill.objects.filter(group=group, name__iexact=name).exclude(pk=exclude_pk).exists()


def skills(request):
    return render(request, 'bank/skills.html', _board_context())


@require_POST
def skill_add(request):
    group = request.POST.get('group')
    if group not in Skill.Group.values:
        return _render_board(request, error='Unknown group.')
    names = [n.strip() for n in re.split(r'[,\n]', request.POST.get('names', ''))]
    added, skipped = [], []
    with transaction.atomic():
        order = Skill.objects.filter(group=group).aggregate(m=Max('order'))['m']
        order = -1 if order is None else order
        for name in names:
            if not name:
                continue
            if _name_taken(group, name) or name.lower() in (a.lower() for a in added):
                skipped.append(name)
                continue
            order += 1
            Skill.objects.create(group=group, name=name, order=order)
            added.append(name)
    return _render_board(request, note=f'Skipped duplicates: {", ".join(skipped)}' if skipped else '')


@require_POST
def skill_rename(request, pk):
    skill = get_object_or_404(Skill, pk=pk)
    name = request.POST.get('name', '').strip()
    if not name:
        return _render_board(request, error='A skill needs a name.')
    if _name_taken(skill.group, name, exclude_pk=skill.pk):
        return _render_board(request, error=f'"{name}" is already in {skill.get_group_display()}.')
    skill.name = name
    skill.save(update_fields=['name'])
    return _render_board(request)


@require_POST
def skill_delete(request, pk):
    get_object_or_404(Skill, pk=pk).delete()
    return _render_board(request)


@require_POST
def skill_move(request):
    """Put skill `pk` into `group`; `ids` is that group's full id list in its new order."""
    skill = get_object_or_404(Skill, pk=request.POST.get('pk'))
    group = request.POST.get('group')
    if group not in Skill.Group.values:
        return _render_board(request, error='Unknown group.')
    if group != skill.group and _name_taken(group, skill.name):
        return _render_board(request, error=f'"{skill.name}" is already in {Skill.Group(group).label}.')
    ids = [int(i) for i in request.POST.getlist('ids') if i.isdigit()]
    with transaction.atomic():
        skill.group = group
        skill.save(update_fields=['group'])
        rows = {s.pk: s for s in Skill.objects.filter(pk__in=ids, group=group)}
        for order, sid in enumerate(ids):
            if sid in rows:
                rows[sid].order = order
        Skill.objects.bulk_update(rows.values(), ['order'])
    return _render_board(request)
