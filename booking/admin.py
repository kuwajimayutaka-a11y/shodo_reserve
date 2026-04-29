from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser, Family, Student, LessonSlot, Reservation, Waitlist


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    model = CustomUser
    list_display = ('email', 'name', 'is_staff', 'is_active')
    list_filter = ('is_staff', 'is_active')
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('個人情報', {'fields': ('name',)}),
        ('権限', {'fields': ('is_staff', 'is_active', 'is_superuser', 'groups', 'user_permissions')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'name', 'password1', 'password2', 'is_staff', 'is_active'),
        }),
    )
    search_fields = ('email', 'name')
    ordering = ('email',)


class StudentInline(admin.TabularInline):
    model = Student
    extra = 1


@admin.register(Family)
class FamilyAdmin(admin.ModelAdmin):
    list_display = ('user', 'phone_number')
    search_fields = ('user__email', 'user__name', 'phone_number')
    inlines = [StudentInline]


@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = ('name', 'family')
    list_filter = ('family',)
    search_fields = ('name', 'family__user__email', 'family__user__name')


@admin.register(LessonSlot)
class LessonSlotAdmin(admin.ModelAdmin):
    list_display = ('title', 'start_time', 'capacity', 'reservation_start_time', 'available_slots')
    list_filter = ('start_time',)
    search_fields = ('title',)


@admin.register(Reservation)
class ReservationAdmin(admin.ModelAdmin):
    list_display = ('lesson_slot', 'student', 'reserved_at')
    list_filter = ('lesson_slot__title', 'reserved_at')
    search_fields = ('student__name', 'lesson_slot__title')


@admin.register(Waitlist)
class WaitlistAdmin(admin.ModelAdmin):
    list_display = ('lesson_slot', 'student', 'waitlisted_at')
    list_filter = ('lesson_slot__title',)
    search_fields = ('student__name', 'lesson_slot__title')
    readonly_fields = ('waitlisted_at',)
