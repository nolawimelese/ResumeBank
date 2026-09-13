from django.test import TestCase
from django.urls import reverse

from bank.models import Bullet, Component, Skill

from .models import PresetBullet, PresetComponent, PresetSkill, ResumePreset


class WorkspaceSaveTests(TestCase):
    def setUp(self):
        self.preset = ResumePreset.objects.create(name='Base')
        self.exp = Component.objects.create(category=Component.Category.EXPERIENCE, title='Intern')
        self.b1 = Bullet.objects.create(component=self.exp, text='one', order=0)
        self.b2 = Bullet.objects.create(component=self.exp, text='two', order=1)
        self.proj = Component.objects.create(category=Component.Category.PROJECT, title='Proj')
        self.orphan = Bullet.objects.create(component=self.proj, text='orphan', order=0)
        self.skill = Skill.objects.create(group=Skill.Group.LANGUAGES, name='Python')
        self.url = reverse('presets:save', args=[self.preset.pk])

    def post_save(self, data, htmx=True):
        headers = {'HX-Request': 'true'} if htmx else {}
        return self.client.post(self.url, data, headers=headers)

    def test_rewrites_join_tables_from_post(self):
        response = self.post_save({
            'name': 'Base', 'page_limit': '2', 'include_gpa': 'on',
            f'comp_{self.exp.pk}': 'on', f'comp_{self.exp.pk}_order': '3',
            f'bullet_{self.b2.pk}': 'on', f'bullet_{self.b2.pk}_order': '0',
            f'bullet_{self.b1.pk}': 'on', f'bullet_{self.b1.pk}_order': '1',
            f'skill_{self.skill.pk}': 'on', f'skill_{self.skill.pk}_order': '4',
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['HX-Trigger'], 'preset-saved')

        self.preset.refresh_from_db()
        self.assertEqual(self.preset.page_limit, 2)
        self.assertTrue(self.preset.include_gpa)
        self.assertFalse(self.preset.include_coursework)

        pc = PresetComponent.objects.get(preset=self.preset)
        self.assertEqual((pc.component_id, pc.order), (self.exp.pk, 3))
        self.assertEqual(
            list(pc.preset_bullets.values_list('bullet_id', 'order')),
            [(self.b2.pk, 0), (self.b1.pk, 1)],
        )
        self.assertEqual(list(self.preset.preset_skills.values_list('skill_id', 'order')), [(self.skill.pk, 4)])

    def test_bullet_under_unchecked_component_is_dropped(self):
        self.post_save({
            'name': 'Base',
            f'comp_{self.exp.pk}': 'on',
            f'bullet_{self.orphan.pk}': 'on',
        })
        self.assertFalse(PresetBullet.objects.filter(bullet=self.orphan).exists())

    def test_unchecking_everything_empties_the_preset(self):
        PresetComponent.objects.create(preset=self.preset, component=self.exp)
        PresetSkill.objects.create(preset=self.preset, skill=self.skill)
        self.post_save({'name': 'Base'})
        self.assertEqual(self.preset.preset_components.count(), 0)
        self.assertEqual(self.preset.preset_skills.count(), 0)

    def test_unknown_ids_and_bad_orders_are_ignored(self):
        self.post_save({
            'name': 'Base', 'page_limit': 'abc',
            'comp_999999': 'on', f'comp_{self.exp.pk}': 'on', f'comp_{self.exp.pk}_order': 'x',
        })
        self.preset.refresh_from_db()
        self.assertEqual(self.preset.page_limit, 1)
        self.assertEqual(list(self.preset.preset_components.values_list('component_id', 'order')), [(self.exp.pk, 0)])

    def test_name_clash_keeps_old_name_but_still_saves_picks(self):
        ResumePreset.objects.create(name='Taken')
        response = self.post_save({'name': 'Taken', f'comp_{self.exp.pk}': 'on'})
        self.assertContains(response, 'already exists')
        self.preset.refresh_from_db()
        self.assertEqual(self.preset.name, 'Base')
        self.assertEqual(self.preset.preset_components.count(), 1)

    def test_plain_post_redirects_to_workspace(self):
        response = self.post_save({'name': 'Renamed'}, htmx=False)
        self.assertRedirects(response, reverse('presets:workspace', args=[self.preset.pk]))
        self.preset.refresh_from_db()
        self.assertEqual(self.preset.name, 'Renamed')


class CloneTests(TestCase):
    def test_clone_copies_join_rows_not_bank_rows(self):
        preset = ResumePreset.objects.create(name='Base', include_gpa=False, page_limit=2)
        comp = Component.objects.create(category=Component.Category.EXPERIENCE, title='Intern')
        bullet = Bullet.objects.create(component=comp, text='x')
        skill = Skill.objects.create(name='Python')
        pc = PresetComponent.objects.create(preset=preset, component=comp, order=1)
        PresetBullet.objects.create(preset_component=pc, bullet=bullet, order=2)
        PresetSkill.objects.create(preset=preset, skill=skill, order=3)

        response = self.client.post(reverse('presets:clone', args=[preset.pk]))
        clone = ResumePreset.objects.get(name='Base (copy)')
        self.assertRedirects(response, reverse('presets:workspace', args=[clone.pk]))
        self.assertEqual((clone.include_gpa, clone.page_limit), (False, 2))

        new_pc = clone.preset_components.get()
        self.assertEqual((new_pc.component_id, new_pc.order), (comp.pk, 1))
        self.assertEqual(list(new_pc.preset_bullets.values_list('bullet_id', 'order')), [(bullet.pk, 2)])
        self.assertEqual(list(clone.preset_skills.values_list('skill_id', 'order')), [(skill.pk, 3)])
        # Bank rows are shared, not duplicated.
        self.assertEqual(Component.objects.count(), 1)
        self.assertEqual(Bullet.objects.count(), 1)

        # A second clone gets a distinct name.
        self.client.post(reverse('presets:clone', args=[preset.pk]))
        self.assertTrue(ResumePreset.objects.filter(name='Base (copy) 2').exists())
