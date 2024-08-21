from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.conf import settings
import json
from authentication.models import *
from home.models import *
from accounts.models import *
from django.core.serializers import serialize
from django.contrib.auth.decorators import login_required
from django.db.models import F
from firebase_admin import storage
import datetime
from firebase_admin import auth

def create_firebase_session_cookie(request):
    # Extract ID token from request (you should secure this endpoint)
    id_token = request.POST.get('idToken')
    
    try:
        # Verify the ID token
        decoded_token = auth.verify_id_token(id_token)
        uid = decoded_token['uid']
        
        # Create a session cookie (valid for 5 days in this example)
        session_cookie = auth.create_session_cookie(id_token, expires_in=datetime.timedelta(days=5))
        
        # Return the session cookie to the client
        response = JsonResponse({'sessionCookie': session_cookie})
        return response
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)

@login_required(login_url='/login')
def chat_view(request):
    notifications = Notification.objects.filter(user=request.user).order_by('-created_at')
    unread_notifications = Notification.objects.filter(user=request.user, read=False).order_by('-created_at')
    unread_notifications_count = Notification.objects.filter(user=request.user, read=False).count()

    mutual_people = get_mutual_people(request.user)

    f_users = User.objects.filter(following__user=request.user)

    following_users = Follow.objects.filter(user=request.user).values_list('following', flat=True)
    followers_users = Follow.objects.filter(following=request.user).values_list('user', flat=True)

    mutual_followers_ids = set(following_users).intersection(set(followers_users))

    mutual_followers = User.objects.filter(id__in=mutual_followers_ids)

    def generate_signed_url(blob_path):
        bucket = storage.bucket()
        blob = bucket.blob(blob_path)
        url = blob.generate_signed_url(
            version="v4",
            expiration=datetime.timedelta(hours=1),
            method="GET",
        )
        return url

    if request.user.profile_picture_url: 
        blob_path = request.user.profile_picture_url.split('social-app-50633.appspot.com/')[-1]
        current_user_profile_picture_url = generate_signed_url(blob_path)
    else:
        current_user_profile_picture_url = None

    for user in mutual_people:
        if user.profile_picture_url: 
            blob_path = user.profile_picture_url.split('social-app-50633.appspot.com/')[-1]
            user.profile_pic = generate_signed_url(blob_path)

    for user in f_users:
        if user.profile_picture_url: 
            blob_path = user.profile_picture_url.split('social-app-50633.appspot.com/')[-1]
            user.profile_pic = generate_signed_url(blob_path)

    mutual_followers_data = []
    for user in mutual_followers:
        user_data = {
            'id': user.id,
            'username': user.username,
            'profile_picture_url': None
        }
        if user.profile_picture_url:
            blob_path = user.profile_picture_url.split('social-app-50633.appspot.com/')[-1]
            user_data['profile_picture_url'] = generate_signed_url(blob_path)
        mutual_followers_data.append(user_data)

    firebase_config = {
        'apiKey': settings.FIREBASE_API_KEY,
        'authDomain': settings.FIREBASE_AUTH_DOMAIN,
        'databaseURL': settings.FIREBASE_DATABASE_URL,
        'projectId': settings.FIREBASE_PROJECT_ID,
        'storageBucket': settings.FIREBASE_STORAGE_BUCKET,
        'messagingSenderId': settings.FIREBASE_MESSAGING_SENDER_ID,
        'appId': settings.FIREBASE_APP_ID,
    }

    followed_users_json = json.dumps(mutual_followers_data, default=str)

    context = {
        'firebase_config_json': json.dumps(firebase_config),
        'followed_users_json': followed_users_json,
        'notifications': notifications,
        'unread_notifications_count': unread_notifications_count,
        'unread_notifications': unread_notifications,    
        'following_users': f_users,
        'recommended_profiles': mutual_people,
        'current_profile_picture_url': current_user_profile_picture_url,
    }

    return render(request, 'chat.html', context)

def get_mutual_people(user):
    # Get the IDs of users whom the given user follows
    followed_user_ids = Follow.objects.filter(user=user).values_list('following_id', flat=True)

    # Get users who are followed by the followed users
    followed_users = User.objects.filter(id__in=followed_user_ids)

    # Get IDs of users whom the followed users are following
    followed_by_followed_users_ids = Follow.objects.filter(user__in=followed_users).values_list('following_id', flat=True)

    # Exclude users that the current user is already following
    recommended_users = User.objects.filter(
        id__in=followed_by_followed_users_ids
    ).exclude(
        id__in=followed_user_ids
    ).exclude(
        id=user.id
    ).distinct()[:4]

    return recommended_users