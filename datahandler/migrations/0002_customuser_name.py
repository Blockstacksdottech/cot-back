# Generated by Django 4.2.13 on 2024-06-08 20:04

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('datahandler', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='customuser',
            name='name',
            field=models.CharField(default='', max_length=255),
        ),
    ]
