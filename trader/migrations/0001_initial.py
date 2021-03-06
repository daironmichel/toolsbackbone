# Generated by Django 3.0 on 2019-12-14 12:35

from decimal import Decimal
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Broker',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=250)),
                ('slug', models.SlugField(max_length=250)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='brokers', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'unique_together': {('user', 'slug')},
            },
        ),
        migrations.CreateModel(
            name='TradingStrategy',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=250)),
                ('exposure_percent', models.DecimalField(decimal_places=0, max_digits=3, max_length=100)),
                ('profit_percent', models.DecimalField(decimal_places=0, max_digits=3, max_length=100)),
                ('loss_percent', models.DecimalField(decimal_places=0, max_digits=3, max_length=100)),
                ('fee_per_trade', models.DecimalField(decimal_places=2, default=0, max_digits=5)),
                ('price_margin', models.DecimalField(decimal_places=2, default=Decimal('0.02'), max_digits=5)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='trading_strategies', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Trading Strategy',
                'verbose_name_plural': 'Trading Strategies',
            },
        ),
        migrations.CreateModel(
            name='ServiceProvider',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=250)),
                ('slug', models.SlugField(max_length=250)),
                ('protocol', models.CharField(choices=[('OAUTH1', 'OAuth 1.0a'), ('OAUTH2', 'OAuth 2')], default='OAUTH1', max_length=10)),
                ('consumer_key', models.CharField(max_length=250)),
                ('consumer_secret', models.CharField(max_length=250)),
                ('request_token_url', models.CharField(default='', max_length=250)),
                ('authorize_url', models.CharField(default='', max_length=250)),
                ('access_token_url', models.CharField(default='', max_length=250)),
                ('refresh_url', models.CharField(default='', max_length=250)),
                ('revoke_url', models.CharField(default='', max_length=250)),
                ('base_url', models.CharField(default='', max_length=250)),
                ('account_key', models.CharField(default='', max_length=250)),
                ('broker', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='service_providers', to='trader.Broker')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='service_providers', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'unique_together': {('broker', 'slug')},
            },
        ),
        migrations.CreateModel(
            name='ProviderSession',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('status', models.SmallIntegerField(choices=[(0, 'Requesting Access'), (1, 'Access Granted'), (2, 'Access Token Inactive'), (3, 'Access Token Expired'), (4, 'Access Token Revoked')], default=0)),
                ('request_token', models.CharField(default='', max_length=250)),
                ('request_token_secret', models.CharField(default='', max_length=250)),
                ('access_token', models.CharField(default='', max_length=250)),
                ('access_token_secret', models.CharField(default='', max_length=250)),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('refreshed', models.DateTimeField(auto_now=True)),
                ('provider', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='session', to='trader.ServiceProvider')),
            ],
        ),
        migrations.CreateModel(
            name='Account',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=250)),
                ('description', models.CharField(max_length=250)),
                ('account_id', models.CharField(max_length=250)),
                ('account_key', models.CharField(max_length=250)),
                ('account_type', models.CharField(max_length=50)),
                ('institution_type', models.CharField(max_length=50)),
                ('account_mode', models.CharField(choices=[('CASH', 'CASH'), ('MARGIN', 'MARGIN')], max_length=25)),
                ('account_status', models.CharField(choices=[('ACTIVE', 'ACTIVE'), ('CLOSED', 'CLOSED')], max_length=25)),
                ('pdt_status', models.CharField(max_length=50)),
                ('cash_balance', models.DecimalField(decimal_places=2, max_digits=12)),
                ('cash_buying_power', models.DecimalField(decimal_places=2, max_digits=12)),
                ('margin_buying_power', models.DecimalField(decimal_places=2, max_digits=12)),
                ('last_updated', models.DateTimeField(auto_now=True)),
                ('broker', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='accounts', to='trader.Broker')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='accounts', to=settings.AUTH_USER_MODEL)),
            ],
        ),
    ]
