# Generated by Django 3.1.3 on 2020-12-05 05:12

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('sync', '0007_auto_20201205_0509'),
    ]

    operations = [
        migrations.AddField(
            model_name='source',
            name='source_acodec',
            field=models.CharField(choices=[('M4A', 'M4A'), ('OPUS', 'OPUS')], db_index=True, default='OPUS', help_text='Source audio codec, desired audio encoding format to download', max_length=8, verbose_name='source audio codec'),
        ),
        migrations.AlterField(
            model_name='source',
            name='source_vcodec',
            field=models.CharField(choices=[('AVC1', 'AVC1 (H.264)'), ('VP9', 'VP9')], db_index=True, default='VP9', help_text='Source video codec, desired video encoding format to download', max_length=8, verbose_name='source video codec'),
        ),
    ]
