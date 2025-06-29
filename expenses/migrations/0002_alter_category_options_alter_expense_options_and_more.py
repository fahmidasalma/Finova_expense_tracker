# Generated by Django 5.1.6 on 2025-06-10 14:55

import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("expenses", "0001_initial"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="category",
            options={"verbose_name_plural": "Categories"},
        ),
        migrations.AlterModelOptions(
            name="expense",
            options={"ordering": ["-date"]},
        ),
        migrations.RemoveField(
            model_name="expense",
            name="data",
        ),
        migrations.AddField(
            model_name="expense",
            name="category",
            field=models.CharField(blank=True, max_length=266, null=True),
        ),
        migrations.AddField(
            model_name="expense",
            name="date",
            field=models.DateField(default=django.utils.timezone.now),
        ),
    ]
