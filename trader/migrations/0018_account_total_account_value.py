# Generated by Django 3.0.3 on 2020-03-03 14:09

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('trader', '0017_account_account_balance'),
    ]

    operations = [
        migrations.AddField(
            model_name='account',
            name='total_account_value',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=12),
            preserve_default=False,
        ),
    ]