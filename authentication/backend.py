from .models import User

class CustomAuthBackend:
    def authenticate(self, request, email=None, password=None):
        try:
            user = User.objects.get(email=email)
            if user.password == password:
                return user
            else:
                return None
        except User.DoesNotExist:
            return None

    def get_user(self, id):
        try:
            return User.objects.get(pk=id)
        except User.DoesNotExist:
            return None
