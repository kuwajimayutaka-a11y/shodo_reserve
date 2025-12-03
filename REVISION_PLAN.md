# 書道教室予約システム - 改修計画書

## 概要
前回実装した管理者機能に対して、4つの主要な改修を実施します。

---

## 改修1: Select2の導入（UI/UX改善）

### 目的
生徒数が多い場合に、プルダウンリストから生徒を検索・選択しやすくするため、Select2ライブラリを導入します。

### 対象画面
1. **一般ユーザー用カレンダー** (`/calendar/`)
   - 「予約する生徒」プルダウン
   - 「補欠登録する生徒」プルダウン

2. **管理者用カレンダー** (`/admin-dashboard/calendar/`)
   - 「予約する生徒」プルダウン

### 実装内容
- Select2ライブラリをテンプレートに追加
- JavaScriptで各プルダウンをSelect2で初期化
- 検索機能の有効化
- スタイリングの調整

### 変更ファイル
- `booking/templates/base.html` - Select2 CDNの追加
- `booking/templates/booking/calendar.html` - Select2の初期化
- `booking/templates/booking/admin/calendar.html` - Select2の初期化

---

## 改修2: 管理者アクセスエラーの修正（バグ修正）

### 問題
管理者が一般ユーザー向けの画面にアクセスするとエラーが発生します。

### 原因
- `view_students` ビュー: `Family.objects.get(user=request.user)` で、管理者に紐づくFamilyが存在しない場合、404エラーが発生
- `reservation_calendar` ビュー: 同様の理由でエラーが発生

### 解決方法
1. 管理者がこれらのビューにアクセスした場合、特別な処理を実施
2. 管理者の場合は全生徒・全予約を表示するか、管理者用画面へリダイレクト
3. または、管理者にもFamilyアカウントを自動作成

### 実装方針
- `view_students` ビュー: 管理者の場合は生徒管理画面へリダイレクト
- `reservation_calendar` ビュー: 管理者の場合は管理者用カレンダーへリダイレクト

### 変更ファイル
- `booking/views.py` - `view_students`と`reservation_calendar`ビューの修正

---

## 改修3: 管理者によるユーザー作成機能（新機能）

### 目的
管理者が新しい保護者アカウント（ユーザー）を作成し、初期パスワードを設定できるようにします。

### 機能要件
1. 管理者ダッシュボードから「ユーザー追加」ページにアクセス
2. ユーザー名、メールアドレス、初期パスワードを入力
3. ユーザーアカウントを作成
4. 自動的にFamilyアカウントも作成
5. 作成完了後、ユーザー情報を表示（パスワード確認用）

### 実装内容
- `admin_views.py`に`create_user_admin`ビューを追加
- `UserCreationForm`の代わりにカスタムフォームを使用
- テンプレート作成: `admin/create_user.html`
- URLパターン追加: `/admin-dashboard/users/add/`

### 変更ファイル
- `booking/forms.py` - `UserCreationForm`の拡張フォーム追加
- `booking/admin_views.py` - `create_user_admin`ビュー追加
- `booking/urls.py` - URLパターン追加
- `booking/templates/booking/admin/create_user.html` - テンプレート作成
- `booking/templates/booking/admin/dashboard.html` - リンク追加

---

## 改修4: 生徒追加申請・承認フロー（新機能）

### 現状の問題
ユーザーが自由に生徒を追加できるため、不正な生徒登録や悪用の可能性があります。

### 解決方法
生徒追加を申請制にし、管理者の承認を必須にします。

### フロー概要

**ユーザー側:**
1. 「生徒を追加」ボタンをクリック
2. 生徒名を入力して申請
3. 申請完了メッセージを表示
4. 管理者の承認待ちであることを通知

**管理者側:**
1. ダッシュボードに「生徒追加申請」の件数を表示
2. 「生徒追加申請」ページで申請一覧を確認
3. 各申請に対して「承認」または「却下」を選択
4. 承認すると生徒が登録される
5. 却下すると申請が削除される

### 新規モデル: StudentAdditionRequest

```python
class StudentAdditionRequest(models.Model):
    """生徒追加申請"""
    family = models.ForeignKey(Family, on_delete=models.CASCADE)
    student_name = models.CharField(max_length=100)
    requested_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(
        max_length=10,
        choices=[('pending', '待機中'), ('approved', '承認'), ('rejected', '却下')],
        default='pending'
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    approved_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL)
```

### 実装内容

**モデル:**
- `StudentAdditionRequest`モデルを作成
- マイグレーションファイルを生成

**ビュー:**
- `add_student`ビューを修正（申請を作成）
- `admin_student_addition_requests`ビューを追加（申請一覧）
- `approve_student_request`ビューを追加（承認処理）
- `reject_student_request`ビューを追加（却下処理）

**テンプレート:**
- `booking/add_student.html` - 申請フォーム
- `booking/admin/student_addition_requests.html` - 申請一覧（管理者）

**URL:**
- `/add-student/` - 生徒追加申請（ユーザー）
- `/admin-dashboard/student-requests/` - 申請一覧（管理者）
- `/admin-dashboard/student-requests/<id>/approve/` - 承認（管理者）
- `/admin-dashboard/student-requests/<id>/reject/` - 却下（管理者）

### 変更ファイル
- `booking/models.py` - `StudentAdditionRequest`モデル追加
- `booking/admin.py` - モデル登録
- `booking/views.py` - `add_student`ビュー修正
- `booking/admin_views.py` - 申請管理ビュー追加
- `booking/urls.py` - URLパターン追加
- `booking/templates/booking/add_student.html` - テンプレート修正
- `booking/templates/booking/admin/student_addition_requests.html` - テンプレート作成
- `booking/templates/booking/admin/dashboard.html` - 申請件数表示

---

## 実装スケジュール

| フェーズ | 内容 | 優先度 |
|---------|------|--------|
| 1 | Select2の導入 | 高 |
| 2 | 管理者アクセスエラーの修正 | 高 |
| 3 | 管理者によるユーザー作成機能 | 中 |
| 4-6 | 生徒追加申請フロー | 高 |

---

## 技術スタック

- **フロントエンド**: Select2 (CDN)
- **バックエンド**: Django
- **データベース**: SQLite（開発環境）/ PostgreSQL（本番環境）

---

## セキュリティ考慮事項

1. **ユーザー作成時のパスワード管理**
   - 初期パスワードは安全に表示（一度だけ）
   - ユーザーに初回ログイン時のパスワード変更を促す

2. **生徒追加申請の承認**
   - 管理者のみが承認可能
   - 承認者と承認日時を記録

3. **アクセス制御**
   - 管理者機能は`@user_passes_test(is_admin)`で保護
   - ユーザー機能は`@login_required`で保護

---

## テスト項目

- [ ] Select2が正常に動作するか
- [ ] 管理者が一般ユーザー向けページにアクセスしてもエラーが出ないか
- [ ] 管理者がユーザーを作成できるか
- [ ] ユーザーが生徒追加申請を送信できるか
- [ ] 管理者が申請を承認・却下できるか
- [ ] 承認後に生徒が登録されるか
