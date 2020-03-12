# Generated by Django 3.0.3 on 2020-03-12 11:59

import django.contrib.postgres.fields.jsonb
from django.db import migrations
import trader.models


class Migration(migrations.Migration):

    dependencies = [
        ('trader', '0021_auto_20200312_1028'),
    ]

    operations = [
        migrations.AddField(
            model_name='autopilottask',
            name='tracking_data',
            field=django.contrib.postgres.fields.jsonb.JSONField(default=trader.models.default_tracking_data),
        ),
    ]
