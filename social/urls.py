"""
URL configuration for social project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.conf import settings
from django.contrib import admin
from django.urls import include, path
from django.conf.urls.static import static
from home.views import *
from authentication.views import *
from accounts.views import *
from chat.views import *


# from django.contrib.auth import login
# from django.contrib.auth import logout

urlpatterns = [
    path('', home, name='home'),
    path('login/', loginpage, name='login'),
    # path('login/welcome/', welcome, name='welcome'),
    path('logout/', logout_view, name='logout'),
    path('register/', register_step1, name='register_step1'),
    path('register/step2/', register_step2, name='register_step2'),
    path('create/', create_post, name='create_post'),
    path('like/', like_post, name='like_post'),
    path('comment/create/<int:post_id>/' , comment_create, name='comment_create'),
    path('p/@<str:username>/', profile, name='profile'),
    path('follow/<str:username>/', follow, name='follow_user'),
    path('search-users/', search_users, name='search_users'),
    path('post/<str:post_id>/', post, name='post'),
    path('mark_notification_read/<int:notification_id>/', notification_mark_as_read, name='mark_notification_read'),
    path('chat/', chat_view, name='chat'),
    path('explore/', explore, name='explore'),
    path('search_people/', search_people, name='search_people'),
    path('save_post/', save_post, name='save_post'),
    path('saves/', saved_posts, name='saves'),
    path('remove_saved_post/', remove_saved_post, name='remove_saved_post'),
    path('update-profile-picture/', update_profile_picture, name='update_profile_picture'),
    path('p/@<str:username>/edit/', edit_profile, name='edit_profile'),
    path('hashtags/<str:tagname>/', hashtags, name='hashtag'),
    path('', include('pwa.urls')),
    path('admin/', admin.site.urls),
]

# Serve static files during development
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)