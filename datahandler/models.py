from django.db import models
from django.contrib.auth.models import AbstractUser
import uuid

# Create your models here.


class CustomUser(AbstractUser):
    username = models.CharField(max_length=255, default="", unique=True)
    name = models.CharField(max_length=255, default="")
    email = models.EmailField(unique=True)
    is_active = models.BooleanField(default=True)
    is_member = models.BooleanField(default=False)

    def __str__(self):
        return self.username


class RecoveryRequest(models.Model):
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE)
    recovery_id = models.UUIDField(default=uuid.uuid4, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"RecoveryRequest for {self.user.username}"


class UserDetails(models.Model):
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE)
    full_name = models.CharField(max_length=255, default="", blank=True)
    mobile = models.CharField(max_length=20, default="", blank=True)
    address = models.TextField(default="", blank=True)
    city = models.CharField(max_length=100, default="", blank=True)
    state = models.CharField(max_length=100, default="", blank=True)
    country = models.CharField(max_length=100, default="", blank=True)
    zip_code = models.CharField(max_length=20, default="", blank=True)

    def __str__(self):
        return self.user.username


class UserImage(models.Model):
    user = models.OneToOneField(
        CustomUser, on_delete=models.CASCADE)
    profile_picture = models.ImageField(
        upload_to='profile_pictures/', null=True, blank=True)

    def __str__(self):
        return self.user.username
    
# blog model
class Article(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    title = models.CharField(max_length=255, default="", blank=True)
    content = models.TextField(default="", blank=True)
    image = models.ImageField(
        upload_to='thumbnails/', null=True, blank=True)
    date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title

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
    pair = models.CharField(max_length=10)
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

    # Percentage change fields
    pair_pct_change = models.FloatField(default=0)
    pair_comm_pct_change = models.FloatField(default=0)
    pair_2_week_change = models.FloatField(default=0)
    pair_3_week_change = models.FloatField(default=0)
    pair_4_week_change = models.FloatField(default=0)
    pair_5_week_change = models.FloatField(default=0)
    pair_6_week_change = models.FloatField(default=0)
    pair_7_week_change = models.FloatField(default=0)
    pair_8_week_change = models.FloatField(default=0)
    pair_9_week_change = models.FloatField(default=0)
    pair_10_week_change = models.FloatField(default=0)
    pair_comm_2_week_change = models.FloatField(default=0)
    pair_comm_3_week_change = models.FloatField(default=0)
    pair_comm_4_week_change = models.FloatField(default=0)
    pair_comm_5_week_change = models.FloatField(default=0)
    pair_comm_6_week_change = models.FloatField(default=0)
    pair_comm_7_week_change = models.FloatField(default=0)
    pair_comm_8_week_change = models.FloatField(default=0)
    pair_comm_9_week_change = models.FloatField(default=0)
    pair_comm_10_week_change = models.FloatField(default=0)

    # Open interest fields
    pair_pct_change_open_interest = models.FloatField(default=0)
    pair_2_week_change_open_interest = models.FloatField(default=0)
    pair_3_week_change_open_interest = models.FloatField(default=0)
    pair_4_week_change_open_interest = models.FloatField(default=0)
    pair_5_week_change_open_interest = models.FloatField(default=0)
    pair_6_week_change_open_interest = models.FloatField(default=0)
    pair_7_week_change_open_interest = models.FloatField(default=0)
    pair_8_week_change_open_interest = models.FloatField(default=0)
    pair_9_week_change_open_interest = models.FloatField(default=0)
    pair_10_week_change_open_interest = models.FloatField(default=0)

    # Noncommercial diff absolute fields
    noncomm_diff_absolute_long = models.FloatField(default=0)
    noncomm_diff_absolute_short = models.FloatField(default=0)
    noncomm_2_diff_absolute_long = models.FloatField(default=0)
    noncomm_3_diff_absolute_long = models.FloatField(default=0)
    noncomm_4_diff_absolute_long = models.FloatField(default=0)
    noncomm_5_diff_absolute_long = models.FloatField(default=0)
    noncomm_6_diff_absolute_long = models.FloatField(default=0)
    noncomm_7_diff_absolute_long = models.FloatField(default=0)
    noncomm_8_diff_absolute_long = models.FloatField(default=0)
    noncomm_9_diff_absolute_long = models.FloatField(default=0)
    noncomm_10_diff_absolute_long = models.FloatField(default=0)
    noncomm_2_diff_absolute_short = models.FloatField(default=0)
    noncomm_3_diff_absolute_short = models.FloatField(default=0)
    noncomm_4_diff_absolute_short = models.FloatField(default=0)
    noncomm_5_diff_absolute_short = models.FloatField(default=0)
    noncomm_6_diff_absolute_short = models.FloatField(default=0)
    noncomm_7_diff_absolute_short = models.FloatField(default=0)
    noncomm_8_diff_absolute_short = models.FloatField(default=0)
    noncomm_9_diff_absolute_short = models.FloatField(default=0)
    noncomm_10_diff_absolute_short = models.FloatField(default=0)

    # Commercial diff absolute fields
    comm_diff_absolute_long = models.FloatField(default=0)
    comm_diff_absolute_short = models.FloatField(default=0)
    comm_2_diff_absolute_long = models.FloatField(default=0)
    comm_3_diff_absolute_long = models.FloatField(default=0)
    comm_4_diff_absolute_long = models.FloatField(default=0)
    comm_5_diff_absolute_long = models.FloatField(default=0)
    comm_6_diff_absolute_long = models.FloatField(default=0)
    comm_7_diff_absolute_long = models.FloatField(default=0)
    comm_8_diff_absolute_long = models.FloatField(default=0)
    comm_9_diff_absolute_long = models.FloatField(default=0)
    comm_10_diff_absolute_long = models.FloatField(default=0)
    comm_2_diff_absolute_short = models.FloatField(default=0)
    comm_3_diff_absolute_short = models.FloatField(default=0)
    comm_4_diff_absolute_short = models.FloatField(default=0)
    comm_5_diff_absolute_short = models.FloatField(default=0)
    comm_6_diff_absolute_short = models.FloatField(default=0)
    comm_7_diff_absolute_short = models.FloatField(default=0)
    comm_8_diff_absolute_short = models.FloatField(default=0)
    comm_9_diff_absolute_short = models.FloatField(default=0)
    comm_10_diff_absolute_short = models.FloatField(default=0)

    # Extra fields
    sentiment = models.CharField(max_length=50, default='Neutral')
    is_contract = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.pair} - {self.date_interval.date.strftime('%Y-%m-%d')}"


class VideoLinks(models.Model):
    topic = models.CharField(default="", max_length=255)
    link = models.URLField(max_length=200)

    def __str__(self):
        return self.link


class PdfFiles(models.Model):
    topic = models.CharField(default="", max_length=255)
    file = models.FileField(upload_to='pdfs/')

    def __str__(self):
        return self.file.name


class Announcement(models.Model):
    topic = models.CharField(max_length=255)
    description = models.TextField()
    date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.topic
