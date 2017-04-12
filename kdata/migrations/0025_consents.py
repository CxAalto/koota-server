# -*- coding: utf-8 -*-
# Generated by Django 1.10 on 2017-01-16 20:33
from __future__ import unicode_literals

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import kdata.util


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('kdata', '0024_attrs_4096'),
    ]

    operations = [
        migrations.CreateModel(
            name='Consent',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('ts_create', models.DateTimeField(auto_now_add=True)),
                ('data', kdata.util.JsonConfigField(blank=True, help_text='Context data about what this consent means.')),
                ('text', models.TextField(blank=True, null=True)),
                ('sha256', models.TextField(blank=True, null=True)),
                ('group', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='kdata.Group')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
        ),
    ]