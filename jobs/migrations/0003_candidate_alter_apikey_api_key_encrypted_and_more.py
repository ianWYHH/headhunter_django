# Generated by Django 4.2.14 on 2025-07-28 05:54

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('jobs', '0002_apikey'),
    ]

    operations = [
        migrations.CreateModel(
            name='Candidate',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(db_index=True, max_length=255, verbose_name='姓名')),
                ('emails', models.JSONField(blank=True, default=list, verbose_name='邮箱地址 (多个)')),
                ('homepage', models.URLField(blank=True, max_length=255, null=True, verbose_name='个人主页')),
                ('github_profile', models.URLField(blank=True, max_length=255, null=True, verbose_name='GitHub主页')),
                ('linkedin_profile', models.URLField(blank=True, max_length=255, null=True, verbose_name='领英主页')),
                ('external_id', models.BigIntegerField(blank=True, db_index=True, null=True, unique=True, verbose_name='外部系统ID')),
                ('skills', models.JSONField(blank=True, default=list, verbose_name='技能关键字')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='创建时间')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='更新时间')),
            ],
            options={
                'verbose_name': '候选人',
                'verbose_name_plural': '候选人',
                'ordering': ['-updated_at'],
            },
        ),
        migrations.AlterField(
            model_name='apikey',
            name='api_key_encrypted',
            field=models.BinaryField(help_text='加密后的API密钥', verbose_name='加密密钥'),
        ),
        migrations.AlterField(
            model_name='apikey',
            name='created_at',
            field=models.DateTimeField(auto_now_add=True, verbose_name='创建时间'),
        ),
        migrations.AlterField(
            model_name='apikey',
            name='provider',
            field=models.CharField(help_text="服务商的唯一标识, 例如 'qwen', 'kimi'", max_length=100, unique=True, verbose_name='服务商'),
        ),
        migrations.AlterField(
            model_name='apikey',
            name='updated_at',
            field=models.DateTimeField(auto_now=True, verbose_name='更新时间'),
        ),
        migrations.AlterField(
            model_name='company',
            name='created_at',
            field=models.DateTimeField(auto_now_add=True, verbose_name='创建时间'),
        ),
        migrations.AlterField(
            model_name='company',
            name='description',
            field=models.TextField(blank=True, null=True, verbose_name='公司描述'),
        ),
        migrations.AlterField(
            model_name='company',
            name='name',
            field=models.CharField(db_index=True, max_length=255, unique=True, verbose_name='公司名称'),
        ),
        migrations.AlterField(
            model_name='company',
            name='updated_at',
            field=models.DateTimeField(auto_now=True, verbose_name='更新时间'),
        ),
        migrations.AlterField(
            model_name='job',
            name='company',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='jobs', to='jobs.company', verbose_name='公司'),
        ),
        migrations.AlterField(
            model_name='job',
            name='created_at',
            field=models.DateTimeField(auto_now_add=True, verbose_name='创建时间'),
        ),
        migrations.AlterField(
            model_name='job',
            name='department',
            field=models.CharField(blank=True, max_length=255, null=True, verbose_name='所属部门'),
        ),
        migrations.AlterField(
            model_name='job',
            name='job_description',
            field=models.TextField(blank=True, null=True, verbose_name='职位描述'),
        ),
        migrations.AlterField(
            model_name='job',
            name='job_requirement',
            field=models.TextField(blank=True, null=True, verbose_name='职位要求'),
        ),
        migrations.AlterField(
            model_name='job',
            name='keywords',
            field=models.JSONField(blank=True, default=list, verbose_name='关键词'),
        ),
        migrations.AlterField(
            model_name='job',
            name='level_set',
            field=models.JSONField(blank=True, default=list, verbose_name='职级要求'),
        ),
        migrations.AlterField(
            model_name='job',
            name='locations',
            field=models.JSONField(blank=True, default=list, verbose_name='工作地点'),
        ),
        migrations.AlterField(
            model_name='job',
            name='notes',
            field=models.TextField(blank=True, null=True, verbose_name='备注'),
        ),
        migrations.AlterField(
            model_name='job',
            name='salary_range',
            field=models.CharField(blank=True, max_length=100, null=True, verbose_name='薪资范围'),
        ),
        migrations.AlterField(
            model_name='job',
            name='skills',
            field=models.JSONField(blank=True, default=list, verbose_name='核心技能'),
        ),
        migrations.AlterField(
            model_name='job',
            name='status',
            field=models.CharField(choices=[('待处理', '待处理'), ('进行中', '进行中'), ('已关闭', '已关闭'), ('成功', '成功')], db_index=True, default='待处理', max_length=50, verbose_name='职位状态'),
        ),
        migrations.AlterField(
            model_name='job',
            name='title',
            field=models.CharField(db_index=True, max_length=255, verbose_name='职位名称'),
        ),
        migrations.AlterField(
            model_name='job',
            name='updated_at',
            field=models.DateTimeField(auto_now=True, verbose_name='更新时间'),
        ),
    ]
