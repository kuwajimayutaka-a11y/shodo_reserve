from django.contrib.auth.views import LoginView
from django.contrib.auth.forms import AuthenticationForm
from .models import Family


class LoginForm(AuthenticationForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'example@email.com',
        })
        self.fields['password'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'パスワード',
        })


class CustomLoginView(LoginView):
    template_name = 'registration/login.html'
    form_class = LoginForm

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
