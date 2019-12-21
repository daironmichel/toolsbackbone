# Generated by Django 3.0.1 on 2019-12-21 13:16

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('trader', '0004_settings_default_strategy'),
    ]

    operations = [
        migrations.AddField(
            model_name='account',
            name='provider',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='accounts', to='trader.ServiceProvider'),
        ),
        migrations.AddField(
            model_name='serviceprovider',
            name='callback_configured',
            field=models.BooleanField(blank=True, default=False),
        ),
        migrations.AlterField(
            model_name='serviceprovider',
            name='account_key',
            field=models.CharField(blank=True, default='', max_length=250),
        ),
    ]
