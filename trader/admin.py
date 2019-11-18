from django.contrib import admin
from trader.models import RiskStrategy, Broker, Account

# Register your models here.


@admin.register(RiskStrategy)
class RiskStrategyAdmin(admin.ModelAdmin):
    list_display = ('user', 'name', 'exposure_percent',
                    'profit_percent', 'loss_percent', 'fee_per_trade', )


@admin.register(Broker)
class BrokerAdmin(admin.ModelAdmin):
    list_display = ('user', 'name')


@admin.register(Account)
class AccountAdmin(admin.ModelAdmin):
    list_display = ('user', 'name', 'number',
                    'purchasing_power', 'last_updated')
