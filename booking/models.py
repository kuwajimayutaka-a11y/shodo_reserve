from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.utils import timezone

# 1. 保護者/家族モデル (U-1: 兄弟予約機能の基盤)
class Family(models.Model):
    """
    保護者アカウントと、そのアカウントに紐づく生徒（兄弟）を管理するためのモデル。
    Djangoの標準Userモデルと1対1で紐づける。
    """
    user = models.OneToOneField(User, on_delete=models.CASCADE, verbose_name="保護者アカウント")
    phone_number = models.CharField(max_length=15, blank=True, verbose_name="連絡先電話番号")

    class Meta:
        verbose_name = "家族/保護者"
        verbose_name_plural = "家族/保護者"

    def __str__(self):
        return f"Family of {self.user.username}"

# 2. 生徒モデル (U-1: 兄弟)
class Student(models.Model):
    """
    実際に授業を受ける生徒（兄弟）のモデル。Familyに紐づく。
    """
    family = models.ForeignKey(Family, on_delete=models.CASCADE, verbose_name="保護者")
    name = models.CharField(max_length=100, verbose_name="生徒氏名")
    
    class Meta:
        verbose_name = "生徒"
        verbose_name_plural = "生徒"

    def __str__(self):
        return self.name

# 3. 授業枠モデル (A-1, A-2: 管理者による設定)
class LessonSlot(models.Model):
    """
    書道教室の授業枠（日時、定員、予約開始時刻）を管理するモデル。
    """
    title = models.CharField(max_length=200, verbose_name="授業名")
    start_time = models.DateTimeField(verbose_name="開始日時")
    end_time = models.DateTimeField(verbose_name="終了日時")
    capacity = models.PositiveIntegerField(default=1, verbose_name="定員")
    reservation_start_time = models.DateTimeField(verbose_name="予約開始時刻")

    class Meta:
        verbose_name = "授業枠"
        verbose_name_plural = "授業枠"
        ordering = ["start_time"]

    def __str__(self):
        return f"{self.title} ({self.start_time.strftime('%Y/%m/%d %H:%M')})"

    def is_reservable(self):
        """現在予約可能かどうかを判定"""
        return timezone.now() >= self.reservation_start_time and self.available_slots() > 0

    def available_slots(self):
        """残りの予約可能枠数を計算"""
        reserved_count = self.reservation_set.count()
        return self.capacity - reserved_count

# 4. 予約モデル (S-1: 生徒による予約)
class Reservation(models.Model):
    """
    生徒による授業枠の予約を管理するモデル。
    """
    lesson_slot = models.ForeignKey(LessonSlot, on_delete=models.CASCADE, verbose_name="授業枠")
    student = models.ForeignKey(Student, on_delete=models.CASCADE, verbose_name="予約生徒")
    reserved_at = models.DateTimeField(auto_now_add=True, verbose_name="予約日時")

    class Meta:
        verbose_name = "予約"
        verbose_name_plural = "予約"
        # 同じ授業枠に同じ生徒が二重予約できないようにする
        unique_together = ("lesson_slot", "student")

    def __str__(self):
        return f"{self.student.name} - {self.lesson_slot.title}"

# 5. 補欠モデル (S-2: 補欠機能)
class Waitlist(models.Model):
    """
    定員オーバー時の補欠予約を管理するモデル。
    """
    lesson_slot = models.ForeignKey(LessonSlot, on_delete=models.CASCADE, verbose_name="授業枠")
    student = models.ForeignKey(Student, on_delete=models.CASCADE, verbose_name="補欠生徒")
    waitlisted_at = models.DateTimeField(auto_now_add=True, verbose_name="補欠登録日時")

    class Meta:
        verbose_name = "補欠"
        verbose_name_plural = "補欠"
        # 補欠は登録順に処理するため、登録日時でソート
        ordering = ["waitlisted_at"]
        # 同じ授業枠に同じ生徒が二重に補欠登録できないようにする
        unique_together = ("lesson_slot", "student")

    def __str__(self):
        return f"補欠: {self.student.name} - {self.lesson_slot.title}"
