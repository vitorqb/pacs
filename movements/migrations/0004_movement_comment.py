# Generated by Django 2.2.2 on 2020-04-13 15:38

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('movements', '0003_auto_20190818_0913'),
    ]

    operations = [
        migrations.AddField(
            model_name='movement',
            name='comment',
            field=models.CharField(blank=True, max_length=500, null=True),
        ),
    ]
