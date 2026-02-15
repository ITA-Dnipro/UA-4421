from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("startups", "0006_alter_startupprofile_uuid"),
    ]

    operations = [
        migrations.AddField(
            model_name="startupprofile",
            name="pitch_deck_url",
            field=models.URLField(blank=True),
        ),
    ]
