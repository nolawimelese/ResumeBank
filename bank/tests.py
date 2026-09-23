from django.test import TestCase
from django.urls import reverse

from .models import Component


class IndexTests(TestCase):
    def test_lists_every_category_including_honors(self):
        # Honors have no PDF section of their own, but the Component Manager still lists them.
        Component.objects.create(category=Component.Category.HONOR, title='Deans List')
        response = self.client.get(reverse('bank:index'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Honors')
        self.assertContains(response, 'Deans List')
