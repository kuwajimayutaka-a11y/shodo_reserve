# 管理者機能実装設計

## 要件
1. 管理者でログインした場合、管理者ダッシュボードにリダイレクト
2. 管理者もカレンダーと生徒情報を見れるように
3. 管理者はすべての生徒を予約できるように

## 現状分析
- Djangoベースの書道教室予約システム
- 既存の管理者機能: `admin_views.py`で実装済み
- 管理者判定: `is_superuser`フラグで判定
- 既存の管理者機能:
  - ダッシュボード (`admin_dashboard`)
  - 授業枠管理
  - 予約一覧
  - 生徒管理

## 実装内容

### 1. ログイン後のリダイレクト処理
- `views.py`にカスタムログインビューを追加、または既存のログイン成功後の処理を修正
- `settings.py`の`LOGIN_REDIRECT_URL`を動的に変更
- ミドルウェアまたはシグナルでログイン後の処理をカスタマイズ

**実装方針**: カスタムログインビューを作成し、ユーザーの権限に応じてリダイレクト先を変更

### 2. 管理者用カレンダー表示
- `admin_views.py`に`admin_reservation_calendar`ビューを追加
- 既存の`reservation_calendar`テンプレートを参考に管理者用テンプレートを作成
- すべての生徒の予約状況を表示

### 3. 管理者用生徒情報表示
- 既存の`admin_student_management`ビューを拡張
- 管理者ダッシュボードから簡単にアクセスできるようにナビゲーションを改善

### 4. 管理者による全生徒予約機能
- `admin_views.py`に`admin_reserve_lesson`ビューを追加
- 全生徒のリストから選択して予約できる機能
- カレンダー画面から直接予約できるUI

## ファイル変更リスト
1. `booking/views.py` - カスタムログインビュー追加
2. `booking/admin_views.py` - 管理者用カレンダーと予約機能追加
3. `booking/urls.py` - 新しいURLパターン追加
4. `booking/templates/booking/admin/calendar.html` - 管理者用カレンダーテンプレート作成
5. `booking/templates/booking/admin/dashboard.html` - ナビゲーション改善
6. `booking/templates/registration/login.html` - ログイン処理の調整(必要に応じて)
