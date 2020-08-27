# Generated by Django 3.0.4 on 2020-06-10 15:12

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('trader', '0024_autopilottask_exit_price'),
    ]

    operations = [
        migrations.CreateModel(
            name='BufferCash',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('amount', models.DecimalField(decimal_places=2, max_digits=12)),
                ('account', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='buffer_cash', to='trader.Account')),
            ],
        ),
    ]