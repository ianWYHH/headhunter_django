# Generated by Django 4.2.14 on 2025-07-29 01:13

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('jobs', '0006_apikey_user_candidate_user_candidategroup_user_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='emaillog',
            name='status',
            field=models.CharField(choices=[('成功', '成功'), ('失败', '失败'), ('待发送', '待发送'), ('已取消', '已取消')], default='待发送', max_length=50, verbose_name='发送状态'),
        ),
    ]
