from django.contrib.auth.models import AbstractBaseUser, BaseUserManager
from django.db import models
from django.contrib.auth.hashers import make_password, check_password
from django.utils import timezone

class UserManager(BaseUserManager):
    def create_user(self, username, email, password=None):
        if not email:
            raise ValueError('Users must have an email address')

        user = self.model(
            username=username,
            email=self.normalize_email(email),
        )
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, username, email, password=None):
        user = self.create_user(
            username=username,
            email=email,
            password=password,
        )
        user.is_superuser = True
        user.is_staff = True
        user.save(using=self._db)
        return user

class User(AbstractBaseUser):
    username = models.CharField(max_length=128, unique=True)
    profile_picture_url = models.URLField(blank=True, null=True)
    email = models.EmailField(max_length=264, unique=True)
    created_at = models.DateTimeField(default=timezone.now)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)

    objects = UserManager()

    USERNAME_FIELD = 'username'
    EMAIL_FIELD = 'email'
    REQUIRED_FIELDS = ['email']  # Add any additional required fields here (other than 'username')

    def __str__(self):
        return self.username

    def set_password(self, password):
        """Hashes the password before saving."""
        self.password = make_password(password)

    def check_password(self, password):
        """Returns True if the password is correct."""
        return check_password(password, self.password)

    def save(self, *args, **kwargs):
        """Override save method to ensure the password is hashed."""
        if not self.pk and not self.password.startswith('pbkdf2_'):  # New user or plain text password
            self.set_password(self.password)
        super().save(*args, **kwargs)
