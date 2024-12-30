from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.contrib.auth.models import User
from .models import *
from django.http import JsonResponse

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
        # Handle form submission logic here
        user_type = request.POST.get('user_type')
        # Process form fields based on user type
        if user_type == 'organization':
            # Handle organization registration
            pass
        elif user_type == 'volunteer':
            # Handle volunteer registration
            pass
        return JsonResponse({'message': 'Registration successful!'})
