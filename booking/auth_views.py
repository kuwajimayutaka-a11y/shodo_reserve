from django.contrib.auth.views import LoginView
from .models import Family


class CustomLoginView(LoginView):
    template_name = 'registration/login.html'

    def get_success_url(self):
        user = self.request.user
        if user.is_staff:
            return '/admin-dashboard/'
        try:
            if user.family.student_set.exists():
                return '/calendar/'
        except Family.DoesNotExist:
            pass
        return '/students/'
