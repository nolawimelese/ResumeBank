"""
ModelForms plus one-level inline formsets for the Component Manager. These
are single-level (Component -> Bullet, Education -> Coursework, Profile -> Link);
the nested case the docs warn about is the preset builder, which does not use
formsets at all (see presets.views.save).
"""
from django import forms
from django.forms import inlineformset_factory

from .models import Bullet, Component, Coursework, Education, Link, Profile


class DateInput(forms.DateInput):
    input_type = 'date'


class ProfileForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = ['name', 'email', 'phone', 'location']


LinkFormSet = inlineformset_factory(
    Profile, Link, fields=['link_type', 'url', 'order'], extra=1, can_delete=True,
)


class EducationForm(forms.ModelForm):
    class Meta:
        model = Education
        fields = ['school', 'degree_title', 'degree', 'location', 'start_date', 'end_date', 'gpa']
        widgets = {'start_date': DateInput, 'end_date': DateInput}


CourseworkFormSet = inlineformset_factory(
    Education, Coursework, fields=['name', 'order'], extra=2, can_delete=True,
)


class ComponentForm(forms.ModelForm):
    class Meta:
        model = Component
        fields = ['category', 'title', 'organization', 'location', 'start_date', 'in_progress', 'end_date', 'tech_stack']
        widgets = {
            'start_date': DateInput,
            'end_date': DateInput,
            # Room for a full one-line "Name | Tech" heading's worth of tech.
            'tech_stack': forms.TextInput(attrs={'size': 70, 'style': 'max-width: 100%'}),
        }
        help_texts = {
            'in_progress': 'Shows "In Progress" instead of the date.'
        }


BulletFormSet = inlineformset_factory(
    Component, Bullet, fields=['text', 'order'], extra=2, can_delete=True,
    widgets={'text': forms.Textarea(attrs={'rows': 2})},
)
