# -*- coding: utf-8 -*-
# Generated by Django 1.9.1 on 2016-03-06 23:46
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('kdata', '0008_auto_20160307_0121'),
    ]

    operations = [
        migrations.AddField(
            model_name='surveytoken',
            name='persistent',
            field=models.BooleanField(default=True),
        ),
    ]
