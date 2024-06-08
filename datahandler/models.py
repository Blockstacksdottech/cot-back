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
