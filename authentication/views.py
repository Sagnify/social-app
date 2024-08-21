from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.views.decorators.cache import never_cache
from .models import User
from accounts.models import *
from home.models import *
from django.contrib import messages
from django.urls import reverse
from .forms import UserRegistrationForm, UserProfileForm
from django.http import JsonResponse


def loginpage(request):
    if request.method == "POST":
        username = request.POST.get('username')
        password = request.POST.get('password')

        user = authenticate(username=username, password=password)
        print("autheticated")
        print(username)
        if user is not None:
            login(request, user)
            print("Logged in")
            UserProfile.objects.get_or_create(user=user)
            

            # Check if the request is an AJAX request
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({'status': 'success', 'username': request.user.username})

            next_url = request.POST.get('next', '/')
            return redirect(next_url)
        else:
            # Check if the request is an AJAX request
            print("Login Error")
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({'status': 'error', 'message': 'Invalid credentials!'})

            return render(request, 'login.html', {'error_message': 'Invalid credentials!'})

    return render(request, 'login.html')

@never_cache
def logout_view(request):
    logout(request)
    return redirect('login')

def register_step1(request):
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('register_step2')
    else:
        form = UserRegistrationForm()
    return render(request, 'register_step1.html', {'form': form})


def register_step2(request):
    if request.method == 'POST':
        form = UserProfileForm(request.POST, instance=request.user.userprofile)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profile created successfully.')
            Notification.objects.create(
                user=request.user,
                title='Profile created successfully',
                description='View Profile',
                target_link=f'/p/@{request.user.username}/',
                icon='fa-regular fa-user mr-1'
            )
            return redirect('profile', username=request.user.username)  # Redirect to profile page or homepage
    else:
        form = UserProfileForm(instance=request.user.userprofile)
    return render(request, 'register_step2.html', {'form': form})

