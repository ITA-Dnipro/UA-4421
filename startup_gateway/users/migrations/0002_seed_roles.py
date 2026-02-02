from django.db import migrations


def seed_roles(apps, schema_editor):
    Role = apps.get_model("users", "Role")
    for name in ("startup", "investor"):
        Role.objects.get_or_create(name=name)


class Migration(migrations.Migration):
    dependencies = [
        ("users", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(seed_roles, migrations.RunPython.noop),
    ]