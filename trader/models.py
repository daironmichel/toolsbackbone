from django.db import models
from django.contrib.auth.models import User

# Create your models here.


class RiskManagementSettings(models.Model):
    exposure = models.IntegerField()
    profit = models.IntegerField()
    loss = models.IntegerField()
    fee_per_trade = models.FloatField()
    user = models.OneToOneField(
        User, on_delete=models.CASCADE, null=True, related_name='risk_management_settings')

    class Meta:
        verbose_name = 'Risk Managent Settings'
        verbose_name_plural = 'Risk Managent Settings'
