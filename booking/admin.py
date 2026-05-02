from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser, Family, Student, LessonSlot, Reservation, Waitlist


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    model = CustomUser
    list_display = ('email', 'name', 'is_staff', 'is_active', 'date_joined')
    list_filter = ('is_staff', 'is_active', 'is_superuser')
    fieldsets = (
        (None,       {'fields': ('email', 'password')}),
        ('個人情報', {'fields': ('name',)}),
        ('権限',     {'fields': ('is_staff', 'is_active', 'is_superuser', 'groups', 'user_permissions')}),
        ('日付',     {'fields': ('last_login', 'date_joined')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'name', 'password1', 'password2', 'is_staff', 'is_active'),
        }),
    )
    search_fields = ('email', 'name')
    ordering = ('email',)
    # username フィールドが存在しないため親クラスの参照を無効化
    filter_horizontal = ('groups', 'user_permissions')


class StudentInline(admin.TabularInline):
    model = Student
    extra = 1
    fields = ('name',)


@admin.register(Family)
class FamilyAdmin(admin.ModelAdmin):
    list_display = ('get_name', 'get_email', 'phone_number', 'get_student_count')
    search_fields = ('user__email', 'user__name', 'phone_number')
    inlines = [StudentInline]

    @admin.display(description='保護者名')
    def get_name(self, obj):
        return obj.user.name

    @admin.display(description='メール')
    def get_email(self, obj):
        return obj.user.email

    @admin.display(description='生徒数')
    def get_student_count(self, obj):
        return obj.student_set.count()


@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = ('name', 'get_family_name', 'get_reservation_count')
    search_fields = ('name', 'family__user__email', 'family__user__name')

    @admin.display(description='保護者')
    def get_family_name(self, obj):
        return obj.family.user.name

    @admin.display(description='予約数')
    def get_reservation_count(self, obj):
        return obj.reservation_set.count()


@admin.register(LessonSlot)
class LessonSlotAdmin(admin.ModelAdmin):
    list_display = ('title', 'start_time', 'end_time', 'capacity', 'available_slots', 'reservation_start_time')
    list_filter = ('title',)
    search_fields = ('title',)
    date_hierarchy = 'start_time'
    ordering = ('-start_time',)


@admin.register(Reservation)
class ReservationAdmin(admin.ModelAdmin):
    list_display = ('get_student', 'get_family', 'get_lesson', 'get_lesson_date', 'reserved_at')
    list_filter = ('lesson_slot__title',)
    search_fields = ('student__name', 'lesson_slot__title', 'student__family__user__name')
    date_hierarchy = 'reserved_at'

    @admin.display(description='生徒')
    def get_student(self, obj):
        return obj.student.name

    @admin.display(description='保護者')
    def get_family(self, obj):
        return obj.student.family.user.name

    @admin.display(description='授業')
    def get_lesson(self, obj):
        return obj.lesson_slot.title or '書道教室'

    @admin.display(description='授業日時')
    def get_lesson_date(self, obj):
        return obj.lesson_slot.start_time.strftime('%Y/%m/%d %H:%M')


@admin.register(Waitlist)
class WaitlistAdmin(admin.ModelAdmin):
    list_display = ('get_student', 'get_lesson', 'waitlisted_at')
    search_fields = ('student__name', 'lesson_slot__title')
    readonly_fields = ('waitlisted_at',)

    @admin.display(description='生徒')
    def get_student(self, obj):
        return obj.student.name

    @admin.display(description='授業')
    def get_lesson(self, obj):
        return obj.lesson_slot.title or '書道教室'
