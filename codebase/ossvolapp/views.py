from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.contrib.auth.models import User
from .models import *
from django.http import JsonResponse
from django.db import transaction
from django.contrib.auth.hashers import make_password
from django.db.models.functions import Upper

def index_view(request):
    return render(request, 'index.html')  # Public landing page

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