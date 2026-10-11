from django.db import migrations


def clear_end_dates(apps, schema_editor):
    """Projects now show a single date by default; honors/certs never had an end."""
    Component = apps.get_model('bank', 'Component')
    Component.objects.filter(category__in=['project', 'honor', 'certification']).update(end_date=None)


class Migration(migrations.Migration):

    dependencies = [
        ('bank', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(clear_end_dates, migrations.RunPython.noop),
    ]
