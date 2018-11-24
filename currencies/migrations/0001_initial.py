# Generated by Django 2.1.3 on 2018-11-19 19:35

import common.models
import django.core.validators
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Currency',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', common.models.NameField(max_length=150, unique=True)),
                ('base_price', models.DecimalField(decimal_places=5, max_digits=20, validators=[django.core.validators.MinValueValidator(0, 'Prices must be positive')])),
                ('imutable', models.BooleanField(default=False)),
            ],
        ),
        migrations.CreateModel(
            name='CurrencyPriceChange',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date', models.DateField()),
                ('new_price', models.DecimalField(decimal_places=5, max_digits=20, validators=[django.core.validators.MinValueValidator(0, 'Prices must be positive')])),
                ('currency', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='currencies.Currency')),
            ],
        ),
        migrations.AlterUniqueTogether(
            name='currencypricechange',
            unique_together={('date', 'currency')},
        ),
    ]