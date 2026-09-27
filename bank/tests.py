import datetime

from django.test import TestCase
from django.urls import reverse

from .models import Component, Education


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


class ComponentPreviewTests(TestCase):
    """The live preview pane is on the component editor only."""

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

    def test_other_editors_have_no_preview(self):
        education = Education.objects.create(school='State U', degree='BS', start_date=datetime.date(2022, 8, 1))
        self.assertPreview(reverse('bank:education_edit', args=[education.pk]), False)
        self.assertPreview(reverse('bank:profile'), False)
