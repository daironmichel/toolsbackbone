# Generated by Django 3.0.3 on 2020-03-12 10:28

from decimal import Decimal
import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('trader', '0020_autopilottask_discord_webhook'),
    ]

    operations = [
        migrations.AddField(
            model_name='tradingstrategy',
            name='pullback_percent',
            field=models.DecimalField(blank=True, decimal_places=2, default=Decimal('0'), max_digits=5, validators=[django.core.validators.MaxValueValidator(Decimal('100'))]),
        ),
        migrations.AlterField(
            model_name='tradingstrategy',
            name='exposure_percent',
            field=models.DecimalField(decimal_places=2, max_digits=5, validators=[django.core.validators.MaxValueValidator(Decimal('100'))]),
        ),
        migrations.AlterField(
            model_name='tradingstrategy',
            name='loss_percent',
            field=models.DecimalField(decimal_places=2, max_digits=5, validators=[django.core.validators.MaxValueValidator(Decimal('100'))]),
        ),
        migrations.AlterField(
            model_name='tradingstrategy',
            name='profit_percent',
            field=models.DecimalField(decimal_places=2, max_digits=5, validators=[django.core.validators.MaxValueValidator(Decimal('100'))]),
        ),
    ]
