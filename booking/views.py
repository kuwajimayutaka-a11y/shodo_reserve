from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.views.generic.edit import CreateView
from django.http import JsonResponse
from django.contrib import messages
from django.core import signing
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
from collections import defaultdict
from datetime import timedelta
from django.db import IntegrityError
from .models import Family, Student, LessonSlot, Reservation
from .forms import SignUpForm, StudentForm
from django.utils import timezone

User = get_user_model()


class SignUpView(CreateView):
    form_class = SignUpForm
    template_name = 'registration/signup.html'

    def form_valid(self, form):
        user = form.save(commit=False)
        user.is_active = False
        user.save()
        Family.objects.create(user=user)

        token = signing.dumps({'user_id': user.pk}, salt='email-verify')
        verify_url = self.request.build_absolute_uri(
            reverse('verify_email', args=[token])
        )
        subject = '秀雪書道教室 メールアドレスの確認'
        message = render_to_string('registration/verify_email.txt', {
            'user': user,
            'verify_url': verify_url,
            'from_email': settings.DEFAULT_FROM_EMAIL,
        })
        send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [user.email])
        return redirect('email_sent')


def email_sent(request):
    return render(request, 'registration/email_sent.html')


def verify_email(request, token):
    try:
        data = signing.loads(token, salt='email-verify', max_age=60 * 60 * 24 * 3)
        user = User.objects.get(pk=data['user_id'])
        user.is_active = True
        user.save()
        return render(request, 'registration/verify_success.html')
    except signing.SignatureExpired:
        return render(request, 'registration/verify_error.html', {
            'error_title': 'リンクの有効期限切れ',
            'error_message': '認証リンクの有効期限（3日間）が切れています。再度登録してください。',
        })
    except (signing.BadSignature, User.DoesNotExist):
        return render(request, 'registration/verify_error.html', {
            'error_title': '無効な認証リンク',
            'error_message': 'このリンクは無効です。正しいリンクをご確認ください。',
        })


@login_required
def view_students(request):
    if request.user.is_staff:
        return redirect('admin_dashboard')
    family = get_object_or_404(Family, user=request.user)
    students = Student.objects.filter(family=family)
    return render(request, 'booking/view_students.html', {
        'students': students, 'family': family,
    })


@login_required
def add_student(request):
    if request.user.is_staff:
        return redirect('admin_dashboard')
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
    return render(request, 'booking/add_student.html', {'form': form, 'family': family})


@login_required
def edit_student(request, student_id):
    if request.user.is_staff:
        return redirect('admin_dashboard')
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
    return render(request, 'booking/edit_student.html', {
        'form': form, 'student': student, 'family': family,
    })


@login_required
def delete_student(request, student_id):
    from django.http import HttpResponseForbidden
    if request.user.is_staff:
        return redirect('admin_dashboard')
    return HttpResponseForbidden("生徒の削除は管理者のみ可能です。")


@login_required
def reservation_calendar(request):
    if request.user.is_staff:
        return redirect('admin_dashboard')
    family = get_object_or_404(Family, user=request.user)
    students = Student.objects.filter(family=family)

    # 保護者の教室アクセス権に基づいてフィルタリング
    allowed_classrooms = []
    if family.access_yokogawa:
        allowed_classrooms.append('yokogawa')
    if family.access_ishihara:
        allowed_classrooms.append('ishihara')
    lessons = LessonSlot.objects.filter(
        start_time__gte=timezone.now(),
        classroom__in=allowed_classrooms,
    ).order_by('start_time')

    # 自分の生徒の予約: {lesson_id: set(student_id)}
    my_reserved = {}
    upcoming_reservations = defaultdict(list)
    for res in Reservation.objects.filter(student__in=students).select_related('student', 'lesson_slot').order_by('lesson_slot__start_time'):
        my_reserved.setdefault(res.lesson_slot_id, set()).add(res.student_id)
        if res.lesson_slot.end_time >= timezone.now():
            upcoming_reservations[res.student_id].append(res)

    lessons_by_date = defaultdict(list)
    for lesson in lessons:
        lessons_by_date[lesson.start_time.date()].append(lesson)
    return render(request, 'booking/calendar.html', {
        'family': family,
        'students': students,
        'lessons_by_date': sorted(lessons_by_date.items()),
        'my_reserved': my_reserved,
        'upcoming_reservations': dict(upcoming_reservations),
    })


@login_required
def reserve_lesson(request, lesson_id):
    if request.user.is_staff:
        return redirect('admin_dashboard')
    lesson = get_object_or_404(LessonSlot, pk=lesson_id)
    family = get_object_or_404(Family, user=request.user)
    wants_json = request.headers.get('x-requested-with') == 'XMLHttpRequest'

    # 教室アクセス権チェック
    allowed_classrooms = []
    if family.access_yokogawa:
        allowed_classrooms.append('yokogawa')
    if family.access_ishihara:
        allowed_classrooms.append('ishihara')
    if lesson.classroom not in allowed_classrooms:
        message = 'この教室の授業は予約できません。'
        if wants_json:
            return JsonResponse({'success': False, 'message': message}, status=403)
        messages.error(request, message)
        return redirect('reservation_calendar')

    if request.method == 'POST':
        student = get_object_or_404(Student, pk=request.POST.get('student_id'), family=family)
        if timezone.now() < lesson.reservation_start_time:
            message = '予約開始時刻前です。'
            if wants_json:
                return JsonResponse({'success': False, 'message': message}, status=400)
            messages.error(request, message)
            return redirect('reservation_calendar')
        if lesson.available_slots() > 0:
            try:
                Reservation.objects.create(lesson_slot=lesson, student=student)
                message = f'{student.name}の予約が完了しました。'
                if wants_json:
                    return JsonResponse({
                        'success': True,
                        'message': message,
                        'lesson_id': lesson.id,
                        'available_slots': lesson.available_slots(),
                        'student_id': student.id,
                        'student_name': student.name,
                    })
                messages.success(request, message)
            except IntegrityError:
                message = '予約に失敗しました。すでに予約済みの可能性があります。'
                if wants_json:
                    return JsonResponse({'success': False, 'message': message}, status=400)
                messages.error(request, message)
        else:
            message = '満席のため予約できません。'
            if wants_json:
                return JsonResponse({'success': False, 'message': message}, status=400)
            messages.error(request, message)
    return redirect('reservation_calendar')


@login_required
def cancel_reservation(request, reservation_id):
    if request.user.is_staff:
        return redirect('admin_dashboard')
    family = get_object_or_404(Family, user=request.user)
    reservation = get_object_or_404(Reservation, pk=reservation_id, student__family=family)
    deadline = reservation.lesson_slot.start_time - timedelta(hours=1)
    can_cancel = timezone.now() < deadline
    if request.method == 'POST':
        if not can_cancel:
            messages.error(request, 'キャンセルできません。授業開始1時間前を過ぎています。')
            return redirect('reservation_calendar')
        student_name = reservation.student.name
        lesson_title = reservation.lesson_slot.title or '書道教室'
        reservation.delete()
        messages.success(request, f'{student_name}の"{lesson_title}"への予約をキャンセルしました。')
        return redirect('reservation_calendar')
    return render(request, 'booking/cancel_reservation.html', {
        'reservation': reservation, 'family': family,
        'can_cancel': can_cancel, 'cancel_deadline': deadline,
    })
