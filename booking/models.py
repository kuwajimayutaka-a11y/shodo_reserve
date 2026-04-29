from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.conf import settings
from django.utils import timezone


class CustomUserManager(BaseUserManager):
    def create_user(self, email, name, password=None, **extra_fields):
        if not email:
            raise ValueError('メールアドレスは必須です')
        email = self.normalize_email(email)
        user = self.model(email=email, name=name, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, name, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)
        return self.create_user(email, name, password, **extra_fields)


class CustomUser(AbstractUser):
    username = None
    email = models.EmailField(unique=True, verbose_name='メールアドレス')
    name = models.CharField(max_length=100, verbose_name='氏名')

    objects = CustomUserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['name']

    class Meta:
        verbose_name = 'ユーザー'
        verbose_name_plural = 'ユーザー'

    def __str__(self):
        return self.email


class Family(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        verbose_name="保護者アカウント"
    )
    phone_number = models.CharField(max_length=15, blank=True, verbose_name="連絡先電話番号")

    class Meta:
        verbose_name = "家族/保護者"
        verbose_name_plural = "家族/保護者"

    def __str__(self):
        return f"Family of {self.user.name}"


class Student(models.Model):
    family = models.ForeignKey(Family, on_delete=models.CASCADE, verbose_name="保護者")
    name = models.CharField(max_length=100, verbose_name="生徒氏名")

    class Meta:
        verbose_name = "生徒"
        verbose_name_plural = "生徒"

    def __str__(self):
        return self.name


class LessonSlot(models.Model):
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
        return timezone.now() >= self.reservation_start_time and self.available_slots() > 0

    def available_slots(self):
        return self.capacity - self.reservation_set.count()


class Reservation(models.Model):
    lesson_slot = models.ForeignKey(LessonSlot, on_delete=models.CASCADE, verbose_name="授業枠")
    student = models.ForeignKey(Student, on_delete=models.CASCADE, verbose_name="予約生徒")
    reserved_at = models.DateTimeField(auto_now_add=True, verbose_name="予約日時")

    class Meta:
        verbose_name = "予約"
        verbose_name_plural = "予約"
        unique_together = ("lesson_slot", "student")

    def __str__(self):
        return f"{self.student.name} - {self.lesson_slot.title}"


class Waitlist(models.Model):
    lesson_slot = models.ForeignKey(LessonSlot, on_delete=models.CASCADE, verbose_name="授業枠")
    student = models.ForeignKey(Student, on_delete=models.CASCADE, verbose_name="補欠生徒")
    waitlisted_at = models.DateTimeField(auto_now_add=True, verbose_name="補欠登録日時")

    class Meta:
        verbose_name = "補欠"
        verbose_name_plural = "補欠"
        ordering = ["waitlisted_at"]
        unique_together = ("lesson_slot", "student")

    def __str__(self):
        return f"補欠: {self.student.name} - {self.lesson_slot.title}"
