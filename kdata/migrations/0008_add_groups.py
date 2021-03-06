# -*- coding: utf-8 -*-
# Generated by Django 1.9.1 on 2016-03-16 09:15
from __future__ import unicode_literals

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('kdata', '0007_auto_20160307_0105_squashed_0011_auto_20160309_1223'),
    ]

    operations = [
        migrations.CreateModel(
            name='Group',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('slug', models.CharField(max_length=64, unique=True)),
                ('name', models.CharField(max_length=64)),
                ('desc', models.CharField(max_length=64)),
                ('active', models.BooleanField(default=True)),
                ('pyclass', models.CharField(blank=True, max_length=128, null=True)),
                ('pyclass_data', models.CharField(blank=True, max_length=256, null=True)),
                ('url', models.CharField(blank=True, max_length=256, null=True)),
                ('ts_start', models.DateTimeField(blank=True, null=True)),
                ('ts_end', models.DateTimeField(blank=True, null=True)),
                ('invite_code', models.CharField(max_length=64)),
                ('otp_required', models.BooleanField(default=False, help_text='Require OTP auth for researchers?')),
            ],
        ),
        migrations.CreateModel(
            name='GroupResearcher',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('active', models.BooleanField(default=True)),
                ('ts_start', models.DateTimeField(blank=True, null=True)),
                ('ts_end', models.DateTimeField(blank=True, null=True)),
                ('group', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='kdata.Group')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='GroupSubject',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('active', models.BooleanField(default=True)),
                ('ts_start', models.DateTimeField(blank=True, null=True)),
                ('ts_end', models.DateTimeField(blank=True, null=True)),
                ('group', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='kdata.Group')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.AlterField(
            model_name='device',
            name='type',
            field=models.CharField(choices=[('Android', 'Android'), ('PurpleRobot', 'Purple Robot (Android)'), ('Ios', 'IOS'), ('MurataBSN', 'Murata Bed Sensor'), ('kdata.survey.TestSurvey1', 'TestSurvey1')], help_text='What type of device is this?', max_length=128),
        ),
        migrations.AddField(
            model_name='group',
            name='researchers',
            field=models.ManyToManyField(related_name='researcher_of_groups', through='kdata.GroupResearcher', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='group',
            name='subjects',
            field=models.ManyToManyField(related_name='subject_of_groups', through='kdata.GroupSubject', to=settings.AUTH_USER_MODEL),
        ),
    ]
