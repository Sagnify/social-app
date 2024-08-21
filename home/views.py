import json
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.http import require_POST, require_GET
from django.contrib.auth.decorators import login_required
from .models import *
from accounts.models import *
from django.contrib import messages
from authentication.models import User
import random
from colorsys import rgb_to_hls, hls_to_rgb
from django.template.loader import render_to_string
from django.utils import timezone
from datetime import timedelta
from django.db.models import Count, F, Q
from .firebase_config import bucket
from firebase_admin import storage
import datetime
from home.recommendation import recommend_posts
from django.core.paginator import Paginator
import os
import uuid



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
def home(request):
    if not request.user.is_authenticated:
        return redirect('login')
    
    posts = recommend_posts(request)

    # Add pagination
    paginator = Paginator(posts, 2)  # Show 10 posts per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    def generate_signed_url(blob_path):
        bucket = storage.bucket()
        blob = bucket.blob(blob_path)
        url = blob.generate_signed_url(
            version="v4",
            expiration=datetime.timedelta(hours=1),
            method="GET",
        )
        return url
    
    current_user_profile_picture_url = None
    
    if request.user.profile_picture_url: 
        blob_path = request.user.profile_picture_url.split('social-app-50633.appspot.com/')[-1]
        current_user_profile_picture_url = generate_signed_url(blob_path)
    
    liked_posts = Like.objects.filter(user=request.user).values_list('post_id', flat=True)
    comments = Comment.objects.filter(post__in=posts).select_related('user').prefetch_related('replies__user')
    saved_posts = Save.objects.filter(user=request.user).values_list('post_id', flat=True)

    notifications = Notification.objects.filter(user=request.user).order_by('-created_at')
    unread_notifications = Notification.objects.filter(user=request.user, read=False).order_by('-created_at')
    unread_notifications_count = Notification.objects.filter(user=request.user, read=False).count()
    

    mutual_people = get_mutual_people(request.user)
    following_users = User.objects.filter(following__user=request.user)

    for user in mutual_people:
        if user.profile_picture_url: 
            blob_path = user.profile_picture_url.split('social-app-50633.appspot.com/')[-1]
            user.profile_pic = generate_signed_url(blob_path)

    for user in following_users:
        if user.profile_picture_url: 
            blob_path = user.profile_picture_url.split('social-app-50633.appspot.com/')[-1]
            user.profile_pic = generate_signed_url(blob_path)
    
    for post in posts:
        post.is_liked = post.id in liked_posts
        post.is_saved = post.id in saved_posts
        
        post.post_comments = comments.filter(post=post, parent_id__isnull=True)

        if post.user.profile_picture_url: 
            blob_path = post.user.profile_picture_url.split('social-app-50633.appspot.com/')[-1]
            post.user_pic = generate_signed_url(blob_path)

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
        'posts': page_obj,
        'comments': comments,
        'current_profile_picture_url': current_user_profile_picture_url,
        'notifications': notifications,
        'unread_notifications_count': unread_notifications_count,
        'unread_notifications': unread_notifications,
        'following_users': following_users,
        'recommended_profiles': mutual_people,
    }

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        # If it's an AJAX request, return JSON response
        return JsonResponse({
            'html': render_to_string('post_list.html', {'posts': page_obj}),
            'has_next': page_obj.has_next(),
            'next_page': page_obj.next_page_number() if page_obj.has_next() else None,
        })
    
    print(f"Number of posts retrieved: {len(posts)}")
    return render(request, 'home.html', context)

@login_required
def post(request, post_id):
    if not request.user.is_authenticated:
        return redirect('login')
    
    post = get_object_or_404(Post.objects.prefetch_related('images'), post_id=post_id)

    def generate_signed_url(blob_path):
        bucket = storage.bucket()
        blob = bucket.blob(blob_path)
        url = blob.generate_signed_url(
            version="v4",
            expiration=datetime.timedelta(hours=1),
            method="GET",
        )
        return url


    current_user_profile_picture_url = None
    if request.user.profile_picture_url: 
        blob_path = request.user.profile_picture_url.split('social-app-50633.appspot.com/')[-1]
        current_user_profile_picture_url = generate_signed_url(blob_path)

    post.is_liked = Like.objects.filter(user=request.user, post=post).exists()
    post.is_saved = Save.objects.filter(user=request.user, post=post).exists()
    
    comments = Comment.objects.filter(post=post, parent_id__isnull=True).select_related('user').prefetch_related('replies__user')
    
    notifications = Notification.objects.filter(user=request.user).order_by('-created_at')
    unread_notifications = Notification.objects.filter(user=request.user, read=False).order_by('-created_at')
    unread_notifications_count = Notification.objects.filter(user=request.user, read=False).count()

    mutual_people = get_mutual_people(request.user)
    following_users = User.objects.filter(following__user=request.user)

    for user in mutual_people:
        if user.profile_picture_url: 
            blob_path = user.profile_picture_url.split('social-app-50633.appspot.com/')[-1]
            user.profile_pic = generate_signed_url(blob_path)

    for user in following_users:
        if user.profile_picture_url: 
            blob_path = user.profile_picture_url.split('social-app-50633.appspot.com/')[-1]
            user.profile_pic = generate_signed_url(blob_path)
    
    post.post_comments = comments

    # Generate signed URL for post user's profile picture
    if post.user.profile_picture_url:
        blob_path = post.user.profile_picture_url.split('social-app-50633.appspot.com/')[-1]
        post.user_pic = generate_signed_url(blob_path)

    # Generate signed URLs for comment profile pictures and their replies
    for comment in comments:
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
        'post': post,
        'current_profile_picture_url': current_user_profile_picture_url,
        'comments': comments,
        'notifications': notifications,
        'unread_notifications_count': unread_notifications_count,
        'unread_notifications': unread_notifications,
        'following_users': following_users,
        'recommended_profiles': mutual_people,
    }
    
    return render(request, 'post.html', context)


@require_GET
def search_users(request):
    query = request.GET.get('q', '')
    if query:
        users = User.objects.filter(username__icontains=query)[:10]
        user_list = [{'username': user.username} for user in users]
    else:
        user_list = []
    return JsonResponse(user_list, safe=False)


@login_required

def create_post(request):
    if request.method == 'POST':
        caption = request.POST.get('caption')
        tags_str = request.POST.get('tags')  # Assuming tags are submitted as a comma-separated string
        user = request.user  # Assuming user is logged in and associated with the post
       
        # Handle multiple image uploads
        image_files = request.FILES.getlist('images')  # Use 'images' to get a list of uploaded files
        image_urls = []
        for image_file in image_files:
            # Generate a unique file name
            file_extension = os.path.splitext(image_file.name)[1]
            unique_filename = f"{uuid.uuid4().hex}{file_extension}"
            blob = bucket.blob(f'posts/{unique_filename}')
            blob.upload_from_file(image_file)
            image_url = blob.public_url
            image_urls.append(image_url)
            print(f"Uploaded image URL: {image_url}")
        
        # Print received data to console for debugging
        print(f"Caption: {caption}")
        print(f"Tags: {tags_str}")
        print(f"User: {user}")
        
        # Create and save the Post instance
        new_post = Post(caption=caption, user=user)
        new_post.save()
        
        # Save image URLs to the Post instance or a related model if necessary
        for image_url in image_urls:
            # Example: Assume you have an `image_urls` field or related model
            new_post.images.create(url=image_url)
        
        # Assuming tags are comma-separated, split them and save them to the post
        if tags_str:
            tag_names = [tag.strip() for tag in tags_str.split(',')]
            for tag_name in tag_names:
                tag, created = Tag.objects.get_or_create(name=tag_name)
                new_post.tags.add(tag)
        
        messages.success(request, 'Post created successfully.')
        
        Notification.objects.create(
            user=user,
            title='New Post created successfully',
            description='View Post',
            target_link=f'/post/{new_post.post_id}/',
            icon='fas fa-check-circle mr-1'
        )
        
        # Redirect or show success message
        return redirect('home')  # Replace 'home' with your actual URL name for home page
    
    # If not a POST request, render the form or handle as needed
    return render(request, 'your_template.html')

@login_required
def like_post(request):
    post_id = request.POST.get('post_id')
    post = get_object_or_404(Post, post_id=post_id)

    liked = False
    like = Like.objects.filter(post=post, user=request.user)
    if like.exists():
        like.delete()
    else:
        Like.objects.create(post=post, user=request.user)
        liked = True

    total_likes = Like.objects.filter(post=post).count()

    return JsonResponse({'liked': liked, 'total_likes': total_likes})

@login_required
@require_POST
def save_post(request):
    post_id = request.POST.get('post_id')
    post = get_object_or_404(Post, post_id=post_id)

    saved = False
    save = Save.objects.filter(post=post, user=request.user)
    if save.exists():
        save.delete()
    else:
        Save.objects.create(post=post, user=request.user)
        saved = True

    total_saves = Save.objects.filter(post=post).count()

    return JsonResponse({'saved': saved, 'total_saves': total_saves})

@login_required
@require_POST
def comment_create(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    parent_id = request.POST.get('parent_id')
    content = request.POST.get('content')
    print(f"Parent ID: {parent_id}")
    print(f"Content: {content}")

    if content:
        parent_comment = None
        if parent_id:
            parent_comment = get_object_or_404(Comment, id=parent_id)
        
        new_comment = Comment(user=request.user, content=content, parent=parent_comment, post=post)
        new_comment.save()

        # Determine which template to render
        if parent_comment:
            # Render reply template
            comment_html = render_to_string('reply.html', {'reply': new_comment}, request=request)
        else:
            # Render main comment template
            comment_html = render_to_string('comment.html', {'comment': new_comment}, request=request)

        # Return JSON response with the new comment HTML
        return JsonResponse({'comment_html': comment_html})
    else:
        # Handle error case if content is empty
        return JsonResponse({'error': 'Content cannot be empty.'}, status=400)
    

@login_required
def notification_mark_as_read(request, notification_id):
    print(f"Marking notification {notification_id} as read...")
    
    notification = get_object_or_404(Notification, id=notification_id)
    notification.read = True
    notification.save()

    print(f"Notification {notification_id} marked as read.")

    # Redirect to the target link of the notification
    redirect_url = notification.target_link
    print(f"Redirecting to: {redirect_url}")
    return redirect(redirect_url)


@login_required
def explore(request):
    # Get the current user
    current_user = request.user

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


    # Get mutual people
    recommended_profiles = get_mutual_people(current_user)

    for user in recommended_profiles:
        if user.profile_picture_url:
            blob_path = user.profile_picture_url.split('social-app-50633.appspot.com/')[-1]
            user.profile_picture_url = generate_signed_url(blob_path)


    notifications = Notification.objects.filter(user=request.user).order_by('-created_at')
    unread_notifications = Notification.objects.filter(user=request.user, read=False).order_by('-created_at')
    unread_notifications_count = Notification.objects.filter(user=request.user, read=False).count()

    # Render the recommended profiles in a template
    context = {
        'recommended_profiles': recommended_profiles,
        'notifications': notifications,
        'unread_notifications_count': unread_notifications_count,
        'unread_notifications': unread_notifications,
        # 'current_user_profile_picture_url': current_user_profile_picture_url,
    }
    return render(request, 'explore.html', context)

def search_people(request):
    query = request.GET.get('q', '')
    current_username = request.user.username

    def generate_signed_url(blob_path):
        bucket = storage.bucket()
        blob = bucket.blob(blob_path)
        url = blob.generate_signed_url(
            version="v4",
            expiration=datetime.timedelta(hours=1),
            method="GET",
        )
        return url
    
    if query:
        users = User.objects.filter(username__icontains=query)[:10]

        results = []
        for user in users:
            user_data = {'username': user.username}
            if user.profile_picture_url:
                blob_path = user.profile_picture_url.split('social-app-50633.appspot.com/')[-1]
                user_data['profile_picture_url'] = generate_signed_url(blob_path)
            else:
                user_data['profile_picture_url'] = None
            results.append(user_data)

        return JsonResponse({'results': results, 'current_username': current_username})
    else:
        results = []
    
    return JsonResponse({'results': results, 'current_username': current_username}, safe=False)

@login_required
def saved_posts(request):
    # Fetch saved posts and prefetch related images
    saved_posts = Post.objects.filter(save__user=request.user).prefetch_related('images')
    notifications = Notification.objects.filter(user=request.user).order_by('-created_at')
    unread_notifications = Notification.objects.filter(user=request.user, read=False).order_by('-created_at')
    unread_notifications_count = Notification.objects.filter(user=request.user, read=False).count()

    mutual_people = get_mutual_people(request.user)
    # Retrieve the list of users that the current user follows
    following_users = User.objects.filter(following__user=request.user)

    
    
    # Generate signed URL for image
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

    current_user_profile_picture_url = None
    
    if request.user.profile_picture_url: 
        blob_path = request.user.profile_picture_url.split('social-app-50633.appspot.com/')[-1]
        current_user_profile_picture_url = generate_signed_url(blob_path)


    
    # Generate signed URLs for post images
    for post in saved_posts:
        if post.user.profile_picture_url: 
            blob_path = request.user.profile_picture_url.split('social-app-50633.appspot.com/')[-1]
            post.profile_picture_url = generate_signed_url(blob_path)
        for image in post.images.all():
            # Extract the blob path from the image URL
            blob_path = image.url.split('social-app-50633.appspot.com/')[-1]
            image.signed_url = generate_signed_url(blob_path)
    
    return render(request, 'saved_posts.html', {'saved_posts': saved_posts, 'notifications': notifications, 'unread_notifications_count': unread_notifications_count,'unread_notifications': unread_notifications,'following_users': following_users, 'recommended_profiles': mutual_people, 'current_profile_picture_url': current_user_profile_picture_url,})

@login_required
@require_POST
def remove_saved_post(request):
    post_id = request.POST.get('post_id')
    post = get_object_or_404(Post, post_id=post_id)
    Save.objects.filter(post=post, user=request.user).delete()
    return JsonResponse({'removed': True})


def hashtags(request, tagname):
    # Retrieve the specific tag matching the given tagname
    try:
        tag = Tag.objects.get(name=tagname)
    except Tag.DoesNotExist:
        return render(request, '404.html', status=404)  # Render 404 page if no matching tag found

    def generate_signed_url(blob_path):
        # Generate a signed URL for a given blob path
        bucket = storage.bucket()
        blob = bucket.blob(blob_path)
        url = blob.generate_signed_url(
            version="v4",
            expiration=datetime.timedelta(hours=1),
            method="GET",
        )
        return url

    # Fetch all posts associated with the tag
    hash_posts = Post.objects.filter(tags=tag).prefetch_related('images').order_by('-created_at')

    # Notifications for the current user
    notifications = Notification.objects.filter(user=request.user).order_by('-created_at')
    unread_notifications = notifications.filter(read=False)
    unread_notifications_count = unread_notifications.count()

    # Mutual people and following users
    mutual_people = get_mutual_people(request.user)
    following_users = User.objects.filter(following__user=request.user)

    # Generate signed URLs for mutual people and following users' profile pictures
    for user in mutual_people:
        if user.profile_picture_url:
            blob_path = user.profile_picture_url.split('social-app-50633.appspot.com/')[-1]
            user.profile_pic = generate_signed_url(blob_path)

    for user in following_users:
        if user.profile_picture_url:
            blob_path = user.profile_picture_url.split('social-app-50633.appspot.com/')[-1]
            user.profile_pic = generate_signed_url(blob_path)

    # Current user's profile picture URL
    current_user_profile_picture_url = None
    if request.user.profile_picture_url:
        blob_path = request.user.profile_picture_url.split('social-app-50633.appspot.com/')[-1]
        current_user_profile_picture_url = generate_signed_url(blob_path)

    # Generate signed URLs for post images
    for post in hash_posts:
        if post.user.profile_picture_url:
            blob_path = post.user.profile_picture_url.split('social-app-50633.appspot.com/')[-1]
            post.profile_picture_url = generate_signed_url(blob_path)
        for image in post.images.all():
            blob_path = image.url.split('social-app-50633.appspot.com/')[-1]
            image.signed_url = generate_signed_url(blob_path)

    return render(request, 'hashtags.html', {
        'tag_name': tagname,
        'posts': hash_posts,
        'notifications': notifications,
        'unread_notifications_count': unread_notifications_count,
        'unread_notifications': unread_notifications,
        'following_users': following_users,
        'recommended_profiles': mutual_people,
        'current_profile_picture_url': current_user_profile_picture_url,
    })