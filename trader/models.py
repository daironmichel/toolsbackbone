from decimal import Decimal

from django.contrib.auth.models import User
from django.contrib.postgres.fields import JSONField
from django.core.validators import MaxValueValidator
from django.db import models
from django.utils.text import slugify

from trader.utils import get_round_price

# Create your models here.


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
    total_account_value = models.DecimalField(
        max_digits=12, decimal_places=2)
    account_balance = models.DecimalField(
        max_digits=12, decimal_places=2)
    net_cash = models.DecimalField(
        max_digits=12, decimal_places=2)
    cash_available_for_investment = models.DecimalField(
        max_digits=12, decimal_places=2)
    cash_balance = models.DecimalField(max_digits=12, decimal_places=2)
    cash_buying_power = models.DecimalField(max_digits=12, decimal_places=2)
    margin_buying_power = models.DecimalField(max_digits=12, decimal_places=2)
    last_updated = models.DateTimeField(auto_now=True)
    broker = models.ForeignKey(
        'Broker', on_delete=models.CASCADE, related_name='accounts')
    provider = models.ForeignKey(
        'ServiceProvider', on_delete=models.CASCADE, related_name='accounts')
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='accounts')

    def __str__(self):
        return f'<Account: {self.id}, "{self.name}">'

    @property
    def real_value(self):
        buffer_cash = BufferCash.objects.filter(account_id=self.id).first()
        buffer_amount = buffer_cash.amount if buffer_cash else Decimal('0.00')
        return self.total_account_value - buffer_amount


class TradingStrategy(models.Model):
    name = models.CharField(max_length=250)
    exposure_percent = models.DecimalField(
        max_digits=5, decimal_places=2, validators=[MaxValueValidator(Decimal(100))])
    profit_percent = models.DecimalField(
        max_digits=5, decimal_places=2, validators=[MaxValueValidator(Decimal(100))])
    loss_percent = models.DecimalField(
        max_digits=5, decimal_places=2, validators=[MaxValueValidator(Decimal(100))])
    pullback_percent = models.DecimalField(
        max_digits=5, decimal_places=2, validators=[MaxValueValidator(Decimal(100))], default=Decimal('0'), blank=True)
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

    def funded(self, account: Account) -> Decimal:
        exposure_amount = account.total_account_value * \
            (self.exposure_percent / Decimal(100))
        return exposure_amount < account.cash_available_for_investment


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

    def get_session_token(self):
        config_session = ProviderSession.objects.filter(
            provider=self).first()
        if not config_session:
            return None
        return (config_session.access_token,
                config_session.access_token_secret)

    def get_stored_session(self):
        return ProviderSession.objects.filter(
            provider=self).first()


def default_tracking_data():
    return {'quotes': [], 'top': '0'}


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


class AutoPilotTask(models.Model):
    READY = 0  # default
    QUEUED = 1
    RUNNING = 2
    DONE = 3
    PAUSED = 4
    TASK_STATUS = [
        (READY, "Ready"),
        (QUEUED, "Queued"),
        (RUNNING, "Running"),
        (DONE, "Done"),
        (PAUSED, "Paused"),
    ]

    # Signals used to force behavior of the task
    AUTO = 0  # task will handle position automatically (default)
    MANUAL_OVERRIDE = 1  # task will shutdown. position will remain as is
    BUY = 2  # task will buy position asap using the strategy
    SELL = 3  # task will sell position asap
    SIGNALS = [
        (AUTO, "Auto Driving"),
        (MANUAL_OVERRIDE, "Manual Override"),
        (BUY, "Buy Symbol"),
        (SELL, "Sell Position"),
    ]

    # current mode the autopilot task consumer is in
    BUYING = 0
    WATCHING = 1  # default
    SELLING = 2
    ERROR = 3
    STATES = [
        (BUYING, "Buying Mode"),
        (WATCHING, "Watching Mode"),
        (SELLING, "Selling Mode"),
        (ERROR, "Error Mode"),
    ]

    # modifiers that determine the behabior towards profit/loss
    FOLLOW_STRATEGY = 0  # follow strategy as is (default)
    MAXIMIZE_PROFIT = 1  # try to get the most profit by moving up the stop/profit price
    MINIMIZE_LOSS = 2  # try to at least brake even and have a smaller loss threshold
    MIN_LOSS_MAX_PROFIT = 3  # hybrid of MAXIMIZE_PROFIT and MINIMIZE_LOSS
    MODS = [
        (FOLLOW_STRATEGY, "Follow Strategy"),
        (MAXIMIZE_PROFIT, "Maximize Profit"),
        (MINIMIZE_LOSS, "Minimize Loss"),
        (MIN_LOSS_MAX_PROFIT, "Minimize Loss, Maximize Profit"),
    ]

    status = models.SmallIntegerField(choices=TASK_STATUS, default=READY)
    signal = models.SmallIntegerField(choices=SIGNALS, default=AUTO)
    state = models.SmallIntegerField(choices=STATES, default=WATCHING)
    modifier = models.SmallIntegerField(choices=MODS, default=FOLLOW_STRATEGY)
    tracking_data = JSONField(default=default_tracking_data)

    strategy = models.ForeignKey(
        TradingStrategy, on_delete=models.PROTECT, related_name='+')
    provider = models.ForeignKey(
        ServiceProvider, on_delete=models.PROTECT, related_name='+')
    account = models.ForeignKey(
        Account, on_delete=models.PROTECT, related_name='+')
    user = models.ForeignKey(
        User, on_delete=models.PROTECT, related_name='+')
    discord_webhook = models.CharField(max_length=250, null=True, blank=True)

    symbol = models.CharField(max_length=10)
    quantity = models.IntegerField(default=0, blank=True)
    entry_price = models.DecimalField(
        max_digits=12, decimal_places=4, default=0, blank=True)
    exit_price = models.DecimalField(
        max_digits=12, decimal_places=4, default=0, blank=True)
    is_otc = models.BooleanField(default=False, blank=True)

    error_message = models.CharField(max_length=500, default='', blank=True)

    # current order being tracked. if no order is being tracked
    # this field should be empty
    tracking_order_id = models.CharField(max_length=250, null=True, blank=True)

    # price used for calculating the loss amount based on the strategy
    # loss percentage. It may increase to accommodate for higher price.
    # for example: when maximazing profit a 3% drop at the highest profit point
    # is a much bigger amount than a 3% drop at the entry price
    base_price = models.DecimalField(max_digits=12, decimal_places=4)

    # price used to determine the stop price at which the position
    # should be sold for a profit. It will increase depending on modifier.
    profit_ref_price = models.DecimalField(max_digits=12, decimal_places=4)

    # price used to determine the stop price at which the position
    # should be sold for a loss. It will increase depending on modifier.
    loss_ref_price = models.DecimalField(max_digits=12, decimal_places=4)

    # timestamp used to determine if ref_price should be moved up
    # after certain amount of time have passed where the stock
    # price is above the ref_price + 1/2 loss_amount
    ref_time = models.DateTimeField()

    def __str__(self):
        return f'<AutoPilotTask: {self.id}, {self.symbol}, user:{self.user_id}>'

    def get_field_names(self):
        return {f.attname for f in self._meta.concrete_fields}

    @property
    def loss_amount(self) -> Decimal:
        return get_round_price(self.base_price * (self.strategy.loss_percent / Decimal('100')))

    @property
    def loss_price(self) -> Decimal:
        return get_round_price(self.loss_ref_price - self.loss_amount)

    @property
    def profit_amount(self) -> Decimal:
        return get_round_price(self.base_price * (self.strategy.profit_percent / Decimal('100')))

    @property
    def profit_price(self) -> Decimal:
        return get_round_price(self.profit_ref_price + self.profit_amount)

    @property
    def top_price(self) -> Decimal:
        top_data = self.tracking_data.get('top', '0')

        if not top_data:
            return Decimal('0')

        return Decimal(top_data)

    @property
    def pullback_amount(self) -> Decimal:
        if not self.strategy.pullback_percent:
            return Decimal('0')

        if not self.top_price:
            return Decimal('0')

        return get_round_price(self.top_price * (self.strategy.pullback_percent / Decimal('100')))

    @property
    def pullback_price(self) -> Decimal:
        if not self.pullback_amount:
            return Decimal('0')
        return get_round_price(self.top_price - self.pullback_amount)

    @property
    def exit_percent(self) -> Decimal:
        gain = self.exit_price - self.entry_price
        percent = gain / self.entry_price * Decimal(100)
        return percent.quantize(Decimal('0.01'))


class BufferCash(models.Model):
    """Represents portion of an Account total value that is meant only
    for giving a boost to the account. The buffer amount will
    not be counted towards the real account value or the exposure 
    percent when buying a security. The buffer amount will never be used
    for buying securities.

    Account Real Value = (Account Balance) - (Buffer Cash)
    """
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    account = models.OneToOneField(
        Account, on_delete=models.CASCADE, related_name='buffer_cash')


class Settings(models.Model):
    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name='settings')
    refresh_rate = models.IntegerField(default=0)
    default_broker = models.ForeignKey(
        Broker, on_delete=models.PROTECT, null=True, default=None, related_name='+')
    default_strategy = models.ForeignKey(
        TradingStrategy, on_delete=models.PROTECT, null=True, default=None, related_name='+')
    default_autopilot_modifier = models.SmallIntegerField(
        choices=AutoPilotTask.MODS, default=AutoPilotTask.FOLLOW_STRATEGY)
    discord_webhook = models.CharField(max_length=250, null=True, blank=True)

    def __str__(self):
        return f'<Settings: {self.id}, user_id: {self.user_id}>'
