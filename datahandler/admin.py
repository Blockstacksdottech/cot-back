from django.contrib import admin
from .models import *

# Register your models here.

admin.site.register(CustomUser)
admin.site.register(DateInterval)
admin.site.register(ProcessedData)
admin.site.register(VideoLinks)
admin.site.register(PdfFiles)
admin.site.register(Article)
admin.site.register(Currency)
admin.site.register(Symbol)
admin.site.register(Seasonality)
admin.site.register(Event)
admin.site.register(EventData)