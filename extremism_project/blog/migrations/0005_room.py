# Generated by Django 4.2.7 on 2023-11-07 16:13

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('blog', '0004_remove_comment_create_at_comment_created_at'),
    ]

    operations = [
        migrations.CreateModel(
            name='Room',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=255)),
                ('slug', models.SlugField()),
                ('user_1', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='user1_rooms', to=settings.AUTH_USER_MODEL)),
                ('user_2', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='user2_rooms', to=settings.AUTH_USER_MODEL)),
            ],
        ),
    ]
