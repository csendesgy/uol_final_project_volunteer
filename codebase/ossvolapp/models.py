from django.db import models
from django.contrib.auth.models import User

# Extending the User model
class AuthUserExtension(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='extension')
    is_org = models.BooleanField(default=False)
    current_login = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return self.user.username


class Language(models.Model):
    language_id = models.BigAutoField(primary_key=True)
    language = models.CharField(max_length=30)

    class Meta:
        db_table = "languages"


class LanguageLevel(models.Model):
    languages_level_id = models.BigAutoField(primary_key=True)
    languages_level = models.CharField(max_length=30)

    class Meta:
        db_table = "languages_level"


class Skill(models.Model):
    skill_id = models.BigAutoField(primary_key=True)
    skill_name = models.CharField(max_length=100)

    class Meta:
        db_table = "skills"


class ProfilesOrg(models.Model):
    profiles_org_id = models.BigAutoField(primary_key=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    org_name = models.CharField(max_length=500)
    org_web = models.CharField(max_length=200, blank=True, null=True)
    org_tel = models.CharField(max_length=30, blank=True, null=True)
    introduction = models.TextField(blank=True, null=True)
    profile_image_org = models.BinaryField(blank=True, null=True)
    site_admin_validated = models.CharField(max_length=1)
    site_admin_approved = models.CharField(max_length=1)

    class Meta:
        db_table = "profiles_org"


class ProfilesVolunteer(models.Model):
    profiles_vol_id = models.BigAutoField(primary_key=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    birth_year = models.PositiveIntegerField()
    tel = models.CharField(max_length=30, blank=True, null=True)
    job_title = models.CharField(max_length=30, blank=True, null=True)
    native_language = models.ForeignKey(Language, on_delete=models.CASCADE)
    introduction = models.TextField(blank=True, null=True)
    accept_recommendation = models.CharField(max_length=1)
    visible_to_orgs = models.CharField(max_length=1)
    willing_to_translate = models.CharField(max_length=1)
    willing_to_light_physical = models.CharField(max_length=1)
    profile_image_vol = models.BinaryField(blank=True, null=True)

    class Meta:
        db_table = "profiles_volunteer"


class VolunteerSkill(models.Model):
    vol_skill_id = models.BigAutoField(primary_key=True)
    profiles_vol = models.ForeignKey(ProfilesVolunteer, on_delete=models.CASCADE)
    skill = models.ForeignKey(Skill, on_delete=models.CASCADE)

    class Meta:
        db_table = "volunteer_skills"


class VolunteerLanguage(models.Model):
    vol_language_id = models.BigAutoField(primary_key=True)
    profiles_vol = models.ForeignKey(ProfilesVolunteer, on_delete=models.CASCADE)
    language = models.ForeignKey(Language, on_delete=models.CASCADE)
    languages_level = models.ForeignKey(LanguageLevel, on_delete=models.CASCADE)

    class Meta:
        db_table = "volunteer_languages"
