# Generated by Django 3.0.2 on 2020-01-29 14:26

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('trader', '0008_auto_20191226_1937'),
    ]

    operations = [
        migrations.CreateModel(
            name='AutoPilotTask',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('status', models.SmallIntegerField(choices=[(0, 'Created'), (1, 'Queued'), (2, 'Running'), (3, 'Done')], default=0)),
                ('signal', models.SmallIntegerField(choices=[(0, 'Auto Driving'), (1, 'Manual Override'), (2, 'Buy Symbol'), (3, 'Sell Position')], default=0)),
                ('state', models.SmallIntegerField(choices=[(0, 'Buying Mode'), (1, 'Watching Mode'), (2, 'Selling Mode')], default=1)),
                ('modifier', models.SmallIntegerField(choices=[(0, 'Follow Strategy'), (1, 'Maximize Profit'), (2, 'Minimize Loss')], default=0)),
                ('symbol', models.CharField(max_length=10)),
                ('quantity', models.IntegerField(blank=True, default=0)),
                ('entry_price', models.DecimalField(blank=True, decimal_places=2, default=0, max_digits=12)),
                ('base_price', models.DecimalField(decimal_places=2, max_digits=12)),
                ('ref_price', models.DecimalField(decimal_places=2, max_digits=12)),
                ('ref_time', models.DateTimeField()),
                ('account', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='+', to='trader.Account')),
                ('provider', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='+', to='trader.ServiceProvider')),
                ('strategy', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='+', to='trader.TradingStrategy')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='+', to=settings.AUTH_USER_MODEL)),
            ],
        ),
    ]
