# Generated by Django 3.0.3 on 2020-02-18 20:16

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('trader', '0010_autopilottask_tracking_order_id'),
    ]

    operations = [
        migrations.AddField(
            model_name='autopilottask',
            name='is_otc',
            field=models.BooleanField(blank=True, default=False),
        ),
    ]
