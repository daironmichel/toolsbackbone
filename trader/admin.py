from django.contrib import admin

from trader.models import (Account, Broker, ProviderSession, ServiceProvider,
                           Settings, TradingStrategy)

# Register your models here.


@admin.register(Settings)
class SettingsAdmin(admin.ModelAdmin):
    list_display = ('user', 'refresh_rate',
                    'default_broker', 'default_strategy')


@admin.register(TradingStrategy)
class TradingStrategyAdmin(admin.ModelAdmin):
    list_display = ('user', 'name', 'exposure_percent',
                    'profit_percent', 'loss_percent', 'fee_per_trade', )


@admin.register(Broker)
class BrokerAdmin(admin.ModelAdmin):
    list_display = ('user', 'name')


@admin.register(Account)
class AccountAdmin(admin.ModelAdmin):
    list_display = ('user', 'name', 'account_id', 'institution_type',
                    'account_type', 'account_mode',
                    'pdt_status', 'cash_buying_power',
                    'margin_buying_power', 'last_updated')


@admin.register(ServiceProvider)
class ServiceProviderAdmin(admin.ModelAdmin):
    list_display = ('name', 'protocol', 'broker', 'user')


@admin.register(ProviderSession)
class ProviderSessionAdmin(admin.ModelAdmin):
    list_display = ('status', 'refreshed', 'provider')
