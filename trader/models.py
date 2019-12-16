from decimal import Decimal

from django.contrib.auth.models import User
from django.db import models
from django.utils.text import slugify

# Create your models here.


class TradingStrategy(models.Model):
    name = models.CharField(max_length=250)
    exposure_percent = models.DecimalField(
        max_digits=3, decimal_places=0, max_length=100)
    profit_percent = models.DecimalField(
        max_digits=3, decimal_places=0, max_length=100)
    loss_percent = models.DecimalField(
        max_digits=3, decimal_places=0, max_length=100)
    fee_per_trade = models.DecimalField(
        max_digits=5, decimal_places=2, default=0)
    price_margin = models.DecimalField(
        max_digits=5, decimal_places=2, default=Decimal('0.02'))
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='trading_strategies')

    class Meta:
        verbose_name = 'Trading Strategy'
        verbose_name_plural = 'Trading Strategies'

    def __str__(self):
        return f'<TradingStrategy: {self.id}, "{self.name}">'

    def get_quantity_for(self, buying_power: Decimal, price_per_share: Decimal) -> Decimal:
        exposure_amount = buying_power * (self.exposure_percent / Decimal(100))
        return (exposure_amount / price_per_share).quantize(Decimal('1'))


class Broker(models.Model):
    name = models.CharField(max_length=250)
    slug = models.SlugField(max_length=250)
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='brokers')

    class Meta:
        unique_together = ("user", "slug")

    def __str__(self):
        # Disable pylint warn about self.user_id not being a member
        # pylint: disable=no-member
        return f'<Broker: {self.id}, "{self.name}">'

    def save(self, force_insert=False, force_update=False, using=None,
             update_fields=None):
        self.slug = slugify(self.name)
        super().save(force_insert, force_update, using, update_fields)


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


class ServiceProvider(models.Model):
    OAUTH1 = 'OAUTH1'
    OAUTH2 = 'OAUTH2'
    PROTOCOLS = [
        (OAUTH1, 'OAuth 1.0a'),
        (OAUTH2, 'OAuth 2'),
    ]

    name = models.CharField(max_length=250)
    slug = models.SlugField(max_length=250)
    protocol = models.CharField(
        max_length=10, choices=PROTOCOLS, default=OAUTH1)
    consumer_key = models.CharField(max_length=250)
    consumer_secret = models.CharField(max_length=250)
    request_token_url = models.CharField(max_length=250, default='')
    authorize_url = models.CharField(max_length=250, default='')
    access_token_url = models.CharField(max_length=250, default='')
    refresh_url = models.CharField(max_length=250, default='')
    revoke_url = models.CharField(max_length=250, default='')
    base_url = models.CharField(max_length=250, default='')
    account_key = models.CharField(max_length=250, default='')
    broker = models.ForeignKey(
        Broker, on_delete=models.CASCADE, related_name='service_providers')
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='service_providers')

    class Meta:
        unique_together = ("broker", "slug")

    def __str__(self):
        return f'<ServiceProvider: {self.id}, "{self.name}">'

    def save(self, force_insert=False, force_update=False, using=None,
             update_fields=None):
        self.slug = slugify(self.name)
        super().save(force_insert, force_update, using, update_fields)


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
    request_token = models.CharField(max_length=250, default='')
    request_token_secret = models.CharField(max_length=250, default='')
    access_token = models.CharField(max_length=250, default='')
    access_token_secret = models.CharField(max_length=250, default='')
    created = models.DateTimeField(auto_now_add=True)
    refreshed = models.DateTimeField(auto_now=True)
    provider = models.OneToOneField(
        ServiceProvider, on_delete=models.CASCADE, related_name='session')

    def __str__(self):
        return f'<ProviderSession: {self.id}>'
