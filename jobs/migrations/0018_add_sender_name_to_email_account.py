# Generated migration for adding sender_name field to EmailAccount

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('jobs', '0017_fix_contact_group_fields'),
    ]

    operations = [
        migrations.AddField(
            model_name='emailaccount',
            name='sender_name',
            field=models.CharField(blank=True, default='', help_text='邮件中显示的发件人姓名，如：张三 <zhang@example.com>', max_length=255, verbose_name='发件人姓名'),
        ),
    ]