# Generated by Django 5.0.7 on 2025-01-10 21:52

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ossvolapp', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Event',
            fields=[
                ('event_id', models.DecimalField(decimal_places=0, max_digits=38, primary_key=True, serialize=False)),
                ('event_name', models.CharField(max_length=100)),
                ('event_zip', models.DecimalField(decimal_places=0, max_digits=5)),
                ('event_date', models.DateField()),
                ('event_description', models.CharField(max_length=4000)),
                ('application_deadline', models.DateField()),
                ('event_image', models.BinaryField()),
                ('profiles_org_id', models.ForeignKey(db_column='profiles_org_id', on_delete=django.db.models.deletion.CASCADE, to='ossvolapp.profilesorg')),
            ],
            options={
                'db_table': 'events',
            },
        ),
        migrations.CreateModel(
            name='EventEnrollment',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('applied_at', models.DateField()),
                ('is_accepted', models.CharField(blank=True, max_length=1, null=True)),
                ('accepted_at', models.DateField(blank=True, null=True)),
                ('is_rejected', models.CharField(blank=True, max_length=1, null=True)),
                ('rejected_at', models.DateField(blank=True, null=True)),
                ('reject_reason', models.CharField(blank=True, max_length=1000, null=True)),
                ('record_created_at', models.DateField()),
                ('last_updated_at', models.DateField(blank=True, null=True)),
                ('event_id', models.ForeignKey(db_column='event_id', on_delete=django.db.models.deletion.CASCADE, to='ossvolapp.event')),
                ('profiles_vol_id', models.ForeignKey(db_column='profiles_vol_id', on_delete=django.db.models.deletion.CASCADE, to='ossvolapp.profilesvolunteer')),
            ],
            options={
                'db_table': 'event_enrollment',
                'unique_together': {('event_id', 'profiles_vol_id')},
            },
        ),
        migrations.CreateModel(
            name='EventSkill',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('event_id', models.ForeignKey(db_column='event_id', on_delete=django.db.models.deletion.CASCADE, to='ossvolapp.event')),
                ('skill_id', models.ForeignKey(db_column='skill_id', on_delete=django.db.models.deletion.CASCADE, to='ossvolapp.skill')),
            ],
            options={
                'db_table': 'event_skills',
                'unique_together': {('event_id', 'skill_id')},
            },
        ),
        migrations.CreateModel(
            name='EventTranslateLanguage',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('event_id', models.ForeignKey(db_column='event_id', on_delete=django.db.models.deletion.CASCADE, to='ossvolapp.event')),
                ('required_language_level_id', models.ForeignKey(db_column='required_language_level_id', on_delete=django.db.models.deletion.CASCADE, to='ossvolapp.languagelevel')),
                ('target_language_id', models.ForeignKey(db_column='target_language_id', on_delete=django.db.models.deletion.CASCADE, to='ossvolapp.language')),
            ],
            options={
                'db_table': 'event_translate_language',
                'unique_together': {('event_id', 'target_language_id')},
            },
        ),
    ]
