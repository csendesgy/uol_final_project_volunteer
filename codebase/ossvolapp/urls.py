from django.urls import path
from . import views
from django.http import HttpResponse

# Placeholder views for urls until implementation
def placeholder_view(request):
    return HttpResponse("This is a placeholder view.")
    #example: path('register/', placeholder_view, name='register'),

urlpatterns = [
    path('', views.index_view, name='index'),  
    path('register/', views.register_view, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'), 
    path('home/', views.home_view, name='home'),  # Home page for logged-in users  
]