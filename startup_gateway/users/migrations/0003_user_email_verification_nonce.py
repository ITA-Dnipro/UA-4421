from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("users", "0002_seed_roles"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="email_verification_nonce",
            field=models.CharField(max_length=64, blank=True, default=""),
        ),
    ]
