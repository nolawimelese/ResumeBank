import datetime

from django.test import TestCase
from django.urls import reverse

from presets.models import PresetSkill, ResumePreset

from .models import Component, Education, Skill


class IndexTests(TestCase):
    def test_lists_every_category_including_honors(self):
        # Honors have no PDF section of their own, but the Component Manager still lists them.
        Component.objects.create(category=Component.Category.HONOR, title='Deans List')
        response = self.client.get(reverse('bank:index'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Honors')
        self.assertContains(response, 'Deans List')


class ComponentDateTests(TestCase):
    def test_single_date_categories_drop_end_date(self):
        for category in (Component.Category.HONOR, Component.Category.CERTIFICATION):
            component = Component.objects.create(
                category=category, title='X',
                start_date=datetime.date(2024, 5, 1), end_date=datetime.date(2024, 6, 1),
            )
            component.refresh_from_db()
            self.assertIsNone(component.end_date)

    def test_project_keeps_optional_end_date(self):
        component = Component.objects.create(
            category=Component.Category.PROJECT, title='P',
            start_date=datetime.date(2024, 5, 1), end_date=datetime.date(2024, 6, 1),
        )
        component.refresh_from_db()
        self.assertEqual(component.end_date, datetime.date(2024, 6, 1))


class ComponentTechStackTests(TestCase):
    def test_only_projects_keep_tech_stack(self):
        for category, _ in Component.Category.choices:
            component = Component.objects.create(category=category, title='X', tech_stack='Python')
            component.refresh_from_db()
            expected = 'Python' if category == Component.Category.PROJECT else ''
            self.assertEqual(component.tech_stack, expected, category)


class ComponentInProgressTests(TestCase):
    def test_only_certifications_keep_in_progress(self):
        for category, _ in Component.Category.choices:
            component = Component.objects.create(
                category=category, title='X', start_date=datetime.date(2026, 12, 1), in_progress=True,
            )
            component.refresh_from_db()
            self.assertEqual(component.in_progress, category == Component.Category.CERTIFICATION, category)
            self.assertEqual(component.start_date, datetime.date(2026, 12, 1))  # date is kept either way


class EditorPreviewTests(TestCase):
    """The live preview pane is on the component and education editors only."""

    def assertPreview(self, url, present):
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        check = self.assertContains if present else self.assertNotContains
        check(response, 'id="component-preview"')
        check(response, 'js/component_preview.js')

    def test_component_editors_have_preview(self):
        component = Component.objects.create(category=Component.Category.EXPERIENCE, title='Intern')
        self.assertPreview(reverse('bank:component_new'), True)
        self.assertPreview(reverse('bank:component_edit', args=[component.pk]), True)

    def test_education_editors_have_preview(self):
        education = Education.objects.create(school='State U', degree='BS', start_date=datetime.date(2022, 8, 1))
        self.assertPreview(reverse('bank:education_new'), True)
        self.assertPreview(reverse('bank:education_edit', args=[education.pk]), True)

    def test_profile_editor_has_no_preview(self):
        self.assertPreview(reverse('bank:profile'), False)


class SkillBoardTests(TestCase):
    """The skills board: every action is its own POST and returns the re-rendered board."""

    def names(self, group):
        return list(Skill.objects.filter(group=group).order_by('order', 'id').values_list('name', flat=True))

    def test_page_lists_groups_in_pdf_order_including_empty_ones(self):
        response = self.client.get(reverse('bank:skills'))
        self.assertEqual(response.status_code, 200)
        labels = [g['label'] for g in response.context['groups']]
        self.assertEqual(labels, ['Languages', 'Frameworks', 'Tools', 'Other'])

    def test_add_splits_skips_blanks_and_duplicates_and_appends(self):
        Skill.objects.create(group=Skill.Group.LANGUAGES, name='Python', order=5)
        response = self.client.post(reverse('bank:skill_add'), {
            'group': 'languages', 'names': 'Go, python,\nRust,, go\r\n',
        })
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'bank/_skill_board.html')
        self.assertEqual(self.names('languages'), ['Python', 'Go', 'Rust'])
        self.assertEqual(Skill.objects.get(name='Go').order, 6)
        self.assertContains(response, 'Skipped duplicates: python, go')

    def test_add_rejects_unknown_group(self):
        self.client.post(reverse('bank:skill_add'), {'group': 'nope', 'names': 'Go'})
        self.assertFalse(Skill.objects.exists())

    def test_rename(self):
        go = Skill.objects.create(group=Skill.Group.LANGUAGES, name='Go')
        Skill.objects.create(group=Skill.Group.LANGUAGES, name='Rust')
        self.client.post(reverse('bank:skill_rename', args=[go.pk]), {'name': ' Golang '})
        go.refresh_from_db()
        self.assertEqual(go.name, 'Golang')
        for bad in ('', 'rust'):
            response = self.client.post(reverse('bank:skill_rename', args=[go.pk]), {'name': bad})
            self.assertContains(response, 'class="flash error"')
            go.refresh_from_db()
            self.assertEqual(go.name, 'Golang')

    def test_delete_cascades_to_presets(self):
        go = Skill.objects.create(group=Skill.Group.LANGUAGES, name='Go')
        PresetSkill.objects.create(preset=ResumePreset.objects.create(name='P'), skill=go)
        response = self.client.get(reverse('bank:skills'))
        self.assertContains(response, 'hx-confirm')  # used skills ask before deleting
        self.client.post(reverse('bank:skill_delete', args=[go.pk]))
        self.assertFalse(Skill.objects.exists())
        self.assertFalse(PresetSkill.objects.exists())

    def test_move_regroups_and_renumbers_target(self):
        go = Skill.objects.create(group=Skill.Group.LANGUAGES, name='Go', order=0)
        django = Skill.objects.create(group=Skill.Group.FRAMEWORKS, name='Django', order=0)
        react = Skill.objects.create(group=Skill.Group.FRAMEWORKS, name='React', order=1)
        self.client.post(reverse('bank:skill_move'), {
            'pk': go.pk, 'group': 'frameworks', 'ids': [react.pk, go.pk, django.pk],
        })
        self.assertEqual(self.names('frameworks'), ['React', 'Go', 'Django'])
        self.assertEqual(self.names('languages'), [])

    def test_move_refuses_duplicate_name_in_target_group(self):
        go = Skill.objects.create(group=Skill.Group.LANGUAGES, name='Go')
        Skill.objects.create(group=Skill.Group.OTHER, name='go')
        response = self.client.post(reverse('bank:skill_move'), {'pk': go.pk, 'group': 'other', 'ids': [go.pk]})
        self.assertContains(response, 'class="flash error"')
        go.refresh_from_db()
        self.assertEqual(go.group, 'languages')

    def test_endpoints_are_post_only(self):
        self.assertEqual(self.client.get(reverse('bank:skill_add')).status_code, 405)
