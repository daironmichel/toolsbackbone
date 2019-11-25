# pylint: disable=no-member
from django.contrib.auth.models import User
from django.db import models

# Create your models here.


class TradingStrategy(models.Model):
    name = models.CharField(max_length=250)
    exposure_percent = models.IntegerField()
    profit_percent = models.IntegerField()
    loss_percent = models.IntegerField()
    fee_per_trade = models.FloatField(default=0)
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='trading_strategies')

    class Meta:
        verbose_name = 'Trading Strategy'
        verbose_name_plural = 'Trading Strategies'

    def __str__(self):
        return f'<TradingStrategy: {self.id}, "{self.name}">'


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

    name = models.CharField(max_length=250)
    description = models.CharField(max_length=250)
    account_id = models.CharField(max_length=250)
    account_key = models.CharField(max_length=250)
    account_type = models.CharField(max_length=250)
    account_mode = models.CharField(max_length=250, choices=ACCOUNT_MODES)
    pdt_status = models.CharField(max_length=250)
    number = models.IntegerField()
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


class Position(models.Model):
    symbol = models.CharField(max_length=6)
    quantity = models.IntegerField()
    account = models.ForeignKey(
        Account, on_delete=models.CASCADE, related_name='positions')
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='positions')

    def __str__(self):
        return f'<Position: {self.id}, {self.symbol}, qty={self.quantity}>'


class Order(models.Model):
    OPEN = 'OPEN'
    EXECUTED = 'EXECUTED'
    CANCELLED = 'CANCELLED'
    CANCEL_REQUESTED = 'CANCEL_REQUESTED'
    EXPIRED = 'EXPIRED'
    REJECTED = 'REJECTED'
    PARTIAL = 'PARTIAL'
    ORDER_STATUS = [
        (OPEN, OPEN),
        (EXECUTED, EXECUTED),
        (CANCELLED, CANCELLED),
        (CANCEL_REQUESTED, CANCEL_REQUESTED),
        (EXPIRED, EXPIRED),
        (REJECTED, REJECTED),
        (PARTIAL, PARTIAL)
    ]

    BUY = 'BUY'
    SELL = 'SELL'
    BUY_TO_COVER = 'BUY_TO_COVER'
    SELL_SHORT = 'SELL_SHORT'
    ORDER_ACTIONS = [
        (BUY, BUY),
        (SELL, SELL),
        (BUY_TO_COVER, BUY_TO_COVER),
        (SELL_SHORT, SELL_SHORT)
    ]

    symbol = models.CharField(max_length=6)
    quantity = models.IntegerField()
    preview_ids = models.CharField(max_length=250)
    order_id = models.CharField(max_length=250)
    status = models.CharField(max_length=50, choices=ORDER_STATUS)
    action = models.CharField(max_length=50, choices=ORDER_ACTIONS)
    account = models.ForeignKey(
        Account, on_delete=models.CASCADE, related_name='orders')
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='orders')

    def __str__(self):
        return f'<Order: {self.id}, {self.action} {self.quantity} {self.symbol}>'


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
