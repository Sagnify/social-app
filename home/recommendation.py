from django.utils import timezone
from datetime import timedelta
from django.db.models import Count, F, Q
from django.contrib.auth.decorators import login_required
from .models import *
from accounts.models import *
from django.contrib import messages
from authentication.models import User
import random

@login_required
def recommend_posts(request):
    # Check if the user follows anyone
    followed_users = User.objects.filter(following__user=request.user)
    
    if followed_users.exists():
        # Existing logic for users who follow others
        recommended_posts = recommend_posts_for_following_users(request, followed_users)
    else:
        # New logic for users who don't follow anyone
        recommended_posts = recommend_posts_for_new_users(request)
    
    # Shuffle the recommended posts
    shuffled_posts = shuffle_posts(recommended_posts)
    
    return shuffled_posts

def shuffle_posts(posts):
    posts_list = list(posts)
    
    # Shuffle the entire list
    random.shuffle(posts_list)

    return posts_list

def recommend_posts_for_following_users(request, followed_users):
    # Existing logic (unchanged)
    recent_threshold = timezone.now() - timedelta(days=7)
    
    recent_posts = Post.objects.filter(
        Q(like__user__in=followed_users) | Q(comments__user__in=followed_users),
        created_at__gte=recent_threshold
    ).exclude(user=request.user).annotate(
        like_count=Count('like', distinct=True),
        comment_count=Count('comments', distinct=True),
        interaction_score=F('like_count') + F('comment_count'),
        recency_score=F('created_at')
    ).order_by('-interaction_score', '-recency_score').prefetch_related('images')
    
    if recent_posts.count() >= 20:
        return recent_posts[:20]
    
    older_posts = Post.objects.filter(
        Q(like__user__in=followed_users) | Q(comments__user__in=followed_users),
        created_at__lt=recent_threshold
    ).exclude(user=request.user).annotate(
        like_count=Count('like', distinct=True),
        comment_count=Count('comments', distinct=True),
        interaction_score=F('like_count') + F('comment_count'),
        recency_score=F('created_at')
    ).order_by('-interaction_score', '-recency_score').prefetch_related('images')
    
    recommended_posts = list(recent_posts) + list(older_posts)
    
    return recommended_posts[:20]

def recommend_posts_for_new_users(request):
    # Define the threshold for recent posts (e.g., last 30 days)
    recent_threshold = timezone.now() - timedelta(days=30)
    
    # Get recent popular posts
    popular_posts = Post.objects.filter(
        created_at__gte=recent_threshold
    ).exclude(user=request.user).annotate(
        like_count=Count('like', distinct=True),
        comment_count=Count('comments', distinct=True),
        interaction_score=F('like_count') + F('comment_count')
    ).order_by('-interaction_score', '-created_at').prefetch_related('images')
    
    # If there are enough popular posts, return them
    if popular_posts.count() >= 20:
        return popular_posts[:20]
    
    # If not enough popular posts, get older posts to fill the gap
    older_posts = Post.objects.filter(
        created_at__lt=recent_threshold
    ).exclude(user=request.user).annotate(
        like_count=Count('like', distinct=True),
        comment_count=Count('comments', distinct=True),
        interaction_score=F('like_count') + F('comment_count')
    ).order_by('-interaction_score', '-created_at').prefetch_related('images')
    
    # Combine recent popular and older posts
    recommended_posts = list(popular_posts) + list(older_posts)
    
    return recommended_posts[:20]