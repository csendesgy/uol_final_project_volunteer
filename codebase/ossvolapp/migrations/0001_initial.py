# Generated by Django 5.0.7 on 2024-12-30 19:34

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Language',
            fields=[
                ('language_id', models.BigAutoField(primary_key=True, serialize=False)),
                ('language', models.CharField(max_length=30)),
            ],
            options={
                'db_table': 'languages',
            },
        ),
        migrations.CreateModel(
            name='LanguageLevel',
            fields=[
                ('languages_level_id', models.BigAutoField(primary_key=True, serialize=False)),
                ('languages_level', models.CharField(max_length=30)),
            ],
            options={
                'db_table': 'languages_level',
            },
        ),
        migrations.CreateModel(
            name='Skill',
            fields=[
                ('skill_id', models.BigAutoField(primary_key=True, serialize=False)),
                ('skill_name', models.CharField(max_length=100)),
            ],
            options={
                'db_table': 'skills',
            },
        ),
        migrations.CreateModel(
            name='AuthUserExtension',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('is_org', models.BooleanField(default=False)),
                ('current_login', models.DateTimeField(blank=True, null=True)),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='extension', to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='ProfilesOrg',
            fields=[
                ('profiles_org_id', models.BigAutoField(primary_key=True, serialize=False)),
                ('org_name', models.CharField(max_length=500)),
                ('org_web', models.CharField(blank=True, max_length=200, null=True)),
                ('org_tel', models.CharField(blank=True, max_length=30, null=True)),
                ('introduction', models.TextField(blank=True, null=True)),
                ('profile_image_org', models.BinaryField(blank=True, null=True)),
                ('site_admin_validated', models.CharField(max_length=1)),
                ('site_admin_approved', models.CharField(max_length=1)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'db_table': 'profiles_org',
            },
        ),
        migrations.CreateModel(
            name='ProfilesVolunteer',
            fields=[
                ('profiles_vol_id', models.BigAutoField(primary_key=True, serialize=False)),
                ('birth_year', models.PositiveIntegerField()),
                ('tel', models.CharField(blank=True, max_length=30, null=True)),
                ('job_title', models.CharField(blank=True, max_length=30, null=True)),
                ('introduction', models.TextField(blank=True, null=True)),
                ('accept_recommendation', models.CharField(max_length=1)),
                ('visible_to_orgs', models.CharField(max_length=1)),
                ('willing_to_translate', models.CharField(max_length=1)),
                ('willing_to_light_physical', models.CharField(max_length=1)),
                ('profile_image_vol', models.BinaryField(blank=True, null=True)),
                ('native_language', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='ossvolapp.language')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'db_table': 'profiles_volunteer',
            },
        ),
        migrations.CreateModel(
            name='VolunteerLanguage',
            fields=[
                ('vol_language_id', models.BigAutoField(primary_key=True, serialize=False)),
                ('language', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='ossvolapp.language')),
                ('languages_level', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='ossvolapp.languagelevel')),
                ('profiles_vol', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='ossvolapp.profilesvolunteer')),
            ],
            options={
                'db_table': 'volunteer_languages',
            },
        ),
        migrations.CreateModel(
            name='VolunteerSkill',
            fields=[
                ('vol_skill_id', models.BigAutoField(primary_key=True, serialize=False)),
                ('profiles_vol', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='ossvolapp.profilesvolunteer')),
                ('skill', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='ossvolapp.skill')),
            ],
            options={
                'db_table': 'volunteer_skills',
            },
        ),
    ]
