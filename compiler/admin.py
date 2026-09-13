from django.contrib import admin

from .models import Resume


@admin.register(Resume)
class ResumeAdmin(admin.ModelAdmin):
    """Compile history is non-updating, so everything is read-only here."""

    list_display = ('preset_name', 'generated_at', 'page_count', 'over_limit')
    list_filter = ('over_limit', 'preset')
    readonly_fields = ('preset', 'preset_name', 'generated_at', 'page_count', 'over_limit', 'pdf_file', 'tex_file')

    def has_add_permission(self, request):
        return False
