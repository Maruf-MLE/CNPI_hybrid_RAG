from __future__ import annotations

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies: list = []

    operations = [
        migrations.CreateModel(
            name="ProcessedMessage",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "mid",
                    models.CharField(
                        db_index=True,
                        help_text="Facebook Messenger message ID (mid)",
                        max_length=255,
                        unique=True,
                    ),
                ),
                (
                    "psid",
                    models.CharField(
                        help_text="Page-Scoped User ID of the sender",
                        max_length=64,
                    ),
                ),
                ("processed_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={
                "verbose_name": "Processed Message",
                "verbose_name_plural": "Processed Messages",
            },
        ),
    ]
