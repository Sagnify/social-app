from django.db import models
from authentication.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver

# Create your models here.
class Follow(models.Model):
    user = models.ForeignKey(User, related_name='follower', on_delete=models.CASCADE)
    following = models.ForeignKey(User, related_name='following', on_delete=models.CASCADE)

    class Meta:
        unique_together = ('user', 'following')
        indexes = [
            models.Index(fields=['user', 'following']),
        ]

    def __str__(self):
        return f"{self.user.username} follows {self.following.username}"

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    # profile_pic = models.ImageField(upload_to='profile_pics/', null=True, blank=True)
    first_name = models.CharField(max_length=30, blank=True)
    last_name = models.CharField(max_length=30, blank=True)
    bio = models.TextField(blank=True)
    location = models.CharField(max_length=100, blank=True)
    x_link = models.URLField(blank=True)
    yt_link = models.URLField(blank=True)
    fb_link = models.URLField(blank=True)
    insta_link = models.URLField(blank=True)
    date_of_birth = models.DateField(null=True, blank=True)

    def __str__(self):
        return self.user.username

# Signal to create or update the user profile


@receiver(post_save, sender=User)
def create_or_update_user_profile(instance, **kwargs):
    UserProfile.objects.get_or_create(user=instance)
    instance.userprofile.save()