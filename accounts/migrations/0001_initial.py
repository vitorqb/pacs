# Generated by Django 2.1.3 on 2018-11-19 19:35

import common.models
from django.db import migrations, models
import django.db.models.deletion
import mptt.fields


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Account',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', common.models.NameField(max_length=150, unique=True)),
                ('lft', models.PositiveIntegerField(db_index=True, editable=False)),
                ('rght', models.PositiveIntegerField(db_index=True, editable=False)),
                ('tree_id', models.PositiveIntegerField(db_index=True, editable=False)),
                ('level', models.PositiveIntegerField(db_index=True, editable=False)),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='AccountType',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', common.models.NameField(max_length=150, unique=True)),
                ('children_allowed', models.BooleanField()),
                ('movements_allowed', models.BooleanField()),
                ('new_accounts_allowed', models.BooleanField()),
            ],
        ),
        migrations.AddField(
            model_name='account',
            name='acc_type',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='accounts.AccountType'),
        ),
        migrations.AddField(
            model_name='account',
            name='parent',
            field=mptt.fields.TreeForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='children', to='accounts.Account'),
        ),
    ]
