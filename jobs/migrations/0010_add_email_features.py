# Generated by Django 4.2.14 on 2025-07-29 08:30

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('jobs', '0009_add_tracking_fields_to_emaillog'),
    ]

    operations = [
        # 1. Add new fields to EmailAccount model
        migrations.AddField(
            model_name='emailaccount',
            name='daily_send_limit',
            field=models.PositiveIntegerField(default=200, verbose_name='每日发送上限'),
        ),
        migrations.AddField(
            model_name='emailaccount',
            name='imap_host',
            field=models.CharField(blank=True, max_length=255, null=True, verbose_name='IMAP服务器'),
        ),
        migrations.AddField(
            model_name='emailaccount',
            name='imap_port',
            field=models.PositiveIntegerField(blank=True, null=True, verbose_name='IMAP端口'),
        ),
        migrations.AddField(
            model_name='emailaccount',
            name='imap_use_ssl',
            field=models.BooleanField(default=True, verbose_name='IMAP使用SSL'),
        ),
        migrations.AddField(
            model_name='emailaccount',
            name='signature',
            field=models.TextField(blank=True, null=True, verbose_name='邮箱签名 (支持HTML)'),
        ),
        # 2. Create the new EmailReply model
        migrations.CreateModel(
            name='EmailReply',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('from_email', models.EmailField(max_length=254, verbose_name='发件人邮箱')),
                ('subject', models.CharField(max_length=255, verbose_name='邮件主题')),
                ('body', models.TextField(verbose_name='邮件正文')),
                ('received_at', models.DateTimeField(verbose_name='收到时间')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('candidate', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='replies', to='jobs.candidate', verbose_name='发件候选人')),
                ('in_reply_to', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='replies', to='jobs.emaillog', verbose_name='回复的邮件')),
                ('to_account', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='replies', to='jobs.emailaccount', verbose_name='收件账户')),
                ('user', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL, verbose_name='处理人')),
            ],
            options={
                'verbose_name': '邮件回复',
                'verbose_name_plural': '邮件回复',
                'ordering': ['-received_at'],
            },
        ),
        # 3. Remove the old UserSignature model
        migrations.DeleteModel(
            name='UserSignature',
        ),
    ]
