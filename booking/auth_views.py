from django.contrib.auth.views import (
    LoginView,
    PasswordResetView,
    PasswordResetConfirmView,
)
from django.contrib.auth.forms import (
    AuthenticationForm,
    PasswordResetForm,
    SetPasswordForm,
)
from django.urls import reverse_lazy
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


class StyledPasswordResetForm(PasswordResetForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['email'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'example@email.com',
        })


class StyledSetPasswordForm(SetPasswordForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['new_password1'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': '新しいパスワード',
        })
        self.fields['new_password2'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': '新しいパスワード（確認）',
        })


class CustomPasswordResetView(PasswordResetView):
    template_name = 'registration/password_reset_form.html'
    email_template_name = 'registration/password_reset_email.txt'
    subject_template_name = 'registration/password_reset_subject.txt'
    form_class = StyledPasswordResetForm
    success_url = reverse_lazy('password_reset_done')


class CustomPasswordResetConfirmView(PasswordResetConfirmView):
    template_name = 'registration/password_reset_confirm.html'
    form_class = StyledSetPasswordForm
    success_url = reverse_lazy('password_reset_complete')
