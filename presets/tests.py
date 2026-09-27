from django.test import TestCase
from django.urls import reverse

from bank.models import Bullet, Component, Coursework, Education, Link, Profile, Skill

from .models import (
    PresetBullet, PresetComponent, PresetCoursework, PresetLink, PresetSkill, ResumePreset,
)


class WorkspaceSaveTests(TestCase):
    def setUp(self):
        self.preset = ResumePreset.objects.create(name='Base')
        self.exp = Component.objects.create(category=Component.Category.EXPERIENCE, title='Intern')
        self.b1 = Bullet.objects.create(component=self.exp, text='one', order=0)
        self.b2 = Bullet.objects.create(component=self.exp, text='two', order=1)
        self.proj = Component.objects.create(category=Component.Category.PROJECT, title='Proj')
        self.orphan = Bullet.objects.create(component=self.proj, text='orphan', order=0)
        self.skill = Skill.objects.create(group=Skill.Group.LANGUAGES, name='Python')
        edu = Education.objects.create(school='U', degree='BS', start_date='2023-01-01')
        self.c1 = Coursework.objects.create(education=edu, name='Algorithms', order=0)
        self.c2 = Coursework.objects.create(education=edu, name='Databases', order=1)
        self.link = Link.objects.create(profile=Profile.load(), url='https://github.com/jane')
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
            f'course_{self.c2.pk}': 'on', f'course_{self.c2.pk}_order': '5',
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['HX-Trigger'], 'preset-saved')

        self.preset.refresh_from_db()
        self.assertEqual(self.preset.page_limit, 2)
        self.assertTrue(self.preset.include_gpa)

        pc = PresetComponent.objects.get(preset=self.preset)
        self.assertEqual((pc.component_id, pc.order), (self.exp.pk, 3))
        self.assertEqual(
            list(pc.preset_bullets.values_list('bullet_id', 'order')),
            [(self.b2.pk, 0), (self.b1.pk, 1)],
        )
        self.assertEqual(list(self.preset.preset_skills.values_list('skill_id', 'order')), [(self.skill.pk, 4)])
        self.assertEqual(
            list(self.preset.preset_coursework.values_list('coursework_id', 'order')), [(self.c2.pk, 5)],
        )

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
        PresetCoursework.objects.create(preset=self.preset, coursework=self.c1)
        self.post_save({'name': 'Base'})
        self.assertEqual(self.preset.preset_components.count(), 0)
        self.assertEqual(self.preset.preset_skills.count(), 0)
        self.assertEqual(self.preset.preset_coursework.count(), 0)

    def test_saves_header_toggles_and_link_picks(self):
        self.post_save({'name': 'Base', 'show_email': 'on', f'link_{self.link.pk}': 'on', f'link_{self.link.pk}_order': '2'})
        self.preset.refresh_from_db()
        self.assertEqual((self.preset.show_phone, self.preset.show_email, self.preset.show_location), (False, True, False))
        self.assertEqual(list(self.preset.preset_links.values_list('link_id', 'order')), [(self.link.pk, 2)])

        self.post_save({'name': 'Base'})
        self.assertFalse(self.preset.preset_links.exists())

    def test_unknown_ids_and_bad_orders_are_ignored(self):
        self.post_save({
            'name': 'Base', 'page_limit': 'abc',
            'comp_999999': 'on', f'comp_{self.exp.pk}': 'on', f'comp_{self.exp.pk}_order': 'x',
            'course_999999': 'on', f'course_{self.c1.pk}': 'on',
        })
        self.preset.refresh_from_db()
        self.assertEqual(self.preset.page_limit, 1)
        self.assertEqual(list(self.preset.preset_components.values_list('component_id', 'order')), [(self.exp.pk, 0)])
        self.assertEqual(list(self.preset.preset_coursework.values_list('coursework_id', flat=True)), [self.c1.pk])

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
        preset = ResumePreset.objects.create(name='Base', include_gpa=False, page_limit=2, show_phone=False)
        comp = Component.objects.create(category=Component.Category.EXPERIENCE, title='Intern')
        bullet = Bullet.objects.create(component=comp, text='x')
        skill = Skill.objects.create(name='Python')
        edu = Education.objects.create(school='U', degree='BS', start_date='2023-01-01')
        course = Coursework.objects.create(education=edu, name='Algorithms')
        pc = PresetComponent.objects.create(preset=preset, component=comp, order=1)
        PresetBullet.objects.create(preset_component=pc, bullet=bullet, order=2)
        PresetSkill.objects.create(preset=preset, skill=skill, order=3)
        PresetCoursework.objects.create(preset=preset, coursework=course, order=4)
        link = Link.objects.create(profile=Profile.load(), url='https://github.com/jane')
        PresetLink.objects.create(preset=preset, link=link, order=5)

        response = self.client.post(reverse('presets:clone', args=[preset.pk]))
        clone = ResumePreset.objects.get(name='Base (copy)')
        self.assertRedirects(response, reverse('presets:workspace', args=[clone.pk]))
        self.assertEqual((clone.include_gpa, clone.page_limit), (False, 2))
        self.assertEqual((clone.show_phone, clone.show_email, clone.show_location), (False, True, True))

        new_pc = clone.preset_components.get()
        self.assertEqual((new_pc.component_id, new_pc.order), (comp.pk, 1))
        self.assertEqual(list(new_pc.preset_bullets.values_list('bullet_id', 'order')), [(bullet.pk, 2)])
        self.assertEqual(list(clone.preset_skills.values_list('skill_id', 'order')), [(skill.pk, 3)])
        self.assertEqual(list(clone.preset_coursework.values_list('coursework_id', 'order')), [(course.pk, 4)])
        self.assertEqual(list(clone.preset_links.values_list('link_id', 'order')), [(link.pk, 5)])
        # Bank rows are shared, not duplicated.
        self.assertEqual(Component.objects.count(), 1)
        self.assertEqual(Bullet.objects.count(), 1)
        self.assertEqual(Coursework.objects.count(), 1)

        # A second clone gets a distinct name.
        self.client.post(reverse('presets:clone', args=[preset.pk]))
        self.assertTrue(ResumePreset.objects.filter(name='Base (copy) 2').exists())


class WorkspaceTests(TestCase):
    def test_workspace_lists_honors(self):
        preset = ResumePreset.objects.create(name='Base')
        Component.objects.create(category=Component.Category.HONOR, title='Deans List')
        response = self.client.get(reverse('presets:workspace', args=[preset.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Deans List')

    def test_workspace_renders_header_fieldset(self):
        preset = ResumePreset.objects.create(name='Base', show_location=False)
        link = Link.objects.create(profile=Profile.load(), url='https://github.com/jane')
        response = self.client.get(reverse('presets:workspace', args=[preset.pk]))
        self.assertContains(response, '<legend>Header</legend>', html=True)
        self.assertContains(response, 'name="show_phone" checked')
        self.assertContains(response, 'name="show_location" >')
        # New links are opt-in: unchecked until the preset picks them.
        self.assertContains(response, f'name="link_{link.pk}" >')

    def test_picked_rows_come_first_in_preset_order(self):
        preset = ResumePreset.objects.create(name='Base')
        a, b, c = (
            Component.objects.create(category=Component.Category.PROJECT, title=t) for t in ('A', 'B', 'C')
        )
        b1 = Bullet.objects.create(component=c, text='one', order=0)
        b2 = Bullet.objects.create(component=c, text='two', order=1)
        b3 = Bullet.objects.create(component=c, text='three', order=2)
        s1, s2, s3 = (Skill.objects.create(name=n, order=i) for i, n in enumerate(('Go', 'Rust', 'C')))
        pc = PresetComponent.objects.create(preset=preset, component=c, order=0)
        PresetComponent.objects.create(preset=preset, component=b, order=1)
        PresetBullet.objects.create(preset_component=pc, bullet=b3, order=0)
        PresetBullet.objects.create(preset_component=pc, bullet=b1, order=1)
        PresetSkill.objects.create(preset=preset, skill=s3, order=0)

        response = self.client.get(reverse('presets:workspace', args=[preset.pk]))
        (projects,) = response.context['sections']
        self.assertEqual([e['component'] for e in projects['entries']], [c, b, a])
        self.assertEqual([x['bullet'] for x in projects['entries'][0]['bullets']], [b3, b1, b2])
        (languages,) = response.context['skill_groups']
        self.assertEqual([x['skill'] for x in languages['entries']], [s3, s1, s2])
        # Positions render from the display order, as hidden inputs rather than number fields.
        self.assertContains(response, f'type="hidden" class="pos" name="comp_{a.pk}_order" value="2"')
        self.assertContains(response, f'type="hidden" class="pos" name="bullet_{b2.pk}_order" value="2"')
        self.assertContains(response, 'type="number"', count=1)  # only page_limit
