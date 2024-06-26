from django.db import models
from django.contrib.auth.models import AbstractUser

# Create your models here.


class CustomUser(AbstractUser):
    username = models.CharField(max_length=255, default="", unique=True)
    name = models.CharField(max_length=255, default="")

    def __str__(self):
        return self.username


class DateInterval(models.Model):
    date = models.DateTimeField()

    def __str__(self):
        return str(self.date)


class Data(models.Model):
    date_interval = models.ForeignKey(DateInterval, on_delete=models.CASCADE)
    symbol = models.CharField(max_length=100)
    decision = models.CharField(max_length=50)
    sentiment_score = models.FloatField()
    crowded_long_positions = models.FloatField()
    crowded_short_positions = models.FloatField()
    speculative_positioning_index = models.FloatField()
    cot_ratio = models.FloatField()
    net_speculative_position = models.FloatField()
    comm_noncomm_ratio = models.FloatField()
    pct_oi_spec_positions = models.FloatField()
    overall_decision = models.CharField(max_length=50)
    overall_sentiment = models.FloatField()

    def __str__(self):
        return f"{self.symbol} - {self.date_interval}"


class GeneralData(models.Model):
    date_interval = models.ForeignKey(DateInterval, on_delete=models.CASCADE)
    symbol = models.CharField(max_length=100)
    comm_long = models.FloatField()
    comm_short = models.FloatField()
    comm_total = models.FloatField()
    comm_long_pct = models.FloatField()
    comm_short_pct = models.FloatField()
    comm_net_position = models.FloatField()
    comm_long_change = models.FloatField()
    comm_short_change = models.FloatField()
    comm_net_position_change = models.FloatField()
    comm_long_change_pct = models.FloatField()
    comm_short_change_pct = models.FloatField()
    comm_sentiment = models.CharField(max_length=50)
    noncomm_long = models.FloatField()
    noncomm_short = models.FloatField()
    noncomm_total = models.FloatField()
    noncomm_long_pct = models.FloatField()
    noncomm_short_pct = models.FloatField()
    noncomm_net_position = models.FloatField()
    noncomm_long_change = models.FloatField()
    noncomm_short_change = models.FloatField()
    noncomm_net_position_change = models.FloatField()
    noncomm_long_change_pct = models.FloatField()
    noncomm_short_change_pct = models.FloatField()
    noncomm_sentiment = models.CharField(max_length=50)

    def __str__(self):
        return f"{self.symbol} - {self.date_interval}"


class ProcessedData(models.Model):
    date_interval = models.ForeignKey(DateInterval, on_delete=models.CASCADE)
    pair = models.CharField(max_length=20)
    base_long = models.FloatField(default=0)
    base_short = models.FloatField(default=0)
    base_net_position = models.FloatField(default=0)
    quote_long = models.FloatField(default=0)
    quote_short = models.FloatField(default=0)
    quote_net_position = models.FloatField(default=0)
    base_comm_long = models.FloatField(default=0)
    base_comm_short = models.FloatField(default=0)
    base_comm_net_position = models.FloatField(default=0)
    quote_comm_long = models.FloatField(default=0)
    quote_comm_short = models.FloatField(default=0)
    quote_comm_net_position = models.FloatField(default=0)
    base_nonrep_long = models.FloatField(default=0)
    base_nonrep_short = models.FloatField(default=0)
    base_nonrep_net_position = models.FloatField(default=0)
    quote_nonrep_long = models.FloatField(default=0)
    quote_nonrep_short = models.FloatField(default=0)
    quote_nonrep_net_position = models.FloatField(default=0)
    pair_long = models.FloatField(default=0)
    pair_short = models.FloatField(default=0)
    pair_net_position = models.FloatField(default=0)
    pct_change = models.FloatField(default=0)
    two_week_change = models.FloatField(default=0)
    three_week_change = models.FloatField(default=0)
    four_week_change = models.FloatField(default=0)
    five_week_change = models.FloatField(default=0)
    six_week_change = models.FloatField(default=0)
    seven_week_change = models.FloatField(default=0)
    eight_week_change = models.FloatField(default=0)
    nine_week_change = models.FloatField(default=0)
    ten_week_change = models.FloatField(default=0)
    sentiment = models.CharField(max_length=20)

    def __str__(self):
        return f"{self.pair} - {self.date_interval}"
