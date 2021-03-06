# -*- coding: utf-8 -*-
# Generated by Django 1.9.1 on 2016-08-09 15:48
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('kdata', '0016_group_config'),
    ]

    operations = [
        migrations.AddField(
            model_name='oauthdevice',
            name='ts_refresh2',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='device',
            name='type',
            field=models.CharField(choices=[('Ios', 'iOS (our app)'), ('Android', 'Android'), ('PurpleRobot', 'PurpleRobot'), ('MurataBSN', 'MurataBSN'), ('kdata.devices.Actiwatch', 'Philips Actiwatch'), ('kdata.aware.AwareDevice', 'Aware device'), ('kdata.aware.AwareDeviceValidCert', 'Aware device (iOS)'), ('kdata.funf.FunfJournal', 'Funf-journal device'), ('kdata.survey.TestSurvey1', 'Test Survey #1'), ('kdata.twitter.Twitter', 'Twitter'), ('kdata.facebook.Facebook', 'Facebook'), ('kdata.instagram.Instagram', 'Instagram')], help_text='What type of device is this?', max_length=128),
        ),
        migrations.AlterField(
            model_name='group',
            name='invite_code',
            field=models.CharField(blank=True, max_length=64),
        ),
        migrations.AlterField(
            model_name='mosquittouser',
            name='username',
            field=models.CharField(max_length=64, unique=True),
        ),
        migrations.AlterField(
            model_name='oauthdevice',
            name='data',
            field=models.CharField(blank=True, max_length=265),
        ),
        migrations.AlterField(
            model_name='oauthdevice',
            name='error',
            field=models.CharField(blank=True, max_length=256),
        ),
        migrations.AlterField(
            model_name='oauthdevice',
            name='refresh_token',
            field=models.CharField(blank=True, max_length=256),
        ),
        migrations.AlterField(
            model_name='oauthdevice',
            name='request_key',
            field=models.CharField(blank=True, db_index=True, max_length=256),
        ),
        migrations.AlterField(
            model_name='oauthdevice',
            name='request_secret',
            field=models.CharField(blank=True, max_length=256),
        ),
        migrations.AlterField(
            model_name='oauthdevice',
            name='resource_key',
            field=models.CharField(blank=True, max_length=256),
        ),
        migrations.AlterField(
            model_name='oauthdevice',
            name='resource_secret',
            field=models.CharField(blank=True, max_length=256),
        ),
        migrations.AlterField(
            model_name='oauthdevice',
            name='service',
            field=models.CharField(blank=True, max_length=64),
        ),
        migrations.AlterField(
            model_name='oauthdevice',
            name='state',
            field=models.CharField(blank=True, max_length=16),
        ),
        migrations.AlterField(
            model_name='oauthdevice',
            name='ts_linked',
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
