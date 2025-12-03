from django.contrib.auth.views import LoginView
from django.shortcuts import redirect

class CustomLoginView(LoginView):
    """
    カスタムログインビュー
    管理者の場合は管理者ダッシュボードへ、
    一般ユーザーの場合は予約カレンダーへリダイレクト
    """
    template_name = 'registration/login.html'
    
    def get_success_url(self):
        # ログインしたユーザーが管理者かどうかをチェック
        if self.request.user.is_staff:
            return '/admin-dashboard/'
        else:
            return '/calendar/'
