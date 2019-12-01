import datetime
import math  # pylint: disable=no-member

import pytz
from django.contrib.auth.models import User
from django.db import models

# Create your models here.


class TradingStrategy(models.Model):
    name = models.CharField(max_length=250)
    exposure_percent = models.IntegerField()
    profit_percent = models.IntegerField()
    loss_percent = models.IntegerField()
    fee_per_trade = models.DecimalField(
        max_digits=5, decimal_places=2, default=0)
    price_margin = models.DecimalField(
        max_digits=5, decimal_places=2, default=2)
    max_price_margin = models.DecimalField(
        max_digits=5, decimal_places=2, default=0.02)
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='trading_strategies')

    class Meta:
        verbose_name = 'Trading Strategy'
        verbose_name_plural = 'Trading Strategies'

    def __str__(self):
        return f'<TradingStrategy: {self.id}, "{self.name}">'

    def get_quantity_for(self, buying_power, price_per_share):
        exposure_amount = math.floor(
            buying_power * (self.exposure_percent / 100))
        return math.floor(exposure_amount / price_per_share)

    def get_limit_price(self, action, current_price):
        buying_actions = (Order.BUY, Order.BUY_TO_COVER)
        limit_abs_dt = self.price_margin
        limit_max_dt = self.max_price_margin

        price = current_price
        digits = 0
        if price > 1:
            while price > 0:
                digits += 1
                price //= 10
            limit_rel_dt = limit_abs_dt / math.pow(10, digits - 1)
        else:
            while price < 1:
                digits += 1
                price *= 10
            limit_rel_dt = limit_abs_dt / math.pow(10, digits + 2)

        limit_rel_dt = round(limit_rel_dt, digits + 2)
        if limit_rel_dt > limit_max_dt:
            limit_rel_dt = limit_max_dt

        if action in buying_actions:
            limit_price = current_price + limit_rel_dt
        else:
            limit_price = current_price - limit_rel_dt

        return round(limit_price, digits + 2)


class Broker(models.Model):
    name = models.CharField(max_length=250)
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='brokers')

    def __str__(self):
        # Disable pylint warn about self.user_id not being a member
        # pylint: disable=no-member
        return f'<Broker: {self.id}, "{self.name}">'


class Account(models.Model):
    CASH = "CASH"
    MARGIN = "MARGIN"
    ACCOUNT_MODES = [
        (CASH, 'CASH'),
        (MARGIN, 'MARGIN')
    ]

    ACTIVE = 'ACTIVE'
    CLOSED = 'CLOSED'
    ACCOUNT_STATUS = [
        (ACTIVE, 'ACTIVE'),
        (CLOSED, 'CLOSED')
    ]

    name = models.CharField(max_length=250)
    description = models.CharField(max_length=250)
    account_id = models.CharField(max_length=250)
    account_key = models.CharField(max_length=250)
    account_type = models.CharField(max_length=50)
    institution_type = models.CharField(max_length=50)
    account_mode = models.CharField(max_length=25, choices=ACCOUNT_MODES)
    account_status = models.CharField(max_length=25, choices=ACCOUNT_STATUS)
    pdt_status = models.CharField(max_length=50)
    cash_balance = models.DecimalField(max_digits=12, decimal_places=2)
    cash_buying_power = models.DecimalField(max_digits=12, decimal_places=2)
    margin_buying_power = models.DecimalField(max_digits=12, decimal_places=2)
    last_updated = models.DateTimeField(auto_now=True)
    broker = models.ForeignKey(
        Broker, on_delete=models.CASCADE, related_name='accounts')
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='accounts')

    def __str__(self):
        return f'<Account: {self.id}, "{self.name}">'


class ProviderSession(models.Model):
    REQUESTING = 0
    CONNECTED = 1
    INACTIVE = 2
    EXPIRED = 3
    CLOSED = 4
    SESSION_STATUS = [
        (REQUESTING, 'Requesting Access'),
        (CONNECTED, 'Access Granted'),
        (INACTIVE, 'Access Token Inactive'),
        (EXPIRED, 'Access Token Expired'),
        (CLOSED, 'Access Token Revoked')
    ]
    status = models.SmallIntegerField(
        choices=SESSION_STATUS, default=REQUESTING)
    request_token = models.CharField(max_length=250, null=True)
    request_token_secret = models.CharField(max_length=250, null=True)
    access_token = models.CharField(max_length=250, null=True)
    access_token_secret = models.CharField(max_length=250, null=True)

    def __str__(self):
        return f'<ProviderSession: {self.id}>'


class ServiceProvider(models.Model):
    OAUTH1 = 'OAUTH1'
    OAUTH2 = 'OAUTH2'
    PROTOCOLS = [
        (OAUTH1, 'OAuth 1.0a'),
        (OAUTH2, 'OAuth 2'),
    ]

    name = models.CharField(max_length=250)
    protocol = models.CharField(
        max_length=10, choices=PROTOCOLS, default=OAUTH1)
    consumer_key = models.CharField(max_length=250)
    consumer_secret = models.CharField(max_length=250)
    request_token_url = models.CharField(max_length=250, null=True, blank=True)
    authorize_url = models.CharField(max_length=250, null=True, blank=True)
    access_token_url = models.CharField(max_length=250, null=True, blank=True)
    refresh_url = models.CharField(max_length=250, null=True, blank=True)
    revoke_url = models.CharField(max_length=250, null=True, blank=True)
    base_url = models.CharField(max_length=250, null=True, blank=True)
    session = models.OneToOneField(
        ProviderSession, on_delete=models.CASCADE, related_name='provider', null=True, blank=True)
    broker = models.ForeignKey(
        Broker, on_delete=models.CASCADE, related_name='service_providers')
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='service_providers')

    def __str__(self):
        return f'<ServiceProvider: {self.id}, "{self.name}">'
