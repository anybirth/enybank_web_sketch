# Generated by Django 2.0.6 on 2018-08-02 16:13

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0002_auto_20180801_1704'),
    ]

    operations = [
        migrations.AlterField(
            model_name='user',
            name='hopes_newsletters',
            field=models.BooleanField(default=True, verbose_name='配信希望'),
        ),
    ]
