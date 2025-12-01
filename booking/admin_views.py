from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from datetime import timedelta, datetime
from .forms import LessonSlotCreateForm, LessonSlotEditForm, StudentForm
from .models import LessonSlot, Reservation, Waitlist, Family, Student
from django.utils import timezone
from django.contrib.auth.models import User

def is_admin(user):
    """管理者権限チェック"""
    return user.is_superuser

# 管理者トップページ
@login_required
@user_passes_test(is_admin)
def admin_dashboard(request):
    """管理者ダッシュボード"""
    total_lessons = LessonSlot.objects.count()
    upcoming_lessons = LessonSlot.objects.filter(start_time__gte=timezone.now()).count()
    total_reservations = Reservation.objects.count()
    total_students = Student.objects.count()
    total_families = Family.objects.count()
    
    context = {
        'total_lessons': total_lessons,
        'upcoming_lessons': upcoming_lessons,
        'total_reservations': total_reservations,
        'total_students': total_students,
        'total_families': total_families,
    }
    return render(request, 'booking/admin/dashboard.html', context)

# 授業枠一括作成機能
@login_required
@user_passes_test(is_admin)
def create_lesson_slots(request):
    """授業枠一括作成"""
    if request.method == "POST":
        form = LessonSlotCreateForm(request.POST)
        if form.is_valid():
            data = form.cleaned_data
            
            start_date = data["start_date"]
            end_date = data["end_date"]
            days_of_week = [int(d) for d in data["days_of_week"]]
            time_slots = data["time_slots"]
            capacity = data["capacity"]
            title = data["title"]
            reservation_start_datetime = data["reservation_start_datetime"]

            # 授業名が空の場合のデフォルト設定
            if not title:
                title = "書道教室"

            current_date = start_date
            created_count = 0
            
            # 時間スロットをパース
            time_pairs = []
            for line in time_slots.strip().split('\n'):
                line = line.strip()
                if line and '-' in line:
                    try:
                        start_str, end_str = line.split('-')
                        start_time = datetime.strptime(start_str.strip(), '%H:%M').time()
                        end_time = datetime.strptime(end_str.strip(), '%H:%M').time()
                        time_pairs.append((start_time, end_time))
                    except ValueError:
                        continue
            
            # 期間内の日付を反復処理
            while current_date <= end_date:
                # 選択された曜日であるかチェック
                if current_date.weekday() in days_of_week:
                    # 各時間スロットに対して授業枠を作成
                    for start_time, end_time in time_pairs:
                        lesson_start_dt = datetime.combine(current_date, start_time, tzinfo=timezone.get_current_timezone())
                        lesson_end_dt = datetime.combine(current_date, end_time, tzinfo=timezone.get_current_timezone())
                        
                        # 授業枠を作成
                        LessonSlot.objects.create(
                            title=title,
                            start_time=lesson_start_dt,
                            end_time=lesson_end_dt,
                            capacity=capacity,
                            reservation_start_time=reservation_start_datetime
                        )
                        created_count += 1
                
                # 次の日へ
                current_date += timedelta(days=1)

            messages.success(request, f"授業枠を {created_count} 件作成しました。")
            return redirect("admin_lesson_list")
    else:
        form = LessonSlotCreateForm()

    context = {
        "form": form
    }
    return render(request, "booking/admin/create_lesson.html", context)

# 授業枠一覧表示
@login_required
@user_passes_test(is_admin)
def lesson_list(request):
    """授業枠一覧"""
    lessons = LessonSlot.objects.all().order_by('-start_time')
    
    context = {
        'lessons': lessons
    }
    return render(request, 'booking/admin/lesson_list.html', context)

# 授業枠個別編集
@login_required
@user_passes_test(is_admin)
def edit_lesson_slot(request, lesson_id):
    """授業枠個別編集"""
    lesson = get_object_or_404(LessonSlot, pk=lesson_id)
    
    if request.method == 'POST':
        form = LessonSlotEditForm(request.POST, instance=lesson)
        if form.is_valid():
            form.save()
            messages.success(request, f"授業枠「{lesson.title}」を更新しました。")
            return redirect('admin_lesson_list')
    else:
        form = LessonSlotEditForm(instance=lesson)
    
    context = {
        'form': form,
        'lesson': lesson
    }
    return render(request, 'booking/admin/edit_lesson.html', context)

# 授業枠削除
@login_required
@user_passes_test(is_admin)
def delete_lesson_slot(request, lesson_id):
    """授業枠削除"""
    lesson = get_object_or_404(LessonSlot, pk=lesson_id)
    
    if request.method == 'POST':
        lesson_title = lesson.title
        lesson.delete()
        messages.success(request, f"授業枠「{lesson_title}」を削除しました。")
        return redirect('admin_lesson_list')
    
    context = {
        'lesson': lesson
    }
    return render(request, 'booking/admin/delete_lesson.html', context)

# 授業枠個別作成
@login_required
@user_passes_test(is_admin)
def create_lesson_single(request):
    """授業枠個別作成"""
    if request.method == "POST":
        form = LessonSlotEditForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "授業枠を作成しました。")
            return redirect("admin_lesson_list")
    else:
        form = LessonSlotEditForm()

    context = {
        "form": form
    }
    return render(request, "booking/admin/create_lesson_single.html", context)

# 予約一覧表示
@login_required
@user_passes_test(is_admin)
def reservation_list(request):
    """予約一覧"""
    reservations = Reservation.objects.all().order_by('-reserved_at')
    
    context = {
        'reservations': reservations
    }
    return render(request, 'booking/admin/reservation_list.html', context)

# 生徒管理一覧
@login_required
@user_passes_test(is_admin)
def student_management(request):
    """生徒管理一覧"""
    families = Family.objects.all().select_related('user').prefetch_related('student_set')
    
    context = {
        'families': families
    }
    return render(request, 'booking/admin/student_management.html', context)

# 生徒追加
@login_required
@user_passes_test(is_admin)
def add_student_admin(request, family_id):
    """管理者による生徒追加"""
    family = get_object_or_404(Family, pk=family_id)
    
    if request.method == 'POST':
        form = StudentForm(request.POST)
        if form.is_valid():
            student = form.save(commit=False)
            student.family = family
            student.save()
            messages.success(request, f"生徒「{student.name}」を追加しました。")
            return redirect('admin_student_management')
    else:
        form = StudentForm()
    
    context = {
        'form': form,
        'family': family
    }
    return render(request, 'booking/admin/add_student.html', context)

# 生徒編集
@login_required
@user_passes_test(is_admin)
def edit_student_admin(request, student_id):
    """管理者による生徒編集"""
    student = get_object_or_404(Student, pk=student_id)
    
    if request.method == 'POST':
        form = StudentForm(request.POST, instance=student)
        if form.is_valid():
            form.save()
            messages.success(request, f"生徒「{student.name}」を更新しました。")
            return redirect('admin_student_management')
    else:
        form = StudentForm(instance=student)
    
    context = {
        'form': form,
        'student': student
    }
    return render(request, 'booking/admin/edit_student.html', context)

# 生徒削除
@login_required
@user_passes_test(is_admin)
def delete_student_admin(request, student_id):
    """管理者による生徒削除"""
    student = get_object_or_404(Student, pk=student_id)
    
    if request.method == 'POST':
        student_name = student.name
        student.delete()
        messages.success(request, f"生徒「{student_name}」を削除しました。")
        return redirect('admin_student_management')
    
    context = {
        'student': student
    }
    return render(request, 'booking/admin/delete_student.html', context)


# 予約キャンセル(管理者用)
@login_required
@user_passes_test(is_admin)
def cancel_reservation_admin(request, reservation_id):
    """管理者による予約キャンセル"""
    reservation = get_object_or_404(Reservation, pk=reservation_id)
    
    if request.method == 'POST':
        student_name = reservation.student.name
        lesson_title = reservation.lesson_slot.title or '書道教室'
        reservation.delete()
        messages.success(request, f'{student_name}の"{lesson_title}"への予約をキャンセルしました。')
        return redirect('admin_reservation_list')
    
    context = {
        'reservation': reservation
    }
    return render(request, 'booking/admin/cancel_reservation.html', context)
