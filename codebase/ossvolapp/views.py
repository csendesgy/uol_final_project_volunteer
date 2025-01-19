from django.shortcuts import render, redirect
from django.conf import settings
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib.auth.hashers import make_password
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.db import transaction, connection
from django.db.models.functions import Upper
from .models import *
import base64
import cx_Oracle
from geopy.distance import geodesic
import pgeocode
import datetime


def index_view(request):
    return render(request, 'index.html')  # Public landing page

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
    return render(request, 'home.html')  # Page for logged-in users

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

                    # Step 2: If not found, insert the language with properly capitalized words
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
                    SELECT e.event_id, e.event_name, e.event_zip, e.event_date, count(ee.profiles_vol_id) as pending_approval_cnt
                      FROM uni_project.events e
                    LEFT JOIN uni_project.event_enrollment ee
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
                    SELECT event_id, event_name, event_zip, event_date 
                    FROM uni_project.events 
                    WHERE TRUNC(event_date) < TRUNC(SYSDATE) 
                      AND profiles_org_id = %s
                    ORDER BY event_date DESC
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
                    SELECT e.event_id, e.event_name, e.event_zip, e.event_date
                    FROM uni_project.events e
                    JOIN uni_project.event_enrollment ee ON e.event_id = ee.event_id
                    WHERE TRUNC(e.event_date) >= TRUNC(SYSDATE)
                      AND ee.is_accepted = 'Y'
                      AND ee.profiles_vol_id = %s
                    ORDER BY e.event_date DESC
                """, [volunteer_profile.profiles_vol_id])
                upcoming_events = cursor.fetchall()

                # Query for past events
                cursor.execute("""
                    SELECT e.event_id, e.event_name, e.event_zip, e.event_date
                    FROM uni_project.events e
                    JOIN uni_project.event_enrollment ee ON e.event_id = ee.event_id
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
                        FROM uni_project.events
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
                            FROM uni_project.events
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
                            UPDATE uni_project.events
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
                            INSERT INTO uni_project.events
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
                            FROM uni_project.events
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
                            skill_id = skill_id_var.getvalue(0)
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
                            language_id = lang_id_var.getvalue(0)
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
                        FROM uni_project.events e
                        JOIN uni_project.profiles_org o ON e.profiles_org_id = o.profiles_org_id
                        LEFT JOIN uni_project.event_skills es ON e.event_id = es.event_id
                        LEFT JOIN uni_project.skills sk ON es.skill_id = sk.skill_id
                        LEFT JOIN uni_project.event_translate_language el ON e.event_id = el.event_id
                        LEFT JOIN uni_project.languages l ON el.target_language_id = l.language_id
                        LEFT JOIN uni_project.languages_level ll ON el.required_language_level_id = ll.languages_level_id
                        LEFT JOIN uni_project.event_enrollment er ON (e.event_id = er.event_id AND er.is_accepted = 'Y')
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
                    JOIN uni_project.events e ON ad.event_id = e.event_id
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
                                    UPDATE uni_project.event_enrollment
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
                                    UPDATE uni_project.event_enrollment
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
                                        UPDATE uni_project.event_enrollment
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
                        FROM uni_project.event_enrollment et
                        JOIN uni_project.profiles_volunteer pv ON et.profiles_vol_id = pv.profiles_vol_id
                        JOIN uni_project.auth_user au ON pv.user_id = au.id
                        WHERE et.event_id = :1 AND NVL(et.is_accepted, 'N') = 'Y'
                    """, [event_id])
                    accepted_volunteers = cursor.fetchall()

                    # Pending volunteers
                    cursor.execute("""
                        SELECT au.first_name, au.last_name, au.email, et.last_updated_at, et.profiles_vol_id
                        FROM uni_project.event_enrollment et
                        JOIN uni_project.profiles_volunteer pv ON et.profiles_vol_id = pv.profiles_vol_id
                        JOIN uni_project.auth_user au ON pv.user_id = au.id
                        WHERE et.event_id = :1 AND NVL(et.is_accepted, 'N') = 'N' AND NVL(et.is_rejected, 'N') = 'N'
                    """, [event_id])
                    pending_volunteers = cursor.fetchall()

                    # Rejected volunteers
                    cursor.execute("""
                        SELECT au.first_name, au.last_name, au.email, et.rejected_at, et.reject_reason, et.last_updated_at, et.profiles_vol_id
                        FROM uni_project.event_enrollment et
                        JOIN uni_project.profiles_volunteer pv ON et.profiles_vol_id = pv.profiles_vol_id
                        JOIN uni_project.auth_user au ON pv.user_id = au.id
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

from django.db.models import Q


def find_event(request):
    query = Event.objects.all()
    zip_code = request.GET.get("zip_code")
    distance = request.GET.get("distance")
    date = request.GET.get("date")
    org_name = request.GET.get("organization_name")
    selected_skills = request.GET.getlist("skills")
    selected_languages = request.GET.getlist("languages")
    skill_search_text = request.GET.get("skill_text")

    # Filter by distance using pgeocode
    if zip_code and distance:
        nomi = pgeocode.Nominatim("us")
        origin = nomi.query_postal_code(zip_code)
        if origin.latitude and origin.longitude:
            # Get all unique event zip codes
            event_zips = Event.objects.values_list('event_zip', flat=True).distinct()
            valid_zips = []
            for event_zip in event_zips:
                destination = nomi.query_postal_code(str(event_zip))
                if (
                    destination.latitude
                    and destination.longitude
                    and geodesic((origin.latitude, origin.longitude), 
                                 (destination.latitude, destination.longitude)).miles <= float(distance)
                ):
                    valid_zips.append(event_zip)
            query = query.filter(event_zip__in=valid_zips)

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
        query = query.filter(
            eventskill__skill_id__skill_name__icontains=skill_search_text
        ).distinct()

    # Filter by languages
    if selected_languages:
        query = query.filter(eventtranslatelanguage__target_language_id__in=selected_languages).distinct()

    # Fetch available skills and ensure "Light Physical Work" is always present
    dynamic_skills = Skill.objects.filter(
        eventskill__event_id__event_date__gte=datetime.date.today()
    ).distinct()[:2]
    mandatory_skill = Skill.objects.filter(skill_name="Light Physical Work").first()
    skills = [mandatory_skill] + list(dynamic_skills) if mandatory_skill else list(dynamic_skills)

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
        'skills': skills,
        'languages': languages,
        'organizations': organizations,
        'suggestions': suggestions,
    })
