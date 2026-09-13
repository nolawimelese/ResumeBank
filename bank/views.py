"""
Component Manager: standalone CRUD for the source data. Presets hold
references, so every edit here shows up in every preset on its next compile.
Delete pages warn using the join-table reverse accessors (a query, not a scan).
"""
from django.contrib import messages
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from compiler.services import SECTION_TITLES

from .forms import (
    BulletFormSet, ComponentForm, CourseworkFormSet, EducationForm, LinkFormSet, ProfileForm, SkillFormSet,
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
        'sections': [(cat, SECTION_TITLES[cat], rows) for cat, rows in by_category.items()],
        'skill_groups': [(g.label, rows) for g, rows in by_group.items() if rows],
    })


def _edit(request, form_cls, formset_cls, instance, title, inline_title, delete_url=None, usage_accessor=None):
    """Shared save loop for a ModelForm plus its one-level inline formset.

    usage_accessor names the reverse join accessor on the inline rows (e.g.
    'presetbullet_set') so the template can warn before a row is deleted."""
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
    })


# ---- Profile (singleton) ----

def profile(request):
    return _edit(request, ProfileForm, LinkFormSet, Profile.load(), 'Profile', 'Links')


# ---- Education ----

def education_new(request):
    return _edit(request, EducationForm, CourseworkFormSet, Education(), 'New education', 'Coursework')


def education_edit(request, pk):
    edu = get_object_or_404(Education, pk=pk)
    return _edit(request, EducationForm, CourseworkFormSet, edu, str(edu), 'Coursework',
                 delete_url=reverse('bank:education_delete', args=[pk]))


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
    return _edit(request, ComponentForm, BulletFormSet, initial, 'New component', 'Bullets')


def component_edit(request, pk):
    component = get_object_or_404(Component, pk=pk)
    return _edit(request, ComponentForm, BulletFormSet, component, str(component), 'Bullets',
                 delete_url=reverse('bank:component_delete', args=[pk]), usage_accessor='presetbullet_set')


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


# ---- Skills: one page, one formset ----

def skills(request):
    if request.method == 'POST':
        formset = SkillFormSet(request.POST)
        if formset.is_valid():
            formset.save()
            messages.success(request, 'Saved skills.')
            return redirect('bank:skills')
    else:
        formset = SkillFormSet()
    return render(request, 'bank/skills.html', {'formset': formset})
