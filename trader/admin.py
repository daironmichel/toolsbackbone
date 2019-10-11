from django.contrib import admin
from trader.models import RiskManagementSettings

# Register your models here.


@admin.register(RiskManagementSettings)
class RiskManagementSettingsAdmin(admin.ModelAdmin):
    list_display = ('user', 'exposure', 'profit', 'loss', 'fee_per_trade', )
