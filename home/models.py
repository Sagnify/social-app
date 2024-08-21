from django.db import models
import uuid
from authentication.models import User

class Post(models.Model):
    
    post_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    # image = models.URLField(blank=True, null=True) 
    caption = models.CharField(max_length=300)
    user = models.ForeignKey('authentication.User', on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    tags = models.ManyToManyField('Tag', related_name='posts', blank=True)
    is_trending = models.BooleanField(default=False)

    def __str__(self):
        return self.caption
    
    def total_likes(self):
        return self.like_set.count()

class PostImage(models.Model):
    post = models.ForeignKey(Post, related_name='images', on_delete=models.CASCADE)
    url = models.URLField()
    
class Tag(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name
    
    

class Like(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('post', 'user')

    def __str__(self):
        return f'{self.user} likes {self.post}'
    
class Save(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    post = models.ForeignKey(Post, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ('post', 'user')

    def __str__(self):
        return f'{self.user} saves {self.post}'


class Comment(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    parent = models.ForeignKey('self', null=True, blank=True, related_name='replies', on_delete=models.CASCADE)
    post = models.ForeignKey('Post', on_delete=models.CASCADE, related_name='comments')  # Add this field

    def __str__(self):
        return f'Comment by {self.user.username}'

    class Meta:
        ordering = ['created_at']

class Notification(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    title = models.CharField(max_length=100)
    description = models.TextField()
    target_link = models.URLField()
    icon = models.URLField()
    read = models.BooleanField(default=False)

    def __str__(self):
        return self.title