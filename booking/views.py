from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import login, logout
from django.urls import reverse_lazy
from django.views.generic.edit import CreateView
from django.contrib import messages
from datetime import timedelta, datetime
from collections import defaultdict
from .models import Family, Student, LessonSlot, Reservation, Waitlist
from .forms import StudentForm
from django.utils import timezone

# ユーザー登録(保護者アカウント作成)
class SignUpView(CreateView):
    form_class = UserCreationForm
    success_url = reverse_lazy('reservation_calendar')
    template_name = 'registration/signup.html'

    def form_valid(self, form):
        # ユーザーを保存
        user = form.save()
        # ユーザーに紐づくFamilyモデルを自動作成
        Family.objects.create(user=user)
        # ログインさせる
        login(self.request, user)
        return redirect(self.success_url)

# 生徒閲覧・管理(保護者用)
@login_required
def view_students(request):
    """保護者による生徒閲覧・管理"""
    family = get_object_or_404(Family, user=request.user)
    students = Student.objects.filter(family=family)
    
    context = {
        'students': students,
        'family': family
    }
    return render(request, 'booking/view_students.html', context)

# 生徒追加(保護者用)
@login_required
def add_student(request):
    """保護者による生徒追加"""
    family = get_object_or_404(Family, user=request.user)
    
    if request.method == 'POST':
        form = StudentForm(request.POST)
        if form.is_valid():
            student = form.save(commit=False)
            student.family = family
            student.save()
            messages.success(request, f"生徒「{student.name}」を追加しました。")
            return redirect('view_students')
    else:
        form = StudentForm()
    
    context = {
        'form': form,
        'family': family
    }
    return render(request, 'booking/add_student.html', context)

# 生徒編集(保護者用)
@login_required
def edit_student(request, student_id):
    """保護者による生徒編集"""
    family = get_object_or_404(Family, user=request.user)
    student = get_object_or_404(Student, pk=student_id, family=family)
    
    if request.method == 'POST':
        form = StudentForm(request.POST, instance=student)
        if form.is_valid():
            form.save()
            messages.success(request, f"生徒「{student.name}」を更新しました。")
            return redirect('view_students')
    else:
        form = StudentForm(instance=student)
    
    context = {
        'form': form,
        'student': student,
        'family': family
    }
    return render(request, 'booking/edit_student.html', context)

# 生徒削除(保護者用)
@login_required
def delete_student(request, student_id):
    """保護者による生徒削除"""
    family = get_object_or_404(Family, user=request.user)
    student = get_object_or_404(Student, pk=student_id, family=family)
    
    if request.method == 'POST':
        student_name = student.name
        student.delete()
        messages.success(request, f"生徒「{student_name}」を削除しました。")
        return redirect('view_students')
    
    context = {
        'student': student,
        'family': family
    }
    return render(request, 'booking/delete_student.html', context)

# 予約カレンダー画面(日別表示)
@login_required
def reservation_calendar(request):
    family = get_object_or_404(Family, user=request.user)
    students = Student.objects.filter(family=family)
    
    # 今後の授業枠を取得
    lessons = LessonSlot.objects.filter(start_time__gte=timezone.now()).order_by('start_time')
    
    # 日付ごとにグループ化
    lessons_by_date = defaultdict(list)
    for lesson in lessons:
        date_key = lesson.start_time.date()
        lessons_by_date[date_key].append(lesson)
    
    # 日付順にソート
    sorted_lessons_by_date = sorted(lessons_by_date.items())
    
    context = {
        'family': family,
        'students': students,
        'lessons_by_date': sorted_lessons_by_date,
    }
    return render(request, 'booking/calendar.html', context)

# 予約処理
@login_required
def reserve_lesson(request, lesson_id):
    lesson = get_object_or_404(LessonSlot, pk=lesson_id)
    family = get_object_or_404(Family, user=request.user)
    
    if request.method == 'POST':
        student_id = request.POST.get('student_id')
        student = get_object_or_404(Student, pk=student_id, family=family)
        
        # 予約開始時刻チェック
        if timezone.now() < lesson.reservation_start_time:
            messages.error(request, '予約開始時刻前です。')
            return redirect('reservation_calendar')

        # 予約処理
        if lesson.available_slots() > 0:
            try:
                Reservation.objects.create(lesson_slot=lesson, student=student)
                messages.success(request, f'{student.name}の予約が完了しました。')
            except Exception as e:
                messages.error(request, '予約に失敗しました。すでに予約済みの可能性があります。')
        
        # 補欠処理
        elif lesson.available_slots() <= 0:
            try:
                Waitlist.objects.create(lesson_slot=lesson, student=student)
                messages.info(request, f'{student.name}を補欠登録しました。')
            except Exception as e:
                messages.error(request, '補欠登録に失敗しました。すでに登録済みの可能性があります。')

    return redirect('reservation_calendar')

# 予約キャンセル(保護者用)
@login_required
def cancel_reservation(request, reservation_id):
    """保護者による予約キャンセル"""
    family = get_object_or_404(Family, user=request.user)
    reservation = get_object_or_404(Reservation, pk=reservation_id, student__family=family)
    
    if request.method == 'POST':
        student_name = reservation.student.name
        lesson_title = reservation.lesson_slot.title or '書道教室'
        reservation.delete()
        messages.success(request, f'{student_name}の"{lesson_title}"への予約をキャンセルしました。')
        return redirect('reservation_calendar')
    
    context = {
        'reservation': reservation,
        'family': family
    }
    return render(request, 'booking/cancel_reservation.html', context)
