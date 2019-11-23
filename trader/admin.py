from django.contrib import admin

from trader.models import Account, Broker, RiskStrategy, ServiceProvider

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


@admin.register(ServiceProvider)
class ServiceProviderAdmin(admin.ModelAdmin):
    list_display = ('name', 'protocol', 'broker', 'user')
