# Generated by Django 2.1.1 on 2018-09-05 08:49

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('kdata', '0029_groupsubject_attr'),
    ]

    operations = [
        migrations.AlterField(
            model_name='consent',
            name='group',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='kdata.Group'),
        ),
        migrations.AlterField(
            model_name='consent',
            name='user',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterField(
            model_name='device',
            name='label',
            field=models.ForeignKey(blank=True, help_text='How is this device used?  Primary means that you actively use the  device in your life, secondary is used by you sometimes. ', null=True, on_delete=django.db.models.deletion.SET_NULL, to='kdata.DeviceLabel', verbose_name='Usage'),
        ),
        migrations.AlterField(
            model_name='device',
            name='user',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterField(
            model_name='groupresearcher',
            name='group',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='kdata.Group'),
        ),
        migrations.AlterField(
            model_name='groupresearcher',
            name='user',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterField(
            model_name='groupsubject',
            name='group',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='kdata.Group'),
        ),
        migrations.AlterField(
            model_name='groupsubject',
            name='user',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterField(
            model_name='surveytoken',
            name='user',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to=settings.AUTH_USER_MODEL),
        ),
    ]