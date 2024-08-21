import datetime
from django.shortcuts import render, redirect, get_object_or_404
from home.models import *
from authentication.models import User
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden, JsonResponse
import random
from colorsys import rgb_to_hls, hls_to_rgb
from django.template.loader import render_to_string
from .models import *
from django.db import IntegrityError
from firebase_admin import storage
from PIL import Image
import io
from .forms import UserProfileForm
from django.contrib import messages

# Create your views here.

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

@login_required
def profile(request, username):
    if not request.user.is_authenticated:
        return redirect('login')
    
    # Fetch the user based on the username parameter
    profile_user = get_object_or_404(User, username=username)
    
    # Filter posts for the profile user
    posts = Post.objects.filter(user=profile_user).prefetch_related('images').order_by('-created_at')
    
    # Fetch liked posts by the current user
    liked_posts = Like.objects.filter(user=request.user).values_list('post_id', flat=True)

    saved_posts = Save.objects.filter(user=request.user).values_list('post_id', flat=True)
    
    # Fetch all comments related to the filtered posts
    comments = Comment.objects.filter(post__in=posts).select_related('user')

    # Check if the current user is following the profile user
    is_following = Follow.objects.filter(user=request.user, following=profile_user).exists()

    # Fetch follower count for the profile user
    follower_count = Follow.objects.filter(following=profile_user).count()

    mutual_people = get_mutual_people(request.user)

    # Retrieve the list of users that the current user follows
    following_users = User.objects.filter(following__user=request.user)

    notifications = Notification.objects.filter(user=request.user).order_by('-created_at')
    unread_notifications = Notification.objects.filter(user=request.user, read=False).order_by('-created_at')
    unread_notifications_count = Notification.objects.filter(user=request.user, read=False).count()

    try:
        profile_details = UserProfile.objects.get(user__username=username)
    except UserProfile.DoesNotExist:
        profile_details = None


    # Format follower count as abbreviated
    def format_follower_count(count):
        if count < 1000:
            return str(count)
        elif count < 1000000:
            if count % 1000 == 0:
                return f"{count // 1000}k"
            else:
                return f"{count / 1000:.1f}k"
        elif count < 1000000000:
            if count % 1000000 == 0:
                return f"{count // 1000000}M"
            else:
                return f"{count / 1000000:.1f}M"
        else:
            if count % 1000000000 == 0:
                return f"{count // 1000000000}B"
            else:
                return f"{count / 1000000000:.1f}B"
    
    def generate_signed_url(blob_path):
        bucket = storage.bucket()
        blob = bucket.blob(blob_path)
        url = blob.generate_signed_url(
            version="v4",
            expiration=datetime.timedelta(hours=1),
            method="GET",
        )
        return url
    
    for user in mutual_people:
        if user.profile_picture_url: 
            blob_path = user.profile_picture_url.split('social-app-50633.appspot.com/')[-1]
            user.profile_pic = generate_signed_url(blob_path)

    for user in following_users:
        if user.profile_picture_url: 
            blob_path = user.profile_picture_url.split('social-app-50633.appspot.com/')[-1]
            user.profile_pic = generate_signed_url(blob_path)

            
    profile_picture_url = None
    current_user_profile_picture_url = None

    if profile_user.profile_picture_url:
        blob_path = profile_user.profile_picture_url.split('social-app-50633.appspot.com/')[-1]
        profile_picture_url = generate_signed_url(blob_path)
    
    if request.user.profile_picture_url: 
        blob_path = request.user.profile_picture_url.split('social-app-50633.appspot.com/')[-1]
        current_user_profile_picture_url = generate_signed_url(blob_path)

    for post in posts:
        post.is_liked = post.id in liked_posts
        post.is_saved = post.id in saved_posts

        if post.user.profile_picture_url: 
            blob_path = post.user.profile_picture_url.split('social-app-50633.appspot.com/')[-1]
            post.user_pic = generate_signed_url(blob_path)
        
        post.post_comments = comments.filter(post=post)
        
        # Generate signed URLs for comment profile pictures and their replies
        for comment in post.post_comments:
            if comment.user.profile_picture_url:
                blob_path = comment.user.profile_picture_url.split('social-app-50633.appspot.com/')[-1]
                comment.user_pic = generate_signed_url(blob_path)
            
            # Process replies
            for reply in comment.replies.all():
                if reply.user.profile_picture_url:
                    blob_path = reply.user.profile_picture_url.split('social-app-50633.appspot.com/')[-1]
                    reply.user_pic = generate_signed_url(blob_path)

        # Fetch and process random comment and its reply
        random_comment = Comment.objects.filter(post=post, parent_id__isnull=True).order_by('?').first()
        random_comment_reply = None
        if random_comment:
            if random_comment.user.profile_picture_url:
                blob_path = random_comment.user.profile_picture_url.split('social-app-50633.appspot.com/')[-1]
                random_comment.user_pic = generate_signed_url(blob_path)
            
            random_comment_reply = random_comment.replies.first()
            if random_comment_reply and random_comment_reply.user.profile_picture_url:
                blob_path = random_comment_reply.user.profile_picture_url.split('social-app-50633.appspot.com/')[-1]
                random_comment_reply.user_pic = generate_signed_url(blob_path)
        
        setattr(post, 'random_comment', random_comment)
        setattr(post, 'random_comment_reply', random_comment_reply)

        # Generate signed URLs for post images
        for image in post.images.all():
            blob_path = image.url.split('social-app-50633.appspot.com/')[-1]
            image.signed_url = generate_signed_url(blob_path)
    
    context = {
        'profile_user': profile_user,
        'profile_picture_url': profile_picture_url,
        'profile_detail': profile_details,
        'current_profile_picture_url': current_user_profile_picture_url,
        'posts': posts,
        'comments': comments,
        'is_following': is_following,
        'follower_count': format_follower_count(follower_count),
        'following_users': following_users,
        'recommended_profiles': mutual_people,
        'notifications': notifications,
        'unread_notifications_count': unread_notifications_count,
        'unread_notifications': unread_notifications,
    }
    
    print(f"Number of posts retrieved for {profile_user.username}: {len(posts)}")
    return render(request, 'profile.html', context)

@login_required
def follow(request, username):
    if not request.user.is_authenticated:
        return JsonResponse({'success': False, 'message': 'You must be logged in to follow.'}, status=403)

    user_to_follow = get_object_or_404(User, username=username)
    action = request.POST.get('action')

    if action == 'follow':
        try:
            follow, created = Follow.objects.get_or_create(user=request.user, following=user_to_follow)
            if created:
                return JsonResponse({'success': True, 'message': f'You are now following {user_to_follow.username}.'})
            else:
                return JsonResponse({'success': False, 'message': f'You are already following {user_to_follow.username}.'})
        except IntegrityError:
            # This might occur in rare race conditions
            return JsonResponse({'success': False, 'message': f'You are already following {user_to_follow.username}.'})

    elif action == 'unfollow':
        deleted, _ = Follow.objects.filter(user=request.user, following=user_to_follow).delete()
        if deleted:
            return JsonResponse({'success': True, 'message': f'You have unfollowed {user_to_follow.username}.'})
        else:
            return JsonResponse({'success': False, 'message': 'You are not following this user.'})

    else:
        return JsonResponse({'success': False, 'message': 'Invalid action.'}, status=400)

@login_required
def update_profile_picture(request):
    if request.method == 'POST':
        if 'cropped_image' not in request.FILES:
            return JsonResponse({'success': False, 'message': 'No file uploaded.'}, status=400)
        
        cropped_image = request.FILES['cropped_image']
        user = request.user

        # Open the image using Pillow
        img = Image.open(cropped_image)

        # Convert to RGB if it's not already (in case it's RGBA)
        if img.mode != 'RGB':
            img = img.convert('RGB')

        # Create a byte stream to save the image
        img_byte_arr = io.BytesIO()
        img.save(img_byte_arr, format='JPEG')
        img_byte_arr = img_byte_arr.getvalue()

        # Generate a unique filename
        filename = f'{user.username}_{datetime.datetime.now().strftime("%Y%m%d%H%M%S")}.jpg'

        # Upload the file to Firebase Storage
        bucket = storage.bucket()
        blob = bucket.blob(f'profile_pictures/{filename}')
        blob.upload_from_string(img_byte_arr, content_type='image/jpeg')
        blob.make_public()

        # Update the user's profile picture URL
        user.profile_picture_url = blob.public_url
        user.save()

        return JsonResponse({'success': True, 'message': 'Profile picture updated successfully.'})

    return JsonResponse({'success': False, 'message': 'Invalid request method.'}, status=405)

@login_required
def edit_profile(request, username):
    user = get_object_or_404(User, username=username)
    
    # Check if the logged-in user is the owner of the profile
    if request.user != user:
        return HttpResponseForbidden("You don't have permission to edit this profile.")

    # Get or create the UserProfile
    profile, created = UserProfile.objects.get_or_create(user=user)

    if request.method == 'POST':
        form = UserProfileForm(request.POST, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, 'Your profile has been updated successfully!')
            return redirect('profile', username=username)
    else:
        form = UserProfileForm(instance=profile)
    
    return render(request, 'edit_profile.html', {'form': form, 'profile_user': user})