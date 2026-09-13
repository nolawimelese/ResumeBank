from django.contrib import admin

from .models import Bullet, Component, Coursework, Education, Link, Profile, Skill


class LinkInline(admin.TabularInline):
    model = Link
    extra = 1


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    inlines = [LinkInline]

    def has_add_permission(self, request):
        # Singleton: only allow adding until the one row exists.
        return not Profile.objects.exists()


class CourseworkInline(admin.TabularInline):
    model = Coursework
    extra = 1


@admin.register(Education)
class EducationAdmin(admin.ModelAdmin):
    list_display = ('degree', 'school', 'start_date', 'end_date', 'gpa')
    inlines = [CourseworkInline]


class BulletInline(admin.TabularInline):
    model = Bullet
    extra = 1


@admin.register(Component)
class ComponentAdmin(admin.ModelAdmin):
    list_display = ('title', 'category', 'organization', 'start_date', 'end_date')
    list_filter = ('category',)
    search_fields = ('title', 'organization')
    inlines = [BulletInline]


@admin.register(Skill)
class SkillAdmin(admin.ModelAdmin):
    list_display = ('name', 'group', 'order')
    list_filter = ('group',)
    list_editable = ('order',)
