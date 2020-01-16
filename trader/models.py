from decimal import Decimal

from django.contrib.auth.models import User
from django.core.validators import MaxValueValidator
from django.db import models
from django.utils.text import slugify

from trader.utils import get_round_price

# Create your models here.


class Settings(models.Model):
    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name='settings')
    refresh_rate = models.IntegerField(default=0)
    default_broker = models.ForeignKey(
        'Broker', on_delete=models.PROTECT, null=True, default=None, related_name='+')
    default_strategy = models.ForeignKey(
        'TradingStrategy', on_delete=models.PROTECT, null=True, default=None, related_name='+')

    def __str__(self):
        return f'<Settings: {self.id}, user_id: {self.user_id}>'


class TradingStrategy(models.Model):
    name = models.CharField(max_length=250)
    exposure_percent = models.DecimalField(
        max_digits=3, decimal_places=0, validators=[MaxValueValidator(Decimal(100))])
    profit_percent = models.DecimalField(
        max_digits=3, decimal_places=0, validators=[MaxValueValidator(Decimal(100))])
    loss_percent = models.DecimalField(
        max_digits=3, decimal_places=0, validators=[MaxValueValidator(Decimal(100))])
    fee_per_trade = models.DecimalField(
        max_digits=5, decimal_places=2, default=0)
    price_margin = models.DecimalField(
        max_digits=5, decimal_places=2, max_length=Decimal('0.01'), default=Decimal('0.01'), blank=True)
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
    default_provider = models.ForeignKey(
        'ServiceProvider', on_delete=models.SET_NULL, null=True, blank=True, default=None, related_name='+')
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
    provider = models.ForeignKey(
        'ServiceProvider', on_delete=models.CASCADE, related_name='accounts')
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
    callback_configured = models.BooleanField(default=False, blank=True)
    account_key = models.CharField(max_length=250, default='', blank=True)
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


class AutoPilot(models.Model):
    symbol = models.CharField(max_length=10)
    strategy = models.ForeignKey(TradingStrategy, on_delete=models.PROTECT)
    provider = models.ForeignKey(ServiceProvider, on_delete=models.PROTECT)
    account = models.ForeignKey(Account, on_delete=models.PROTECT)

    # Flag used to signal the auto pilot to sell the position asap
    # even thought it hasn't hit the stop price
    early_exit = models.BooleanField(default=False)

    # price used for calculating the loss amount based on the strategy
    # loss percentage. It will increase by the loss_percent amount when
    # profit_percent + loss_percent is reached.
    base_price = models.DecimalField(max_digits=12, decimal_places=2)

    # price used to determine the stop price at which the position
    # should be exited. It will increase by 1/2 loss_percent when
    # that price level is held for a certain amount of time.
    ref_price = models.DecimalField(max_digits=12, decimal_places=2)

    # timestamp used to determine if ref_price should be moved up
    # after certain amount of time have passed where the stock
    # price is above the ref_price + 1/2 loss_amount
    ref_time = models.DateTimeField()

    def __str__(self):
        return f'<AutoPilot: {self.id}, {self.symbol}>'

    @property
    def loss_amount(self) -> Decimal:
        return get_round_price(self.base_price * (self.strategy.loss_percent / Decimal('100')))

    @property
    def profit_amount(self) -> Decimal:
        return get_round_price(self.base_price * (self.strategy.profit_percent / Decimal('100')))

    @property
    def stop_price(self) -> Decimal:
        return get_round_price(self.ref_price - self.loss_amount)
