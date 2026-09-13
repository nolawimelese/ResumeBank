"""
Compile history.

A Resume row is a non-updating record of one compilation. Presets are
mutable, so the row does not describe what was compiled; the saved .tex file
is the immutable snapshot.
"""
from django.db import models


def resume_upload_path(instance, filename):
    # media/resumes/<resume_id>/<filename>. The row must be saved (pk set)
    # before files are assigned.
    return f'resumes/{instance.pk}/{filename}'


class Resume(models.Model):
    # SET_NULL keeps history when a preset is deleted; preset_name is the
    # snapshot that survives it.
    preset = models.ForeignKey(
        'presets.ResumePreset', on_delete=models.SET_NULL, null=True, blank=True, related_name='resumes',
    )
    preset_name = models.CharField(max_length=100)
    generated_at = models.DateTimeField(auto_now_add=True)
    # Result of compilation, not user-entered. Null until compile finishes.
    page_count = models.PositiveSmallIntegerField(null=True, blank=True)
    # Computed at compile time against the preset's page_limit.
    over_limit = models.BooleanField(default=False)
    pdf_file = models.FileField(upload_to=resume_upload_path, blank=True)
    tex_file = models.FileField(upload_to=resume_upload_path, blank=True)

    class Meta:
        ordering = ['-generated_at']

    def __str__(self):
        return f'{self.preset_name} @ {self.generated_at:%Y-%m-%d %H:%M}'
