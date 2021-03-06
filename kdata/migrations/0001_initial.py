# -*- coding: utf-8 -*-
# Generated by Django 1.9.1 on 2016-01-23 22:12
from __future__ import unicode_literals

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Data',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('device_id', models.CharField(max_length=64)),
                ('ts', models.DateTimeField(auto_now_add=True)),
                ('ip', models.GenericIPAddressField()),
                ('data', models.TextField(blank=True)),
            ],
        ),
        migrations.CreateModel(
            name='Device',
            fields=[
                ('name', models.CharField(help_text='Give your device a name', max_length=64)),
                ('type', models.CharField(choices=[('Android', 'Android'), ('PurpleRobot', 'Purple Robot (Android)'), ('Ios', 'IOS'), ('MurataBSN', 'Murata Bed Sensor')], help_text='What type of device is this', max_length=32)),
                ('device_id', models.CharField(max_length=64, primary_key=True, serialize=False)),
                ('active', models.BooleanField(default=True)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.AlterIndexTogether(
            name='data',
            index_together=set([('device_id', 'ts')]),
        ),
    ]
