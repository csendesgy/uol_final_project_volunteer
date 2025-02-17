from django.shortcuts import render, redirect, get_object_or_404
from django.conf import settings
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib.auth.hashers import make_password
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.db import transaction, connection
from django.db.models.functions import Upper
from django.db.models import Q
from .models import *
import base64
import cx_Oracle
import pgeocode
import datetime


def index_view(request):
    # Fetch up to 3 random upcoming events
    random_events = Event.objects.filter(
            event_date__gte=datetime.date.today()
        ).order_by('?')[:6]

    # Process event images
    for event in random_events:
        if event.event_image:
            event.event_image = base64.b64encode(event.event_image).decode('utf-8')
        else:
            event.event_image = None

    return render(request, 'index.html', { # Public landing page
        'random_events': random_events,
    })


def notimp_view(request):
    return render(request, 'notimplemented.html')  # Function not implemented

def login_view(request):
    if request.method == "POST":
        username = request.POST.get('username')
        password = request.POST.get('password')

        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect('home')  # Redirect to the dedicated home page
        else:
            messages.error(request, "Invalid username or password.")
    
    return render(request, 'login.html')

def home_view(request):
    if not request.user.is_authenticated:  # Redirect unauthenticated users to index.html
        return redirect('index')

    user = request.user

    # Check if the user is a volunteer
    is_volunteer = ProfilesVolunteer.objects.filter(user=user).exists()

    recommendations = []
    enrolled_events = []
    random_events = []

    if is_volunteer:
        # Fetch the volunteer profile
        volunteer = ProfilesVolunteer.objects.get(user=user)

        # Fetch recommendations for the volunteer that are not yet applied
        recommendations = Recommendation.objects.filter(
            to_vol_id=volunteer.profiles_vol_id
        ).exclude(
            event_id__in=EventEnrollment.objects.filter(profiles_vol_id=volunteer.profiles_vol_id).values_list('event_id', flat=True)
        ).select_related('event_id', 'event_id__profiles_org_id')

        # Process event images
        for rec in recommendations:
            if rec.event_id.event_image:
                rec.event_id.event_image = base64.b64encode(rec.event_id.event_image).decode('utf-8')
            else:
                rec.event_id.event_image = None

        # Prepare recommendations data
        recommendations = [{
            'event_id': rec.event_id.event_id,
            'event_name': rec.event_id.event_name,
            'org_name': rec.event_id.profiles_org_id.org_name,
            'event_date': rec.event_id.event_date,
            'event_zip': rec.event_id.event_zip,
            'event_description': rec.event_id.event_description,
            'recommendation_msg': rec.recommendation_msg,
            'event_image': rec.event_id.event_image,  # Use processed event_image
        } for rec in recommendations]

        # Fetch up to 3 enrolled events closest to today
        enrolled_events = Event.objects.filter(
            eventenrollment__profiles_vol_id=volunteer.profiles_vol_id,
            event_date__gte=datetime.date.today()
        ).order_by('event_date')[:3]

        for event in enrolled_events:
            if event.event_image:
                event.event_image = base64.b64encode(event.event_image).decode('utf-8')
            else:
                event.event_image = None

        # Fetch up to 3 random events the user is not enrolled in or recommended to
        random_events = Event.objects.exclude(
            eventenrollment__profiles_vol_id=volunteer.profiles_vol_id
        ).exclude(
            recommendations__to_vol_id=volunteer.profiles_vol_id  # Corrected here
        ).filter(
            event_date__gte=datetime.date.today()
        ).order_by('?')[:3]

        for event in random_events:
            if event.event_image:
                event.event_image = base64.b64encode(event.event_image).decode('utf-8')
            else:
                event.event_image = None

    return render(request, 'home.html', {
        'is_volunteer': is_volunteer,
        'recommendations': recommendations,
        'enrolled_events': enrolled_events,
        'random_events': random_events,
    })



def logout_view(request):
    logout(request)  # Logs out the user
    messages.success(request, "You have been successfully logged out.")
    return redirect('index')  # Redirect to the index page

#Init capitals
def capitalize_words(text):
    return ' '.join(word.capitalize() for word in text.split())

def register_view(request):
    if request.method == 'GET':
        languages = Language.objects.all()
        language_levels = LanguageLevel.objects.all()
        skills = Skill.objects.all()
        return render(request, 'register.html', {
            'languages': languages,
            'language_levels': language_levels,
            'skills': skills,
        })
    elif request.method == 'POST':
        user_type = request.POST.get('user_type')

        if user_type == 'organization':
            username = request.POST.get('username')
            email = request.POST.get('org_email')
            password = request.POST.get('password')
            org_name = request.POST.get('org_name')
            org_web = request.POST.get('org_web', '')
            org_tel = request.POST.get('org_phone', '')
            introduction = request.POST.get('org_introduction', '')
            profile_image = request.FILES.get('profile_image_org')
            try:
                with transaction.atomic():
                    # Create a new user in auth_user
                    user = User.objects.create(
                        username=username,
                        email=email,
                        password=make_password(password),
                        is_active=True,
                        is_staff=False
                    )
                    
                    # Create the AuthUserExtension
                    AuthUserExtension.objects.create(
                        user=user,
                        is_org=True
                    )
                    user.save()

                    # Create a new profile in profiles_org
                    ProfilesOrg.objects.create(
                        user=user,
                        org_name=org_name,
                        org_web=org_web,
                        org_tel=org_tel,
                        introduction=introduction,
                        profile_image_org=profile_image.read() if profile_image else None, 
                        site_admin_validated='N',
                        site_admin_approved='N'
                    )
                    # Log in the user
                    login(request, user)
                    messages.success(request, "Organization registration successful!")
                    return redirect('home')

            except Exception as e:
                print(f"Error during organization registration: {e}")
                messages.error(request, "There was an error during organization registration. Please try again.")
                #return redirect('register')

        elif user_type == 'volunteer':
            username = request.POST.get('username')
            email = request.POST.get('email')
            password = request.POST.get('password')
            first_name = request.POST.get('first_name')
            last_name = request.POST.get('last_name')
            birth_year = request.POST.get('birth_year')
            native_language_name = request.POST.get('native_language')
            phone = request.POST.get('phone', '')
            job_title = request.POST.get('job_title', '')
            introduction = request.POST.get('vol_introduction', '')
            profile_image = request.FILES.get('profile_image_vol')
            additional_languages = request.POST.getlist('additional_languages[]')  # List of additional languages
            language_levels = request.POST.getlist('language_levels[]')  # Corresponding levels for the additional languages
            skills = request.POST.getlist('skills[]')  # List of skills
            try:
                with transaction.atomic():
                    # Check if the language exists (case-insensitive)
                    native_language = Language.objects.annotate(
                        upper_language=Upper('language')
                    ).filter(upper_language=native_language_name.upper()).first()

                    # If not found, insert the language with properly capitalized words
                    if not native_language:
                        new_language = Language.objects.create(
                            language=capitalize_words(native_language_name)
                        )
                        #query it again
                        native_language = Language.objects.annotate(
                            upper_language=Upper('language')
                        ).filter(upper_language=native_language_name.upper()).first()

                    native_language_id = native_language.language_id

                    # Create a new user in auth_user
                    user = User.objects.create(
                        username=username,
                        email=email,
                        password=make_password(password),
                        first_name=first_name,
                        last_name=last_name,
                        is_active=True,
                        is_staff=False
                    )
                                        
                    # Create the AuthUserExtension
                    AuthUserExtension.objects.create(
                        user=user,
                        is_org=False
                    )
                    user.save()

                    # Create a new profile in profiles_volunteer
                    volunteer_profile = ProfilesVolunteer.objects.create(
                        user=user,
                        birth_year=birth_year,
                        tel=phone,
                        job_title=job_title,
                        native_language_id=native_language_id,
                        introduction=introduction,
                        accept_recommendation='Y',  # Default values, can be updated
                        visible_to_orgs='Y',        # Default values, can be updated
                        willing_to_translate='N',   # Default values, can be updated
                        willing_to_light_physical='N',  # Default values, can be updated
                        profile_image_vol=profile_image.read() if profile_image else None, 
                    )

                    #Process additional languages
                    for language_name, level_id in zip(additional_languages, language_levels):
                        if language_name.strip():  # Ignore empty language names
                            # Handle language
                            language = Language.objects.annotate(
                                upper_language=Upper('language')
                            ).filter(upper_language=language_name.upper()).first()

                        if not language:
                            language = Language.objects.create(
                                language=capitalize_words(language_name)
                            )
                            #query it again
                            language = Language.objects.annotate(
                                upper_language=Upper('language')
                            ).filter(upper_language=language_name.upper()).first()

                        # Handle language level (lookup only)
                        language_level = LanguageLevel.objects.filter(languages_level_id=level_id).first()
                        if not language_level:
                            raise ValueError(f"Invalid language level ID: {level_id}")

                        # Create VolunteerLanguage
                        VolunteerLanguage.objects.create(
                            profiles_vol=volunteer_profile,
                            language=language,
                            languages_level=language_level
                        )

                    # Process skills
                    for skill_name in skills:
                        skill = Skill.objects.annotate(
                            upper_skill=Upper('skill_name')
                        ).filter(upper_skill=skill_name.upper()).first()

                        if not skill:
                            skill = Skill.objects.create(skill_name=capitalize_words(skill_name))
                            skill = Skill.objects.annotate(
                                upper_skill=Upper('skill_name')
                            ).filter(upper_skill=skill_name.upper()).first()

                        # Create VolunteerSkill
                        VolunteerSkill.objects.create(
                            profiles_vol=volunteer_profile,
                            skill=skill
                        )

                    # Log in the user
                    login(request, user)

                    messages.success(request, "Volunteer registration successful!")
                    return redirect('home')

            except Exception as e:
                print(f"Error during volunteer registration: {e}")
                messages.error(request, "There was an error during volunteer registration. Please try again.")
                return redirect('register')

        else:
            messages.error(request, "Invalid user type selected.")
            return redirect('register')

@login_required
def profile_view(request):
    user = request.user
    is_org = user.extension.is_org  # Determine if the user is an organization or a volunteer
    context = {}
    profile_image_url = None

    if request.method == 'POST':
        try:
            #Debugging
            #print("=== POST Data ===")
            #print(request.POST)
            
            with transaction.atomic():
                if is_org:
                    # Handle organization updates
                    profile = ProfilesOrg.objects.filter(user=user).first()
                    if not profile:
                        messages.error(request, "Organization profile not found.")
                        return redirect('profile')

                    profile.org_web = request.POST.get('org_web', '')
                    profile.org_tel = request.POST.get('org_phone', '')
                    profile.introduction = request.POST.get('org_intro', '')
                    if 'profile_image' in request.FILES:
                        profile.profile_image_org = request.FILES['profile_image'].read()
                    profile.save()

                else:
                    # Handle volunteer updates
                    profile = ProfilesVolunteer.objects.filter(user=user).first()
                    if not profile:
                        messages.error(request, "Volunteer profile not found.")
                        return redirect('profile')

                    user.first_name = request.POST.get('first_name', user.first_name)
                    user.last_name = request.POST.get('last_name', user.last_name)
                    user.email = request.POST.get('email', user.email)
                    user.save()

                    profile.birth_year = request.POST.get('birth_year', profile.birth_year)
                    profile.tel = request.POST.get('phone', profile.tel)
                    profile.job_title = request.POST.get('job_title', profile.job_title)
                    profile.introduction = request.POST.get('intro', profile.introduction)
                    profile.accept_recommendation = 'Y' if request.POST.get('accept_recommendations') else 'N'
                    profile.visible_to_orgs = 'Y' if request.POST.get('visible_to_orgs') else 'N'
                    profile.willing_to_translate = 'Y' if request.POST.get('willing_to_translate') else 'N'
                    profile.willing_to_light_physical = 'Y' if request.POST.get('willing_to_light_physical') else 'N'
                    if 'profile_image' in request.FILES:
                        profile.profile_image_vol = request.FILES['profile_image'].read()

                    # Handle native language update
                    native_language_name = request.POST.get('native_language', '').strip()
                    #print("Native language:", native_language_name)
                    if native_language_name:
                        normalized_language_name = native_language_name.title()
                        native_language, created = Language.objects.get_or_create(
                            language__iexact=normalized_language_name,
                            defaults={'language': normalized_language_name}
                        )
                        profile.native_language = native_language

                    profile.save()

                    # Handle additional languages
                    additional_languages = request.POST.getlist('additional_languages[]')
                    language_levels = request.POST.getlist('language_levels[]')

                    # Existing languages mapped for easy lookup
                    existing_language_entries = {
                        entry.language.language.lower(): entry for entry in
                        VolunteerLanguage.objects.filter(profiles_vol=profile).select_related('language', 'languages_level')
                    }

                    # Track submitted languages
                    submitted_languages = {lang.strip().lower() for lang in request.POST.getlist('existing_languages[]') + additional_languages}

                    # Update or add languages
                    for language_name, level_id in zip(additional_languages, language_levels):
                        if language_name.strip():
                            normalized_language_name = language_name.strip().title()
                            language_level = LanguageLevel.objects.filter(pk=level_id).first()

                            if not language_level:
                                print(f"Skipping invalid level for language {normalized_language_name}")
                                continue

                            if normalized_language_name.lower() in existing_language_entries:
                                # Update existing entry
                                existing_entry = existing_language_entries[normalized_language_name.lower()]
                                existing_entry.languages_level = language_level
                                existing_entry.save()
                                #Debugging
                                #print(f"Updated language: {normalized_language_name} with level {language_level.languages_level}")
                            else:
                                # Add new language
                                language, created = Language.objects.get_or_create(
                                    language__iexact=normalized_language_name,
                                    defaults={'language': normalized_language_name}
                                )
                                VolunteerLanguage.objects.create(
                                    profiles_vol=profile,
                                    language=language,
                                    languages_level=language_level
                                )
                                #Debugging
                                #print(f"Added new language: {normalized_language_name} with level {language_level.languages_level}")
                    # Update levels for existing languages
                    existing_language_levels = request.POST.getlist('existing_language_levels[]')
                    for lang, level_id in zip(request.POST.getlist('existing_languages[]'), existing_language_levels):
                        normalized_language_name = lang.strip().lower()
                        if normalized_language_name in existing_language_entries:
                            existing_entry = existing_language_entries[normalized_language_name]
                            language_level = LanguageLevel.objects.filter(pk=level_id).first()
                            if language_level:
                                existing_entry.languages_level = language_level
                                existing_entry.save()
                                #Debugging
                                #print(f"Updated level for existing language: {lang} to {language_level.languages_level}")

                    # Delete languages not in the submitted list
                    for existing_language, entry in existing_language_entries.items():
                        if existing_language not in submitted_languages:
                            entry.delete()
                            #Debugging
                            #print(f"Deleted language: {existing_language}")

                    # Handle skills
                    new_skills = request.POST.getlist('skills[]')
                    existing_skills = request.POST.getlist('existing_skills[]')
                    #Debugging
                    #print("Submitted new skills:", new_skills)
                    #print("Existing skills:", existing_skills)

                    VolunteerSkill.objects.filter(profiles_vol=profile).exclude(
                        skill__skill_name__in=existing_skills
                    ).delete()

                    for skill_name in new_skills:
                        if skill_name.strip():
                            skill, created = Skill.objects.get_or_create(
                                skill_name__iexact=skill_name.strip(),
                                defaults={'skill_name': skill_name.strip().title()}
                            )
                            VolunteerSkill.objects.get_or_create(
                                profiles_vol=profile,
                                skill=skill
                            )

                messages.success(request, "Profile updated successfully!")
                return redirect('profile')

        except Exception as e:
            print("Error during profile update:", e)
            messages.error(request, f"An error occurred: {e}")
            return redirect('profile')

    if is_org:
        # Fetch organization profile data
        profile = ProfilesOrg.objects.filter(user=user).first()
        if profile:
            profile_image_url = (
                f"data:image/png;base64,{base64.b64encode(profile.profile_image_org).decode('utf-8')}" 
                if profile.profile_image_org else None
            )

            # Determine organization profile status
            if profile.site_admin_validated == 'Y' and profile.site_admin_approved == 'Y':
                org_status = "Profile Approved"
            elif profile.site_admin_validated == 'N' and profile.site_admin_approved == 'N':
                org_status = "Profile Not Yet Validated"
            else:
                org_status = "Profile Rejected"

            context = {
                'is_org': True,
                'profile_image_url': profile_image_url,
                'org_name': profile.org_name,
                'org_email': user.email,
                'org_web': profile.org_web,
                'org_phone': profile.org_tel,
                'org_intro': profile.introduction,
                'org_status': org_status,
            }

    else:
        # Fetch volunteer profile data
        profile = ProfilesVolunteer.objects.filter(user=user).first()
        if profile:
            profile_image_url = (
                f"data:image/png;base64,{base64.b64encode(profile.profile_image_vol).decode('utf-8')}" 
                if profile.profile_image_vol else None
            )
            volunteer_languages = profile.volunteerlanguage_set.select_related('language', 'languages_level').all()
            volunteer_skills = profile.volunteerskill_set.select_related('skill').all()

            #Debugging
            #print("Fetched volunteer languages:", list(volunteer_languages))
            #print("Fetched volunteer skills:", list(volunteer_skills))

            context = {
                'is_org': False,
                'profile_image_url': profile_image_url,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'native_language': profile.native_language.language if profile.native_language else '',
                'email': user.email,
                'birth_year': profile.birth_year,
                'phone': profile.tel,
                'job_title': profile.job_title,
                'intro': profile.introduction,
                'accept_recommendation': profile.accept_recommendation,
                'visible_to_orgs': profile.visible_to_orgs,
                'willing_to_translate': profile.willing_to_translate,
                'willing_to_light_physical': profile.willing_to_light_physical,
                'volunteer_languages': [
                    {
                        'language': lang.language.language,
                        'level': lang.languages_level.languages_level
                    }
                    for lang in volunteer_languages
                ],
                'volunteer_skills': [
                    {
                        'skill_name': skill.skill.skill_name
                    }
                    for skill in volunteer_skills
                ],
                'languages': Language.objects.all(),
                'language_levels': LanguageLevel.objects.all(),
            }

    return render(request, 'profile.html', context)

@login_required
def orgapproval_view(request):
    if not request.user.is_superuser or not request.user.is_active:
        return redirect('home')

    if request.method == 'POST':
        profiles_org_id = request.POST.get('profiles_org_id')
        action = request.POST.get('action')

        if profiles_org_id and action:
            try:
                org = ProfilesOrg.objects.get(profiles_org_id=profiles_org_id)
                if action == "approve":
                    org.site_admin_approved = 'Y'
                    org.site_admin_validated = 'Y'
                elif action == "reject":
                    org.site_admin_approved = 'N'
                    org.site_admin_validated = 'Y'
                elif action == "revalidate":
                    org.site_admin_approved = 'N'
                    org.site_admin_validated = 'N'
                org.save()
            except ProfilesOrg.DoesNotExist:
                pass

    approved_orgs = ProfilesOrg.objects.filter(site_admin_approved='Y')
    rejected_orgs = ProfilesOrg.objects.filter(site_admin_approved='N', site_admin_validated='Y')
    to_be_validated_orgs = ProfilesOrg.objects.filter(site_admin_approved='N', site_admin_validated='N')

    context = {
        'approved_orgs': approved_orgs,
        'rejected_orgs': rejected_orgs,
        'to_be_validated_orgs': to_be_validated_orgs,
    }
    return render(request, 'orgapproval.html', context)


@login_required
def events_view(request):
    user = request.user
    is_org = user.extension.is_org  # Check if the user is an organization
    upcoming_events = []
    past_events = []

    if is_org:
        # Check if the user's organization is approved
        try:
            org_profile = ProfilesOrg.objects.get(user=user)
            show_create_button = org_profile.site_admin_approved == 'Y'
        except ProfilesOrg.DoesNotExist:
            org_profile = None
            show_create_button = False

        if org_profile:
            # Fetch events for the organization
            with connection.cursor() as cursor:
                # Query for upcoming events
                cursor.execute("""
                    SELECT e.event_id, 
                           e.event_name, 
                           e.event_zip, 
                           e.event_date,
                           (SELECT ec.chat_id FROM event_chat ec WHERE ec.event_id = e.event_id) as chat_id,
                           count(ee.profiles_vol_id) as pending_approval_cnt
                      FROM events e
                    LEFT JOIN event_enrollment ee
                      on (e.event_id = ee.event_id
                      and nvl(ee.is_rejected,'N') = 'N' 
                      and nvl(ee.is_accepted,'N') = 'N')
                    WHERE TRUNC(e.event_date) >= TRUNC(SYSDATE) 
                      AND profiles_org_id = %s
                GROUP BY e.event_id, e.event_name, e.event_zip, e.event_date                      
                    ORDER BY e.event_date DESC					
                """, [org_profile.profiles_org_id])
                upcoming_events = cursor.fetchall()

                # Query for past events
                cursor.execute("""
                    SELECT e.event_id, 
                           e.event_name, 
                           e.event_zip, 
                           e.event_date, 
                          (SELECT ec.chat_id FROM event_chat ec WHERE ec.event_id = e.event_id) as chat_id
                    FROM events e
                    WHERE TRUNC(e.event_date) < TRUNC(SYSDATE) 
                      AND e.profiles_org_id = %s
                    ORDER BY e.event_date DESC
                """, [org_profile.profiles_org_id])
                past_events = cursor.fetchall()
    else:
        # Fetch volunteer profile
        try:
            volunteer_profile = ProfilesVolunteer.objects.get(user=user)
        except ProfilesVolunteer.DoesNotExist:
            volunteer_profile = None

        if volunteer_profile:
            with connection.cursor() as cursor:
                # Query for upcoming events
                cursor.execute("""
                    SELECT e.event_id, 
                           e.event_name, 
                           e.event_zip, 
                           e.event_date, 
                          (SELECT ec.chat_id FROM event_chat ec WHERE ec.event_id = e.event_id) as chat_id
                    FROM events e
                    JOIN event_enrollment ee ON e.event_id = ee.event_id
                    WHERE TRUNC(e.event_date) >= TRUNC(SYSDATE)
                      AND ee.is_accepted = 'Y'
                      AND ee.profiles_vol_id = %s
                    ORDER BY e.event_date DESC
                """, [volunteer_profile.profiles_vol_id])
                upcoming_events = cursor.fetchall()

                # Query for past events
                cursor.execute("""
                    SELECT e.event_id, 
                           e.event_name, 
                           e.event_zip, 
                           e.event_date, 
                          (SELECT ec.chat_id FROM event_chat ec WHERE ec.event_id = e.event_id) as chat_id
                    FROM events e
                    JOIN event_enrollment ee ON e.event_id = ee.event_id
                    WHERE TRUNC(e.event_date) < TRUNC(SYSDATE)
                      AND ee.is_accepted = 'Y'
                      AND ee.profiles_vol_id = %s
                    ORDER BY e.event_date DESC
                """, [volunteer_profile.profiles_vol_id])
                past_events = cursor.fetchall()

        show_create_button = False  # Volunteers cannot create events

    context = {
        'is_org': is_org,
        'show_create_button': show_create_button,
        'upcoming_events': upcoming_events,
        'past_events': past_events,
    }
    return render(request, 'events.html', context)

@login_required
def create_edit_event(request):
    user = request.user

    if not user.extension.is_org:
        messages.error(request, "Only organizations can create or edit events.")
        return redirect('events')

    org_profile = ProfilesOrg.objects.filter(user=user).first()
    if not org_profile:
        messages.error(request, "Organization profile not found.")
        return redirect('events')

    event_id = request.POST.get('event_id') or request.GET.get('event_id')
    is_edit = bool(event_id)

    # Database connection details
    dsn = settings.DATABASES['default']['NAME']
    username = settings.DATABASES['default']['USER']
    password = settings.DATABASES['default']['PASSWORD']

    event_data = None
    skills = []
    languages = []
    event_image_data = None

    try:
        with cx_Oracle.connect(user=username, password=password, dsn=dsn) as connection:
            with connection.cursor() as cursor:
                if is_edit:
                    # Fetch event details for editing
                    fetch_event_query = """
                        SELECT event_name, event_zip, event_date, event_description, application_deadline
                        FROM events
                        WHERE event_id = :1 AND profiles_org_id = :2
                    """
                    cursor.execute(fetch_event_query, [event_id, org_profile.profiles_org_id])
                    row = cursor.fetchone()
                    if row:
                        event_data = {
                            'event_name': row[0],
                            'event_zip': row[1],
                            'event_date': row[2],
                            'event_description': row[3],
                            'application_deadline': row[4],
                        }
                    else:
                        messages.error(request, "Event not found or you do not have permission to edit it.")
                        return redirect('events')
                    # get the image
                    fetch_image_query = """
                            SELECT event_image
                            FROM events
                            WHERE event_id = :1
                        """
                    cursor.execute(fetch_image_query, [event_id])
                    image_row = cursor.fetchone()
                    if image_row and image_row[0]:
                        event_image_data = base64.b64encode(image_row[0].read()).decode()

                    # Fetch associated skills
                    fetch_skills_query = """
                        SELECT s.skill_name
                        FROM event_skills es
                        JOIN skills s ON es.skill_id = s.skill_id
                        WHERE es.event_id = :1
                    """
                    cursor.execute(fetch_skills_query, [event_id])
                    skills = [row[0] for row in cursor.fetchall()]

                    # Fetch associated languages
                    fetch_languages_query = """
                        SELECT l.language, ll.languages_level
                        FROM event_translate_language etl
                        JOIN languages l ON etl.target_language_id = l.language_id
                        JOIN languages_level ll ON etl.required_language_level_id = ll.languages_level_id
                        WHERE etl.event_id = :1
                    """
                    cursor.execute(fetch_languages_query, [event_id])
                    languages = [{'language': row[0], 'level': row[1]} for row in cursor.fetchall()]

                if request.method == 'POST':
                    event_image = request.FILES.get('event_image')
                    event_image_data = event_image.read() if event_image else None

                    if is_edit:
                        # Update existing event
                        update_query = """
                            UPDATE events
                            SET event_name = :1,
                                event_zip = :2,
                                event_date = TO_DATE(:3, 'YYYY-MM-DD'),
                                event_description = :4,
                                application_deadline = TO_DATE(:5, 'YYYY-MM-DD'),
                                event_image = :6
                            WHERE event_id = :7 AND profiles_org_id = :8
                        """
                        params = [
                            request.POST.get('event_name'),
                            request.POST.get('event_zip'),
                            request.POST.get('event_date'),
                            request.POST.get('event_description'),
                            request.POST.get('application_deadline'),
                            event_image_data,
                            event_id,
                            org_profile.profiles_org_id,
                        ]
                        cursor.execute(update_query, params)
                    else:
                        # Insert new event
                        insert_query = """
                            INSERT INTO events
                            (event_name, event_zip, event_date, event_description, application_deadline, event_image, profiles_org_id)
                            VALUES (:1, :2, TO_DATE(:3, 'YYYY-MM-DD'), :4, TO_DATE(:5, 'YYYY-MM-DD'), :6, :7)
                        """
                        params = [
                            request.POST.get('event_name'),
                            request.POST.get('event_zip'),
                            request.POST.get('event_date'),
                            request.POST.get('event_description'),
                            request.POST.get('application_deadline'),
                            event_image_data,
                            org_profile.profiles_org_id,
                        ]
                        cursor.execute(insert_query, params)
                        # Fetch the event_id for the new event
                        event_id_query = """
                            SELECT event_id
                            FROM events
                            WHERE profiles_org_id = :1
                              AND event_name = :2
                              AND event_zip = :3
                              AND event_date = TO_DATE(:4, 'YYYY-MM-DD')
                              AND application_deadline = TO_DATE(:5, 'YYYY-MM-DD')
                        """
                        cursor.execute(event_id_query, [
                            org_profile.profiles_org_id,
                            request.POST.get('event_name'),
                            request.POST.get('event_zip'),
                            request.POST.get('event_date'),
                            request.POST.get('application_deadline'),
                        ])
                        event_id = cursor.fetchone()[0]

                        #Add it to the chat
                        insert_chat_query = """
                            INSERT INTO event_chat (event_id) VALUES (:1)
                        """
                        cursor.execute(insert_chat_query, [event_id])

                    connection.commit()

                    # Handle skills
                    new_skills = request.POST.getlist('skills[]')
                    delete_skills_query = """
                        DELETE FROM event_skills WHERE event_id = :1
                    """
                    cursor.execute(delete_skills_query, [event_id])

                    for skill_name in new_skills:
                        skill_query = """
                            SELECT skill_id FROM skills WHERE LOWER(skill_name) = :1
                        """
                        cursor.execute(skill_query, [skill_name.lower()])
                        skill_row = cursor.fetchone()

                        if not skill_row:
                            insert_skill_query = """
                                INSERT INTO skills (skill_name) VALUES (:1) RETURNING skill_id INTO :2
                            """
                            skill_id_var = cursor.var(cx_Oracle.NUMBER)
                            cursor.execute(insert_skill_query, [skill_name.title(), skill_id_var])
                            skill_id = skill_id_var.getvalue()[0]
                        else:
                            skill_id = skill_row[0]

                        insert_event_skill_query = """
                            INSERT INTO event_skills (event_id, skill_id) VALUES (:1, :2)
                        """
                        cursor.execute(insert_event_skill_query, [event_id, skill_id])

                    # Handle languages
                    additional_languages = request.POST.getlist('additional_languages[]')
                    additional_language_levels = request.POST.getlist('language_levels[]')

                    delete_languages_query = """
                        DELETE FROM event_translate_language WHERE event_id = :1
                    """
                    cursor.execute(delete_languages_query, [event_id])

                    for lang_name, level_id in zip(additional_languages, additional_language_levels):
                        lang_query = """
                            SELECT language_id FROM languages WHERE LOWER(language) = :1
                        """
                        cursor.execute(lang_query, [lang_name.lower()])
                        lang_row = cursor.fetchone()

                        if not lang_row:
                            insert_language_query = """
                                INSERT INTO languages (language) VALUES (:1) RETURNING language_id INTO :2
                            """
                            lang_id_var = cursor.var(cx_Oracle.NUMBER)
                            cursor.execute(insert_language_query, [lang_name.title(), lang_id_var])
                            language_id = lang_id_var.getvalue()[0]
                        else:
                            language_id = lang_row[0]

                        insert_event_language_query = """
                            INSERT INTO event_translate_language (event_id, target_language_id, required_language_level_id)
                            VALUES (:1, :2, :3)
                        """
                        cursor.execute(insert_event_language_query, [event_id, language_id, level_id])

                    connection.commit()
                    messages.success(request, f"Event {'updated' if is_edit else 'created'} successfully!")
                    return redirect('events')

    except cx_Oracle.DatabaseError as e:
        print(f"Database error: {e}")
        messages.error(request, "A database error occurred.")
        return redirect('events')

    # Prepare data for rendering the form
    all_skills = Skill.objects.all()
    all_languages = Language.objects.all()

    context = {
        'event_id': event_id,
        'event_name': event_data['event_name'] if event_data else '',
        'event_zip': event_data['event_zip'] if event_data else '',
        'event_date': event_data['event_date'] if event_data else '',
        'event_description': event_data['event_description'] if event_data else '',
        'application_deadline': event_data['application_deadline'] if event_data else '',
        'skills': skills,
        'languages': languages,
        'language_levels': LanguageLevel.objects.all(),
        'all_skills': all_skills,
        'all_languages': all_languages,
        'event_image': event_image_data,
    }

    return render(request, 'create_edit_event.html', context)

def event_page(request, event_id):
    event_data = None
    enrollment_status = None
    user = request.user if request.user.is_authenticated else None
    is_volunteer = user and not user.extension.is_org
    accepted_volunteers = []
    pending_volunteers = []
    rejected_volunteers = []
    org_profile = None 

    try:
        with cx_Oracle.connect(
            user=settings.DATABASES['default']['USER'],
            password=settings.DATABASES['default']['PASSWORD'],
            dsn=settings.DATABASES['default']['NAME'],
        ) as connection:
            with connection.cursor() as cursor:
                # Fetch event details
                cursor.execute("""
                    WITH aggregated_data AS (
                        SELECT
                            e.event_name,
                            e.event_zip,
                            e.event_date,
                            e.event_description,
                            e.application_deadline,
                            o.org_name,
                            LISTAGG(DISTINCT sk.skill_name, '; ') WITHIN GROUP (ORDER BY sk.skill_name) AS skills,
                            LISTAGG(DISTINCT l.language || ' - ' || ll.languages_level, '; ') WITHIN GROUP (ORDER BY l.language) AS languages,
                            e.event_id,
                            COUNT(DISTINCT CASE WHEN er.is_accepted = 'Y' THEN er.profiles_vol_id END) AS no_of_attendees,
                            o.profiles_org_id
                        FROM events e
                        JOIN profiles_org o ON e.profiles_org_id = o.profiles_org_id
                        LEFT JOIN event_skills es ON e.event_id = es.event_id
                        LEFT JOIN skills sk ON es.skill_id = sk.skill_id
                        LEFT JOIN event_translate_language el ON e.event_id = el.event_id
                        LEFT JOIN languages l ON el.target_language_id = l.language_id
                        LEFT JOIN languages_level ll ON el.required_language_level_id = ll.languages_level_id
                        LEFT JOIN event_enrollment er ON (e.event_id = er.event_id AND er.is_accepted = 'Y')
                        WHERE e.event_id = :1
                        GROUP BY
                            e.event_name,
                            e.event_zip,
                            e.event_date,
                            e.event_description,
                            e.application_deadline,
                            o.org_name,
                            e.event_id,
                            o.profiles_org_id
                    )
                    SELECT
                        ad.event_name,
                        ad.event_zip,
                        ad.event_date,
                        ad.event_description,
                        ad.application_deadline,
                        e.event_image,
                        ad.org_name,
                        ad.skills,
                        CASE
                            WHEN ad.languages = ' - ' THEN NULL
                            ELSE ad.languages
                        END AS languages,
                        ad.no_of_attendees,
                        ad.profiles_org_id
                    FROM aggregated_data ad
                    JOIN events e ON ad.event_id = e.event_id
                """, [event_id])
                row = cursor.fetchone()
                if row:
                    # Properly handle the LOB object for event_image
                    event_image = None
                    if row[5]:  # Check if image exists
                        if isinstance(row[5], cx_Oracle.LOB):
                            event_image = base64.b64encode(row[5].read()).decode('utf-8')
                        else:
                            event_image = base64.b64encode(row[5]).decode('utf-8')

                    # Split skills and languages
                    skills = row[7].split('; ') if row[7] else []
                    languages = row[8].split('; ') if row[8] else []

                    event_data = {
                        'event_name': row[0],
                        'event_zip': row[1],
                        'event_date': row[2],
                        'event_description': row[3],
                        'application_deadline': row[4],
                        'event_image': event_image,
                        'organizer_name': row[6],
                        'skills': skills,
                        'languages': languages,
                        'attendees': row[9],
                        'organizer_id': row[10],
                    }
                else:
                    messages.error(request, "Event not found.")
                    return redirect('events')

                # Fetch enrollment details for the organization that created the event
                if user and not is_volunteer and user.extension.is_org:
                    # Fetch the organization profile for the logged-in user
                    org_profile = ProfilesOrg.objects.filter(user=user).first()
                
                #if user and not is_volunteer and user.extension.is_org and row[10] == user.extension.profiles_org_id:
                if org_profile and org_profile.profiles_org_id == row[10]:
                    # Handle POST actions (Accept, Reject, Pending)
                    if request.method == 'POST':
                        action = request.POST.get('action')
                        profiles_vol_id = request.POST.get('profiles_vol_id')
                        reject_reason = request.POST.get('reject_reason', '')
                        profiles_vol_id = int(profiles_vol_id)  # Ensure profiles_vol_id is an integer
                        reject_reason = str(reject_reason.strip().replace("'", "''").replace(";", " "))

                        if action and profiles_vol_id:
                            if action == 'accept':
                                # Update to accept the volunteer
                                cursor.execute("""
                                    UPDATE event_enrollment
                                    SET is_accepted = 'Y',
                                        accepted_at = SYSDATE,
                                        is_rejected = 'N',
                                        rejected_at = NULL,
                                        reject_reason = NULL,
                                        last_updated_at = SYSDATE
                                    WHERE event_id = :1 AND profiles_vol_id = :2
                                """, [event_id, profiles_vol_id])

                            elif action == 'pending':
                                # Update to reset the status to pending
                                cursor.execute("""
                                    UPDATE event_enrollment
                                    SET is_accepted = NULL,
                                        accepted_at = NULL,
                                        is_rejected = NULL,
                                        rejected_at = NULL,
                                        reject_reason = NULL,
                                        last_updated_at = SYSDATE
                                    WHERE event_id = :1 AND profiles_vol_id = :2
                                """, [event_id, profiles_vol_id])

                            elif action == 'reject' and reject_reason.strip():
                                query = f"""
                                        UPDATE event_enrollment
                                        SET is_accepted = NULL,
                                            accepted_at = NULL,
                                            is_rejected = 'Y',
                                            rejected_at = SYSDATE,
                                            reject_reason = '{reject_reason}',
                                            last_updated_at = SYSDATE
                                        WHERE event_id = {event_id} AND profiles_vol_id = {profiles_vol_id}
                                    """
                                # debug
                                # print("Generated SQL Query:")
                                # print(query)
                                cursor.execute(query)

                            # Commit the changes and refresh the page
                            connection.commit()
                            messages.success(request, f"Action '{action}' performed successfully.")
                            return redirect('event_page', event_id=event_id)
                    
                    # Accepted volunteers
                    cursor.execute("""
                        SELECT au.first_name, au.last_name, au.email, et.last_updated_at, et.profiles_vol_id
                        FROM event_enrollment et
                        JOIN profiles_volunteer pv ON et.profiles_vol_id = pv.profiles_vol_id
                        JOIN auth_user au ON pv.user_id = au.id
                        WHERE et.event_id = :1 AND NVL(et.is_accepted, 'N') = 'Y'
                    """, [event_id])
                    accepted_volunteers = cursor.fetchall()

                    # Pending volunteers
                    cursor.execute("""
                        SELECT au.first_name, au.last_name, au.email, et.last_updated_at, et.profiles_vol_id
                        FROM event_enrollment et
                        JOIN profiles_volunteer pv ON et.profiles_vol_id = pv.profiles_vol_id
                        JOIN auth_user au ON pv.user_id = au.id
                        WHERE et.event_id = :1 AND NVL(et.is_accepted, 'N') = 'N' AND NVL(et.is_rejected, 'N') = 'N'
                    """, [event_id])
                    pending_volunteers = cursor.fetchall()

                    # Rejected volunteers
                    cursor.execute("""
                        SELECT au.first_name, au.last_name, au.email, et.rejected_at, et.reject_reason, et.last_updated_at, et.profiles_vol_id
                        FROM event_enrollment et
                        JOIN profiles_volunteer pv ON et.profiles_vol_id = pv.profiles_vol_id
                        JOIN auth_user au ON pv.user_id = au.id
                        WHERE et.event_id = :1 AND NVL(et.is_rejected, 'N') = 'Y'
                    """, [event_id])
                    rejected_volunteers = cursor.fetchall()

                # Check enrollment status if the user is a logged-in volunteer
                if is_volunteer:
                    volunteer_profile = ProfilesVolunteer.objects.filter(user=user).first()
                    if volunteer_profile:
                        cursor.execute("""
                            SELECT is_accepted, is_rejected
                            FROM event_enrollment
                            WHERE event_id = :1 AND profiles_vol_id = :2
                        """, [event_id, volunteer_profile.profiles_vol_id])
                        row = cursor.fetchone()
                        if row:
                            is_accepted, is_rejected = row
                            if is_rejected == 'Y':
                                enrollment_status = 'rejected'
                            elif is_accepted == 'Y':
                                enrollment_status = 'accepted'
                            else:
                                enrollment_status = 'pending'
                        else:
                            enrollment_status = 'not_applied'

            # Handle Apply button
            if request.method == 'POST' and user and is_volunteer and enrollment_status == 'not_applied':
                volunteer_profile = ProfilesVolunteer.objects.filter(user=user).first()
                if volunteer_profile:
                    with connection.cursor() as cursor:
                        cursor.execute("""
                            INSERT INTO event_enrollment (event_id, profiles_vol_id, applied_at, record_created_at)
                            VALUES (:1, :2, SYSDATE, SYSDATE)
                        """, [event_id, volunteer_profile.profiles_vol_id])
                        connection.commit()
                        messages.success(request, "You have successfully applied to this event.")
                        return redirect('event_page', event_id=event_id)

    except cx_Oracle.DatabaseError as e:
        print(f"Error: {e}")
        messages.error(request, "A database error occurred.")
        return redirect('events')

    return render(request, 'event.html', {
        'event_data': event_data,
        'is_logged_in': bool(user),
        'is_volunteer': is_volunteer,
        'enrollment_status': enrollment_status,
        'accepted_volunteers': accepted_volunteers,
        'pending_volunteers': pending_volunteers,
        'rejected_volunteers': rejected_volunteers,
        #'is_event_organizer': user and not is_volunteer and event_data['organizer_id'] == user.extension.profiles_org_id,
        'is_event_organizer': org_profile and event_data['organizer_id'] == org_profile.profiles_org_id,
    })

def find_event(request):
    query = Event.objects.defer('event_image').all()  # Exclude BLOB field
    zip_code = request.GET.get("zip_code")
    distance = request.GET.get("distance")
    date = request.GET.get("date")
    org_name = request.GET.get("organization_name")
    selected_skills = request.GET.getlist("skills")
    skill_search_text = request.GET.get("skill_text")
    selected_languages = request.GET.getlist("languages")
    language_search_text = request.GET.get("language_text")

    # Filter by distance using pgeocode.GeoDistance
    if zip_code and distance:
        try:
            dist = pgeocode.GeoDistance("us")
            event_zips = Event.objects.values_list('event_zip', flat=True).distinct()
            valid_zips = []
            for event_zip in event_zips:
                # Ensure event_zip is a string for compatibility
                event_zip_str = str(event_zip)
                calculated_distance = dist.query_postal_code(str(zip_code), event_zip_str)
                if calculated_distance <= float(distance):
                    valid_zips.append(event_zip)
            
            # Debugging distances
            # print(f"Valid ZIPs within {distance} miles of {zip_code}: {valid_zips}")
            query = query.filter(event_zip__in=valid_zips)
        except Exception as e:
            # print(f"Error during distance calculation: {e}")
            query = query.none()

    # Filter by date
    if date:
        query = query.filter(event_date=date)
    else:
        query = query.filter(
            event_date__gte=datetime.date.today(),
            application_deadline__gte=datetime.date.today()
        )

    # Filter by organization name
    if org_name:
        query = query.filter(profiles_org_id__org_name__icontains=org_name)

    # Filter by skills
    if selected_skills:
        query = query.filter(eventskill__skill_id__in=selected_skills).distinct()

    # Filter by skill text search
    if skill_search_text:
        query = query.filter(eventskill__skill_id__skill_name__icontains=skill_search_text).distinct()

    # Filter by languages
    if selected_languages:
        query = query.filter(eventtranslatelanguage__target_language_id__in=selected_languages).distinct()

    # Filter by language text search
    if language_search_text:
        query = query.filter(
            eventtranslatelanguage__target_language_id__language__icontains=language_search_text
        ).distinct()

    # Fetch all skills for the "Search Skills" textbox
    all_skills = Skill.objects.all()

    # Fetch "Light Physical Work" skill as the mandatory skill
    mandatory_skill = Skill.objects.filter(skill_name="Light Physical Work").first()

    # Fetch all unique skills from upcoming events, excluding "Light Physical Work"
    unique_skills = Skill.objects.filter(
        eventskill__event_id__event_date__gte=datetime.date.today(),
        eventskill__event_id__isnull=False
    ).exclude(skill_name="Light Physical Work").distinct()

    # Convert unique_skills to a list to avoid further evaluation
    unique_skills = list(unique_skills)

    # Limit to 2 skills
    random_skills = unique_skills[:2]

    # DEBUG
    # print("Mandatory Skill:", mandatory_skill)
    # print("Unique Skills:", unique_skills)
    # print("Random Skills (limited):", random_skills)

    # Combine the mandatory skill and random skills, ensuring uniqueness
    skills_checkbox = []
    seen_skill_ids = set()  # To track added skill IDs

    # Add mandatory skill
    if mandatory_skill and mandatory_skill.skill_id not in seen_skill_ids:
        skills_checkbox.append(mandatory_skill)
        seen_skill_ids.add(mandatory_skill.skill_id)

    # Add random skills
    for skill in random_skills:
        if skill.skill_id not in seen_skill_ids:
            skills_checkbox.append(skill)
            seen_skill_ids.add(skill.skill_id)

    # Debug
    # print("Skills checkbox:", skills_checkbox)

    # Fetch all languages
    languages = Language.objects.all()

    # Fetch all organizations
    organizations = ProfilesOrg.objects.all()

    # If no results, find suggestions
    if not query.exists():
        suggestions = Event.objects.filter(event_date__gte=datetime.date.today())[:5]
    else:
        suggestions = []

    return render(request, 'find_event.html', {
        'events': query,
        'skills': all_skills,
        'skills_checkbox': skills_checkbox,
        'languages': languages,
        'organizations': organizations,
        'suggestions': suggestions,
    })

@login_required
def event_recommend(request, event_id):
    user = request.user
    if not user.extension.is_org:
        messages.error(request, "You must be an organization to recommend events.")
        return redirect('events')

    org_profile = ProfilesOrg.objects.filter(user=user).first()
    if not org_profile:
        messages.error(request, "Organization profile not found.")
        return redirect('events')

    event = Event.objects.filter(event_id=event_id, profiles_org_id=org_profile.profiles_org_id).first()
    if not event:
        messages.error(request, "You can only recommend your own events.")
        return redirect('events')

    # Handle POST request to submit a recommendation
    if request.method == 'POST':
        to_vol_id = request.POST.get('to_vol_id')
        recommendation_msg = request.POST.get('recommendation_msg', '').strip()

        # Ensure the volunteer exists and matches criteria
        volunteer = ProfilesVolunteer.objects.filter(
            profiles_vol_id=to_vol_id,
            accept_recommendation='Y',
            visible_to_orgs='Y',
        ).first()

        if not volunteer:
            messages.error(request, "Invalid volunteer selected for recommendation.")
            return redirect('eventrecommend', event_id=event_id)

        # Create a recommendation entry in the database
        Recommendation.objects.create(
            event_id=event,
            from_org_id=org_profile,
            from_vol_id=None,  # Null for org recommendations
            to_vol_id=volunteer,
            recommendation_msg=recommendation_msg
        )

        messages.success(request, f"Recommendation sent to {volunteer.user.first_name} {volunteer.user.last_name}.")
        return redirect('eventrecommend', event_id=event_id)

    # Fetch event skills and languages
    event_skills = list(EventSkill.objects.filter(event_id=event_id).values_list('skill_id', flat=True))
    event_languages = list(EventTranslateLanguage.objects.filter(event_id=event_id).values_list('target_language_id', flat=True))

    # Add special handling for "Light Physical Work"
    light_physical_skill = Skill.objects.filter(skill_name="Light Physical Work").first()

    # Build the query filter for eligible volunteers
    query_filter = models.Q(
        volunteerskill__skill_id__in=event_skills
    ) | models.Q(
        volunteerlanguage__language_id__in=event_languages, willing_to_translate='Y'
    )

    if light_physical_skill and light_physical_skill.skill_id in event_skills:
        query_filter |= models.Q(willing_to_light_physical='Y')

    # Fetch eligible volunteers, excluding BLOB fields
    eligible_volunteers = ProfilesVolunteer.objects.defer('profile_image_vol').filter(
        accept_recommendation='Y',
        visible_to_orgs='Y',
    ).exclude(
        profiles_vol_id__in=EventEnrollment.objects.filter(event_id=event_id).values_list('profiles_vol_id', flat=True)
    ).exclude(
        profiles_vol_id__in=Recommendation.objects.filter(event_id=event_id).values_list('to_vol_id', flat=True)
    ).filter(query_filter).distinct()

    # Annotate each volunteer with matching skills and languages
    annotated_volunteers = []
    for volunteer in eligible_volunteers:
        volunteer_skills = list(volunteer.volunteerskill_set.values_list('skill_id', flat=True))
        volunteer_languages = list(volunteer.volunteerlanguage_set.values_list('language_id', flat=True))

        matching_skills = [skill for skill in Skill.objects.filter(skill_id__in=event_skills) if skill.skill_id in volunteer_skills]
        if light_physical_skill and volunteer.willing_to_light_physical == 'Y' and light_physical_skill.skill_id in event_skills:
            matching_skills.append(light_physical_skill)

        matching_languages = [language for language in Language.objects.filter(language_id__in=event_languages) if language.language_id in volunteer_languages]

        annotated_volunteers.append({
            'volunteer': volunteer,
            'matching_skills': matching_skills,
            'matching_languages': matching_languages,
        })

    # Fetch pending recommendations (recommended but not applied)
    pending_recommendations = Recommendation.objects.filter(event_id=event_id).exclude(
        to_vol_id__in=EventEnrollment.objects.filter(event_id=event_id).values_list('profiles_vol_id', flat=True)
    )

    pending_volunteers = []
    for recommendation in pending_recommendations:
        volunteer = recommendation.to_vol_id
        volunteer_skills = list(volunteer.volunteerskill_set.values_list('skill_id', flat=True))
        volunteer_languages = list(volunteer.volunteerlanguage_set.values_list('language_id', flat=True))

        matching_skills = [skill for skill in Skill.objects.filter(skill_id__in=event_skills) if skill.skill_id in volunteer_skills]
        if light_physical_skill and volunteer.willing_to_light_physical == 'Y' and light_physical_skill.skill_id in event_skills:
            matching_skills.append(light_physical_skill)

        matching_languages = [language for language in Language.objects.filter(language_id__in=event_languages) if language.language_id in volunteer_languages]

        pending_volunteers.append({
            'volunteer': volunteer,
            'matching_skills': matching_skills,
            'matching_languages': matching_languages,
            'recommendation_msg': recommendation.recommendation_msg,
        })

    return render(request, 'event_recommend.html', {
        'event': event,
        'annotated_volunteers': annotated_volunteers,
        'pending_volunteers': pending_volunteers,
        #'recommendation_msg': recommendation.recommendation_msg,  
    })

@login_required
def chat_view(request, room_id=None):
    # Restrict chat rooms based on user type:
    if request.user.extension.is_org:
        org_profile = ProfilesOrg.objects.filter(user=request.user).first()
        if org_profile:
            rooms = EventChat.objects.filter(event_id__profiles_org_id=org_profile).order_by('-event_id__event_date')
        else:
            rooms = EventChat.objects.none()
    else:
        volunteer_profile = ProfilesVolunteer.objects.filter(user=request.user).first()
        if volunteer_profile:
            enrolled_event_ids = EventEnrollment.objects.filter(
                profiles_vol_id=volunteer_profile.profiles_vol_id,
                is_accepted='Y'
            ).values_list('event_id', flat=True)
            rooms = EventChat.objects.filter(event_id__in=enrolled_event_ids).order_by('-event_id__event_date')
        else:
            rooms = EventChat.objects.none()

    if room_id is None:
        if rooms.exists():
            default_room_id = rooms.first().chat_id
            return redirect('chat_room', room_id=default_room_id)
        else:
            context = {
                'rooms': rooms,
                'active_chat_id': None,
                'chat_history': [],
            }
            return render(request, 'chat.html', context)
    else:
        try:
            # Try to get the chat room from the allowed set.
            active_chat = rooms.get(chat_id=room_id)
        except EventChat.DoesNotExist:
            # If the provided room_id is not allowed, fall back to the default room if available.
            if rooms.exists():
                default_room_id = rooms.first().chat_id
                return redirect('chat_room', room_id=default_room_id)
            else:
                context = {
                    'rooms': rooms,
                    'active_chat_id': None,
                    'chat_history': [],
                }
                return render(request, 'chat.html', context)

        chat_history = EventChatHistory.objects.filter(chat_id=active_chat).order_by('sent_at')
        context = {
            'rooms': rooms,
            'active_chat_id': room_id,
            'chat_history': chat_history,
        }
        return render(request, 'chat.html', context)
