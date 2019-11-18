from django.db import models
from django.contrib.auth.models import User

# Create your models here.


class RiskStrategy(models.Model):
    name = models.CharField(max_length=250)
    exposure_percent = models.IntegerField()
    profit_percent = models.IntegerField()
    loss_percent = models.IntegerField()
    fee_per_trade = models.FloatField(default=0)
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, null=True, related_name='risk_strategies')

    class Meta:
        verbose_name = 'Risk Strategy'
        verbose_name_plural = 'Risk Strategies'

    def __str__(self):
        # Disable pylint warn about self.user_id not being a member
        # pylint: disable=no-member
        return f'<RiskStrategy: name="{self.name}", user={self.user_id}>'


class Broker(models.Model):
    name = models.CharField(max_length=250)
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, null=True, related_name='brokers')

    def __str__(self):
        # Disable pylint warn about self.user_id not being a member
        # pylint: disable=no-member
        return f'<Broker: name="{self.name}", user={self.user_id}>'


class Account(models.Model):
    name = models.CharField(max_length=250)
    last_updated = models.DateTimeField(auto_now=True)
    number = models.IntegerField()
    purchasing_power = models.DecimalField(max_digits=12, decimal_places=2)
    broker = models.ForeignKey(
        Broker, on_delete=models.CASCADE, related_name='accounts')
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, null=True, related_name='accounts')

    def __str__(self):
        # Disable pylint warn about self.user_id not being a member
        # pylint: disable=no-member
        return f'<Account: name="{self.name}", user={self.user_id}>'
