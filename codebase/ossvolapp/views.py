from django.shortcuts import render, redirect
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


from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db import connection
from ossvolapp.models import ProfilesOrg, ProfilesVolunteer

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
                    SELECT event_name, event_zip, event_date 
                    FROM uni_project.events 
                    WHERE TRUNC(event_date) >= TRUNC(SYSDATE) 
                      AND profiles_org_id = %s
                    ORDER BY event_date DESC
                """, [org_profile.profiles_org_id])
                upcoming_events = cursor.fetchall()

                # Query for past events
                cursor.execute("""
                    SELECT event_name, event_zip, event_date 
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
                    SELECT e.event_name, e.event_zip, e.event_date
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
                    SELECT e.event_name, e.event_zip, e.event_date
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
