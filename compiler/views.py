from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_GET, require_POST

from presets.models import ResumePreset

from . import services
from .models import Resume


@require_GET
def preview(request, preset_id):
    """Workspace preview pane. Compiles on every call (pdflatex is fast; no cache to invalidate)."""
    preset = get_object_or_404(ResumePreset, pk=preset_id)
    result = services.compile_preview(preset)
    return render(request, 'compiler/_preview.html', {'preset': preset, 'result': result})


@require_POST
def compile_preset(request, preset_id):
    """'Save to history': full compile that records a Resume row."""
    preset = get_object_or_404(ResumePreset, pk=preset_id)
    try:
        resume = services.compile_to_history(preset)
    except services.CompileError as e:
        messages.error(request, f'Compile failed: {e.result.error}')
    else:
        messages.success(request, f'Saved to history: {resume.page_count} page(s).')
    if request.headers.get('HX-Request'):
        return render(request, 'compiler/_history_bar.html', {'preset': preset, 'show_messages': True})
    return redirect('presets:workspace', pk=preset.pk)


def history(request):
    resumes = Resume.objects.select_related('preset')
    preset = None
    if request.GET.get('preset'):
        preset = get_object_or_404(ResumePreset, pk=request.GET['preset'])
        resumes = resumes.filter(preset=preset)
    return render(request, 'compiler/history.html', {'resumes': resumes, 'preset': preset})
