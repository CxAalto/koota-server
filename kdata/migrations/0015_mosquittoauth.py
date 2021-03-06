# -*- coding: utf-8 -*-
# Generated by Django 1.9.1 on 2016-06-12 09:46
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('kdata', '0014_device_attr'),
    ]

    operations = [
        migrations.CreateModel(
            name='MosquittoAcl',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('topic', models.CharField(db_index=True, help_text='mosquitto topic filter, including + and #.', max_length=256)),
                ('rw', models.IntegerField(default=1, help_text='1=ro, 2=rw')),
            ],
        ),
        migrations.CreateModel(
            name='MosquittoUser',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('username', models.CharField(db_index=True, max_length=64)),
                ('_passwd', models.CharField(db_column='passwd', help_text='hashed password', max_length=256)),
                ('superuser', models.BooleanField(default=False, help_text='Is a superuser?')),
            ],
        ),
        migrations.AddField(
            model_name='mosquittoacl',
            name='user',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='kdata.MosquittoUser'),
        ),
    ]
