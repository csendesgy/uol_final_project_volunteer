from django.test import TestCase

# Create your tests here.
import json
import datetime
import asyncio
import string
from django.test import TestCase, TransactionTestCase, Client
from django.urls import reverse
from django.utils import timezone
from ossvolsite.asgi import application 
from django.contrib.auth.models import User
from ossvolapp.models import *
import factory

class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = User
    username = factory.Sequence(lambda n: f'user{n}')
    email = factory.LazyAttribute(lambda obj: f'{obj.username}@example.com')
    password = factory.PostGenerationMethodCall('set_password', 'password')

class AuthUserExtensionFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = AuthUserExtension
    user = factory.SubFactory(UserFactory)
    is_org = False


class LanguageFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Language
    language = factory.Sequence(lambda n: f'Language {n}')

class LanguageLevelFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = LanguageLevel
    languages_level = "Beginner"

class SkillFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Skill
    skill_name = factory.Sequence(lambda n: f'Skill {n}')

class ProfilesOrgFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = ProfilesOrg
    user = factory.SubFactory(UserFactory)
    org_name = factory.Sequence(lambda n: f'Org {n}')
    org_web = "http://example.com"
    org_tel = "1234567890"
    introduction = "An organization profile"
    site_admin_validated = 'Y'
    site_admin_approved = 'Y'

class ProfilesVolunteerFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = ProfilesVolunteer
    user = factory.SubFactory(UserFactory)
    birth_year = 1990
    tel = "0987654321"
    job_title = "Volunteer"
    native_language = factory.SubFactory(LanguageFactory)
    introduction = "A volunteer profile"
    accept_recommendation = 'Y'
    visible_to_orgs = 'Y'
    willing_to_translate = 'N'
    willing_to_light_physical = 'N'


class EventFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Event
    event_id = factory.Sequence(lambda n: n+1000)
    profiles_org_id = factory.SubFactory(ProfilesOrgFactory)
    event_name = factory.Sequence(lambda n: f'Event {string.ascii_uppercase[n % 26]}')
    event_zip = 12345
    event_date = timezone.now().date()+ datetime.timedelta(days=3)
    event_description = "An event description"
    application_deadline = timezone.now().date()+ datetime.timedelta(days=3)
    event_image = b''

class EventEnrollmentFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = EventEnrollment
    event_id = factory.SubFactory(EventFactory)
    profiles_vol_id = factory.SubFactory(ProfilesVolunteerFactory)
    applied_at = timezone.now().date()
    record_created_at = timezone.now().date()
    is_accepted = 'Y'

class EventChatFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = EventChat
    event_id = factory.SubFactory(EventFactory)
    
class EventChatHistoryFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = EventChatHistory
    chat_id = factory.SubFactory(EventChatFactory)
    msg = "Test message"
    sent_at = factory.LazyFunction(timezone.now)
    from_org_id = None
    from_vol_id = None

###########################################
# URL Tests                               #
###########################################

class URLTests(TestCase):
    def test_index_url(self):
        """Test that the index URL reverses correctly."""
        url = reverse('index')
        self.assertEqual(url, '/')
    def test_chat_url(self):
        """Test that the base chat URL reverses correctly."""
        url = reverse('chat')
        self.assertEqual(url, '/chat/')
    def test_chat_room_url(self):
        """Test that the chat room URL with room_id reverses correctly."""
        url = reverse('chat_room', kwargs={'room_id': 1})
        self.assertEqual(url, '/chat/1/')

############################################
## View Tests                              #
############################################

class BasicViewTests(TestCase):
    def setUp(self):
        self.client = Client()

    def test_index_view(self):
        """Index view returns 200 and includes expected content."""
        response = self.client.get(reverse('index'))
        self.assertEqual(response.status_code, 200)
        self.assertIn("welcome", response.content.decode().lower())

    def test_notimplemented_view(self):
        """Not implemented view returns expected placeholder text."""
        response = self.client.get(reverse('notimplemented'))
        self.assertEqual(response.status_code, 200)
        self.assertIn("this feature is not yet implemented", response.content.decode().lower())

class AuthViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = UserFactory(username='testuser')
        self.user.set_password('password')
        self.user.save()
        AuthUserExtensionFactory(user=self.user, is_org=False)

    def test_login_success(self):
        """Test that a valid login redirects (status 302)."""
        response = self.client.post(reverse('login'), {'username': 'testuser', 'password': 'password'})
        self.assertEqual(response.status_code, 302)
        self.assertTrue('_auth_user_id' in self.client.session)

    def test_logout_view(self):
        """Test that logout clears the session and redirects."""
        self.client.login(username='testuser', password='password')
        response = self.client.get(reverse('logout'))
        self.assertEqual(response.status_code, 302)
        self.assertNotIn('_auth_user_id', self.client.session)

    def tearDown(self):
        EventChatHistory.objects.all().delete()
        EventChat.objects.all().delete()
        Recommendation.objects.all().delete()
        EventEnrollment.objects.all().delete()
        EventTranslateLanguage.objects.all().delete()
        EventSkill.objects.all().delete()
        Event.objects.all().delete()
        VolunteerLanguage.objects.all().delete()
        VolunteerSkill.objects.all().delete()
        ProfilesVolunteer.objects.all().delete()
        ProfilesOrg.objects.all().delete()
        Skill.objects.all().delete()
        LanguageLevel.objects.all().delete()
        Language.objects.all().delete()
        AuthUserExtension.objects.all().delete()
        User.objects.all().delete()

class HomeViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.vol_user = UserFactory(username='voluser')
        self.vol_user.set_password('password')
        self.vol_user.save()
        AuthUserExtensionFactory(user=self.vol_user, is_org=False)
        self.vol_profile = ProfilesVolunteerFactory(user=self.vol_user)
        self.client.login(username='voluser', password='password')

    def test_home_view_volunteer(self):
        """Home view for a volunteer should return expected content."""
        response = self.client.get(reverse('home'))
        self.assertEqual(response.status_code, 200)
        self.assertIn("recommendations", response.content.decode().lower())

    def tearDown(self):
        EventChatHistory.objects.all().delete()
        EventChat.objects.all().delete()
        Recommendation.objects.all().delete()
        EventEnrollment.objects.all().delete()
        EventTranslateLanguage.objects.all().delete()
        EventSkill.objects.all().delete()
        Event.objects.all().delete()
        VolunteerLanguage.objects.all().delete()
        VolunteerSkill.objects.all().delete()
        ProfilesVolunteer.objects.all().delete()
        ProfilesOrg.objects.all().delete()
        Skill.objects.all().delete()
        LanguageLevel.objects.all().delete()
        Language.objects.all().delete()
        AuthUserExtension.objects.all().delete()
        User.objects.all().delete()
        
class EventsViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.org_user = UserFactory(username='orgedit')
        self.org_user.set_password('password')
        self.org_user.save()
        self.org_profile = ProfilesOrgFactory(user=self.org_user)
        AuthUserExtensionFactory(user=self.org_user, is_org=True)
        self.client.login(username='orgedit', password='password')
        self.event = EventFactory(profiles_org_id=self.org_profile)
        self.event.save()
        self.event_chat = EventChatFactory(event_id=self.event)
        
    def test_events_view_org(self):
        """Events view for an organization should display event details including chat_id."""
        response = self.client.get(reverse('events'))
        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        self.assertIn(self.event.event_name, content)
        self.assertIn(str(self.event_chat.chat_id), content)
    
    def tearDown(self):
        EventChatHistory.objects.all().delete()
        EventChat.objects.all().delete()
        Recommendation.objects.all().delete()
        EventEnrollment.objects.all().delete()
        EventTranslateLanguage.objects.all().delete()
        EventSkill.objects.all().delete()
        Event.objects.all().delete()
        VolunteerLanguage.objects.all().delete()
        VolunteerSkill.objects.all().delete()
        ProfilesVolunteer.objects.all().delete()
        ProfilesOrg.objects.all().delete()
        Skill.objects.all().delete()
        LanguageLevel.objects.all().delete()
        Language.objects.all().delete()
        AuthUserExtension.objects.all().delete()
        User.objects.all().delete()

class CreateEditEventTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.org_user = UserFactory(username='orgedit')
        self.org_user.set_password('password')
        self.org_user.save()
        self.org_profile = ProfilesOrgFactory(user=self.org_user)
        AuthUserExtensionFactory(user=self.org_user, is_org=True)
        self.client.login(username='orgedit', password='password')
        self.event = EventFactory(profiles_org_id=self.org_profile)
        self.event_chat = EventChatFactory(event_id=self.event)


    def test_create_event_get(self):
        """GET request to event maintenance should render the creation form."""
        response = self.client.get(reverse('eventmaint'))
        self.assertEqual(response.status_code, 200)
        self.assertIn("Create New Event", response.content.decode())

    def test_edit_event_post(self):
        """POST request to event maintenance should update the event details."""
        data = {
            'event_id': self.event.event_id,
            'event_name': "Updated Event Name",
            'event_zip': "54321",
            'event_date': self.event.event_date.strftime('%Y-%m-%d'),
            'event_description': "Updated description",
            'application_deadline': self.event.application_deadline.strftime('%Y-%m-%d'),
        }
        
        response = self.client.post(reverse('eventmaint'), data)
        self.assertEqual(response.status_code, 302)

    def tearDown(self):
        EventChatHistory.objects.all().delete()
        EventChat.objects.all().delete()
        Recommendation.objects.all().delete()
        EventEnrollment.objects.all().delete()
        EventTranslateLanguage.objects.all().delete()
        EventSkill.objects.all().delete()
        Event.objects.all().delete()
        VolunteerLanguage.objects.all().delete()
        VolunteerSkill.objects.all().delete()
        ProfilesVolunteer.objects.all().delete()
        ProfilesOrg.objects.all().delete()
        Skill.objects.all().delete()
        LanguageLevel.objects.all().delete()
        Language.objects.all().delete()
        AuthUserExtension.objects.all().delete()
        User.objects.all().delete()

class FindEventTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.event = EventFactory(event_zip=12345)  

    def test_find_event_with_results(self):
        """Find event view should return events when search criteria match."""
        response = self.client.get(reverse('find_event'), {'zip_code': '12345', 'distance': '10'})
        self.assertEqual(response.status_code, 200)
        self.assertIn(self.event.event_name, response.content.decode())

    def test_find_event_no_results(self):
        """Find event view should provide suggestions when no events match."""
        response = self.client.get(reverse('find_event'), {'zip_code': '00000', 'distance': '10'})
        self.assertEqual(response.status_code, 200)
        self.assertIn("No events found", response.content.decode())

    def tearDown(self):
        EventChatHistory.objects.all().delete()
        EventChat.objects.all().delete()
        Recommendation.objects.all().delete()
        EventEnrollment.objects.all().delete()
        EventTranslateLanguage.objects.all().delete()
        EventSkill.objects.all().delete()
        Event.objects.all().delete()
        VolunteerLanguage.objects.all().delete()
        VolunteerSkill.objects.all().delete()
        ProfilesVolunteer.objects.all().delete()
        ProfilesOrg.objects.all().delete()
        Skill.objects.all().delete()
        LanguageLevel.objects.all().delete()
        Language.objects.all().delete()
        AuthUserExtension.objects.all().delete()
        User.objects.all().delete()

class EventRecommendTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.org_user = UserFactory(username='recommendorg')
        self.org_user.set_password('password')
        self.org_user.save()
        self.org_profile = ProfilesOrgFactory(user=self.org_user)
        AuthUserExtensionFactory(user=self.org_user, is_org=True)
        self.client.login(username='recommendorg', password='password')
        self.event = EventFactory(profiles_org_id=self.org_profile)
        self.volunteer = ProfilesVolunteerFactory()

    def test_event_recommend_post(self):
        """Submitting a recommendation should create a Recommendation record."""
        data = {
            'to_vol_id': self.volunteer.profiles_vol_id,
            'recommendation_msg': "Please join our event!"
        }
        response = self.client.post(reverse('eventrecommend', kwargs={'event_id': self.event.event_id}), data)
        self.assertEqual(response.status_code, 302)
        rec_exists = Recommendation.objects.filter(event_id=self.event, to_vol_id=self.volunteer).exists()
        self.assertTrue(rec_exists)

    def tearDown(self):
        EventChatHistory.objects.all().delete()
        EventChat.objects.all().delete()
        Recommendation.objects.all().delete()
        EventEnrollment.objects.all().delete()
        EventTranslateLanguage.objects.all().delete()
        EventSkill.objects.all().delete()
        Event.objects.all().delete()
        VolunteerLanguage.objects.all().delete()
        VolunteerSkill.objects.all().delete()
        ProfilesVolunteer.objects.all().delete()
        ProfilesOrg.objects.all().delete()
        Skill.objects.all().delete()
        LanguageLevel.objects.all().delete()
        Language.objects.all().delete()
        AuthUserExtension.objects.all().delete()
        User.objects.all().delete()

############################################
## API View Tests                          #
############################################

class EventAPITests(TestCase):
    def setUp(self):
        self.client = Client()
        self.api_user = UserFactory(username='apiuser')
        self.api_user.set_password('password')
        self.api_user.save()
        AuthUserExtensionFactory(user=self.api_user, is_org=False)
        self.client.login(username='apiuser', password='password')
        self.event = EventFactory()
    def test_event_api_get(self):
        """API view should return aggregated event data in JSON."""
        url = reverse('event_api', kwargs={'event_id': self.event.event_id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('event_name', data)

