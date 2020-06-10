from django.contrib import admin

from trader.models import (Account, AutoPilotTask, Broker, BufferCash,
                           ProviderSession, ServiceProvider, Settings,
                           TradingStrategy)

# Register your models here.


@admin.register(Settings)
class SettingsAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'refresh_rate',
                    'default_broker', 'default_strategy')


@admin.register(TradingStrategy)
class TradingStrategyAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'user', 'exposure_percent',
                    'profit_percent', 'loss_percent', 'fee_per_trade', )


@admin.register(Broker)
class BrokerAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'user')


@admin.register(Account)
class AccountAdmin(admin.ModelAdmin):
    list_display = ('id', 'account_id', 'name', 'institution_type',
                    'account_type', 'account_mode',
                    'pdt_status', 'cash_buying_power',
                    'margin_buying_power', 'last_updated', 'user')


@admin.register(BufferCash)
class BufferCashAdmin(admin.ModelAdmin):
    list_display = ('id', 'account_name', 'amount')

    def account_name(self, instance: BufferCash):
        return instance.account.name


@admin.register(ServiceProvider)
class ServiceProviderAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'protocol', 'broker', 'user')


@admin.register(ProviderSession)
class ProviderSessionAdmin(admin.ModelAdmin):
    list_display = ('id', 'status', 'refreshed', 'provider')


@admin.register(AutoPilotTask)
class AutoPilotTaskAdmin(admin.ModelAdmin):
    list_display = ('id', 'symbol', 'status', 'strategy', 'provider', 'user')
