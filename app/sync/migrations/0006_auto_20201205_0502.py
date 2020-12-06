# Generated by Django 3.1.3 on 2020-12-05 05:02

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('sync', '0005_auto_20201205_0411'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='source',
            name='output_format',
        ),
        migrations.RemoveField(
            model_name='source',
            name='source_profile',
        ),
        migrations.AddField(
            model_name='source',
            name='source_resolution',
            field=models.CharField(choices=[('360p', '360p (SD)'), ('480p', '480p (SD)'), ('720p', '720p (HD)'), ('1080p', '1080p (Full HD)'), ('2160p', '2160p (4K)'), ('audio', 'Audio only')], db_index=True, default='1080p', help_text='Source resolution, desired video resolution to download', max_length=8, verbose_name='source resolution'),
        ),
        migrations.AddField(
            model_name='source',
            name='source_vcodec',
            field=models.CharField(choices=[('M4A', 'M4A'), ('OPUS', 'OPUS'), ('AAC', 'AAC')], db_index=True, default='OPUS', help_text='Source audio codec, desired audio encoding format to download', max_length=8, verbose_name='source audio codec'),
        ),
        migrations.AlterField(
            model_name='source',
            name='prefer_60fps',
            field=models.BooleanField(default=True, help_text='Where possible, prefer 60fps media for this source', verbose_name='prefer 60fps'),
        ),
    ]
