# Generated by Django 3.1.3 on 2020-12-05 05:09

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('sync', '0006_auto_20201205_0502'),
    ]

    operations = [
        migrations.AlterField(
            model_name='source',
            name='source_vcodec',
            field=models.CharField(choices=[('M4A', 'M4A'), ('OPUS', 'OPUS')], db_index=True, default='OPUS', help_text='Source audio codec, desired audio encoding format to download', max_length=8, verbose_name='source audio codec'),
        ),
    ]
