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

class Event(models.Model):
    event_id = models.DecimalField(primary_key=True, max_digits=38, decimal_places=0)  
    profiles_org_id = models.ForeignKey('ProfilesOrg', on_delete=models.CASCADE, db_column='profiles_org_id')  
    event_name = models.CharField(max_length=100) 
    event_zip = models.DecimalField(max_digits=5, decimal_places=0) 
    event_date = models.DateField() 
    event_description = models.CharField(max_length=4000)  
    application_deadline = models.DateField() 
    event_image = models.BinaryField()  

    class Meta:
        db_table = 'events'



class EventSkill(models.Model):
    event_id = models.ForeignKey('Event', on_delete=models.CASCADE, db_column='event_id') 
    skill_id = models.ForeignKey('Skill', on_delete=models.CASCADE, db_column='skill_id') 

    class Meta:
        db_table = 'event_skills'
        unique_together = (('event_id', 'skill_id'),) 


class EventTranslateLanguage(models.Model):
    event_id = models.ForeignKey('Event', on_delete=models.CASCADE, db_column='event_id')  
    target_language_id = models.ForeignKey('Language', on_delete=models.CASCADE, db_column='target_language_id')  
    required_language_level_id = models.ForeignKey('LanguageLevel', on_delete=models.CASCADE, db_column='required_language_level_id')  

    class Meta:
        db_table = 'event_translate_language'
        unique_together = (('event_id', 'target_language_id'),)


class EventEnrollment(models.Model):
    event_id = models.ForeignKey('Event', on_delete=models.CASCADE, db_column='event_id') 
    profiles_vol_id = models.ForeignKey('ProfilesVolunteer', on_delete=models.CASCADE, db_column='profiles_vol_id')
    applied_at = models.DateField()  
    is_accepted = models.CharField(max_length=1, null=True, blank=True) 
    accepted_at = models.DateField(null=True, blank=True)  
    is_rejected = models.CharField(max_length=1, null=True, blank=True)
    rejected_at = models.DateField(null=True, blank=True)  
    reject_reason = models.CharField(max_length=1000, null=True, blank=True)  
    record_created_at = models.DateField()  
    last_updated_at = models.DateField(null=True, blank=True)

    class Meta:
        db_table = 'event_enrollment'
        unique_together = ('event_id', 'profiles_vol_id')  

class Recommendation(models.Model):
    recommendation_id = models.BigAutoField(primary_key=True)
    event_id = models.ForeignKey('Event', on_delete=models.CASCADE, db_column='event_id', related_name='recommendations')
    from_org_id = models.ForeignKey('ProfilesOrg', on_delete=models.CASCADE, db_column='from_org_id', null=True, blank=True, related_name='sent_recommendations')
    from_vol_id = models.ForeignKey('ProfilesVolunteer', on_delete=models.CASCADE, db_column='from_vol_id', null=True, blank=True, related_name='vol_sent_recommendations')
    to_vol_id = models.ForeignKey('ProfilesVolunteer', on_delete=models.CASCADE, db_column='to_vol_id', related_name='received_recommendations')
    recommendation_msg = models.CharField(max_length=200, null=True, blank=True)

    class Meta:
        db_table = "recommendations"


class EventChat(models.Model):
    chat_id = models.BigAutoField(primary_key=True)
    event_id = models.ForeignKey('Event', on_delete=models.CASCADE, db_column='event_id', related_name='chats')
    event_chat_name = models.CharField(max_length=100)

    class Meta:
        db_table = "event_chat"


class EventChatHistory(models.Model):
    chat_log_id = models.BigAutoField(primary_key=True)
    chat_id = models.ForeignKey('EventChat', on_delete=models.CASCADE, db_column='chat_id', related_name='chat_logs')
    from_org_id = models.ForeignKey('ProfilesOrg', on_delete=models.CASCADE, db_column='from_org_id', null=True, blank=True, related_name='org_chat_logs')
    from_vol_id = models.ForeignKey('ProfilesVolunteer', on_delete=models.CASCADE, db_column='from_vol_id', null=True, blank=True, related_name='vol_chat_logs')
    msg = models.TextField()
    sent_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "event_chat_history"
