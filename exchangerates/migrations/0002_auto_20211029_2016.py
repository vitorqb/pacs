# Generated by Django 3.0.6 on 2021-10-29 20:16

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('exchangerates', '0001_initial'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='exchangerate',
            unique_together={('currency_code', 'date')},
        ),
    ]
