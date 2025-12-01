from django.contrib import admin
from .models import Family, Student, LessonSlot, Reservation, Waitlist

# 家族/保護者モデルのインライン表示
class StudentInline(admin.TabularInline):
    model = Student
    extra = 1 # 新しい生徒を1人追加できるようにする

@admin.register(Family)
class FamilyAdmin(admin.ModelAdmin):
    list_display = ('user', 'phone_number')
    search_fields = ('user__username', 'phone_number')
    inlines = [StudentInline]

@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = ('name', 'family')
    list_filter = ('family',)
    search_fields = ('name', 'family__user__username')

@admin.register(LessonSlot)
class LessonSlotAdmin(admin.ModelAdmin):
    list_display = ('title', 'start_time', 'capacity', 'reservation_start_time', 'available_slots')
    list_filter = ('start_time', 'reservation_start_time')
    search_fields = ('title',)

@admin.register(Reservation)
class ReservationAdmin(admin.ModelAdmin):
    list_display = ('lesson_slot', 'student', 'reserved_at')
    list_filter = ('lesson_slot__title', 'reserved_at')
    search_fields = ('student__name', 'lesson_slot__title')

@admin.register(Waitlist)
class WaitlistAdmin(admin.ModelAdmin):
    list_display = ('lesson_slot', 'student', 'waitlisted_at')
    list_filter = ('lesson_slot__title', 'waitlisted_at')
    search_fields = ('student__name', 'lesson_slot__title')
    readonly_fields = ('waitlisted_at',)
