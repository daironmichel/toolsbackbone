# Generated by Django 3.0.3 on 2020-02-22 14:52

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('trader', '0012_auto_20200222_1432'),
    ]

    operations = [
        migrations.AlterField(
            model_name='autopilottask',
            name='status',
            field=models.SmallIntegerField(choices=[(0, 'Ready'), (1, 'Queued'), (2, 'Running'), (3, 'Done'), (4, 'Paused')], default=0),
        ),
    ]
