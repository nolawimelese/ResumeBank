import shutil
import tempfile
from datetime import date
from unittest import skipUnless

from django.test import TestCase, override_settings

from bank.models import Bullet, Component, Coursework, Education, Link, Profile, Skill
from presets.models import (
    PresetBullet, PresetComponent, PresetCoursework, PresetLink, PresetSkill, ResumePreset,
)

from . import services
from .models import Resume

HAS_PDFLATEX = shutil.which('pdflatex') is not None


class EscapeTests(TestCase):
    def test_latex_escape_covers_every_special(self):
        self.assertEqual(
            services.latex_escape(r'a & b % c $ d # e _ f { g } h ~ i ^ j \ k < l > m | n'),
            r'a \& b \% c \$ d \# e \_ f \{ g \} h \textasciitilde{} i \textasciicircum{} j \textbackslash{} k'
            r' \textless{} l \textgreater{} m \textbar{} n',
        )

    def test_bullet_markup_escapes_then_bolds(self):
        self.assertEqual(services.bullet_markup('Cut **p95** by 40% & more'), r'Cut \textbf{p95} by 40\% \& more')
        # A lone asterisk is left alone; only paired ** is markup.
        self.assertEqual(services.bullet_markup('a * b'), 'a * b')

    def test_dates(self):
        self.assertEqual(services.fmt_date(date(2025, 6, 1)), 'Jun. 2025')
        self.assertEqual(services.fmt_date(date(2025, 5, 1)), 'May 2025')
        self.assertEqual(services.date_range(date(2024, 9, 1), None), 'Sep. 2024 -- Present')
        self.assertEqual(services.date_range(None, None), '')


class RenderTests(TestCase):
    def setUp(self):
        profile = Profile.load()
        profile.name = 'Jane & Co'
        profile.save()
        self.preset = ResumePreset.objects.create(name='T')
        comp = Component.objects.create(
            category=Component.Category.EXPERIENCE, title='Dev_Ops', organization='ACME',
            start_date=date(2024, 1, 1),
        )
        bullet = Bullet.objects.create(component=comp, text='Did **things** 100%')
        pc = PresetComponent.objects.create(preset=self.preset, component=comp)
        PresetBullet.objects.create(preset_component=pc, bullet=bullet)
        PresetSkill.objects.create(preset=self.preset, skill=Skill.objects.create(name='C++'))
        self.edu = Education.objects.create(school='State U', degree='B.S. CS', start_date=date(2023, 8, 1))
        self.algo = Coursework.objects.create(education=self.edu, name='Algorithms', order=0)
        self.db = Coursework.objects.create(education=self.edu, name='Databases & SQL', order=1)

    def test_coursework_line_lists_only_picked_courses_in_preset_order(self):
        PresetCoursework.objects.create(preset=self.preset, coursework=self.db, order=0)
        PresetCoursework.objects.create(preset=self.preset, coursework=self.algo, order=1)
        tex = services.render_tex(self.preset)
        self.assertIn(r'\textbf{Relevant Coursework}: Databases \& SQL, Algorithms}', tex)

    def test_no_picked_courses_omits_the_coursework_line(self):
        tex = services.render_tex(self.preset)
        self.assertIn('State U', tex)  # education itself always renders
        self.assertNotIn('Relevant Coursework', tex)

    def test_render_escapes_user_strings(self):
        tex = services.render_tex(self.preset)
        self.assertIn(r'Jane \& Co', tex)
        self.assertIn(r'Dev\_Ops', tex)
        self.assertIn(r'\resumeItem{Did \textbf{things} 100\%}', tex)
        self.assertIn('Jan. 2024 -- Present', tex)
        self.assertIn(r'\textbf{Other}{: C++}', tex)
        self.assertNotIn(r'\section{Projects}', tex)  # empty sections are skipped

    def test_header_respects_toggles_and_link_picks(self):
        profile = Profile.load()
        profile.phone, profile.email, profile.location = '555-0100', 'jane@example.com', 'Atlanta, GA'
        profile.save()
        gh = Link.objects.create(profile=profile, link_type=Link.LinkType.GITHUB, url='https://github.com/jane', order=0)
        li = Link.objects.create(profile=profile, link_type=Link.LinkType.LINKEDIN, url='https://linkedin.com/in/jane', order=1)
        Link.objects.create(profile=profile, url='https://jane.dev', order=2)  # not picked
        PresetLink.objects.create(preset=self.preset, link=li, order=0)
        PresetLink.objects.create(preset=self.preset, link=gh, order=1)

        parts = services.resolve_preset(self.preset)['header_parts']
        self.assertEqual(parts[0], '555-0100')
        self.assertIn('jane@example.com', parts[1])
        # Links follow the preset's order, and unpicked links are left out.
        self.assertIn('linkedin.com/in/jane', parts[2])
        self.assertIn('github.com/jane', parts[3])
        self.assertEqual(parts[4], 'Atlanta, GA')
        self.assertEqual(len(parts), 5)

        self.preset.show_phone = self.preset.show_email = self.preset.show_location = False
        parts = services.resolve_preset(self.preset)['header_parts']
        self.assertEqual(len(parts), 2)
        self.assertIn('linkedin.com/in/jane', parts[0])

    def _add_honor(self):
        honor = Component.objects.create(
            category=Component.Category.HONOR, title='Deans List', start_date=date(2024, 5, 1),
        )
        PresetComponent.objects.create(preset=self.preset, component=honor)

    def test_honors_render_under_education_not_as_a_section(self):
        self._add_honor()
        tex = services.render_tex(self.preset)
        self.assertNotIn(r'\section{Honors}', tex)
        self.assertLess(tex.index('State U'), tex.index('Deans List'))
        self.assertLess(tex.index('Deans List'), tex.index(r'\section{Experience}'))

    def test_honors_render_without_any_education(self):
        self.edu.delete()
        self._add_honor()
        tex = services.render_tex(self.preset)
        self.assertIn(r'\section{Education}', tex)
        self.assertIn('Deans List', tex)

    @skipUnless(HAS_PDFLATEX, 'pdflatex not on PATH')
    def test_compile_to_history_records_resume(self):
        media = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, media, ignore_errors=True)
        with override_settings(MEDIA_ROOT=media):
            resume = services.compile_to_history(self.preset)
        self.assertEqual(resume.page_count, 1)
        self.assertFalse(resume.over_limit)
        self.assertTrue(resume.pdf_file.name.startswith(f'resumes/{resume.pk}/'))
        self.assertEqual(Resume.objects.count(), 1)

    @skipUnless(HAS_PDFLATEX, 'pdflatex not on PATH')
    def test_latex_failure_is_reported_not_raised(self):
        result = services.compile_tex(r'\documentclass{article}\begin{document}\undefinedmacro\end{document}')
        self.assertFalse(result.ok)
        self.assertTrue(result.error.startswith('!'))
        self.assertIsNone(result.pdf)
