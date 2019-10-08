from django.db import models

# Create your models here.


class RiskManagementSettings(models.Model):
    exposure = models.IntegerField()
    profit = models.IntegerField()
    loss = models.IntegerField()
    fee_per_trade = models.FloatField()
