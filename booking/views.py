from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.views.generic.edit import CreateView
from django.contrib import messages
from django.core import signing
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
from collections import defaultdict
from .models import Family, Student, LessonSlot, Reservation, Waitlist
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
        messages.success(request, 'メールアドレスの認証が完了しました。ログインしてください。')
        return redirect('login')
    except signing.SignatureExpired:
        messages.error(request, '認証リンクの有効期限が切れています。再度登録してください。')
        return redirect('signup')
    except (signing.BadSignature, User.DoesNotExist):
        messages.error(request, '無効な認証リンクです。')
        return redirect('signup')


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
    lessons = LessonSlot.objects.filter(start_time__gte=timezone.now()).order_by('start_time')
    lessons_by_date = defaultdict(list)
    for lesson in lessons:
        lessons_by_date[lesson.start_time.date()].append(lesson)
    return render(request, 'booking/calendar.html', {
        'family': family,
        'students': students,
        'lessons_by_date': sorted(lessons_by_date.items()),
    })


@login_required
def reserve_lesson(request, lesson_id):
    if request.user.is_staff:
        return redirect('admin_dashboard')
    lesson = get_object_or_404(LessonSlot, pk=lesson_id)
    family = get_object_or_404(Family, user=request.user)
    if request.method == 'POST':
        student = get_object_or_404(Student, pk=request.POST.get('student_id'), family=family)
        if timezone.now() < lesson.reservation_start_time:
            messages.error(request, '予約開始時刻前です。')
            return redirect('reservation_calendar')
        if lesson.available_slots() > 0:
            try:
                Reservation.objects.create(lesson_slot=lesson, student=student)
                messages.success(request, f'{student.name}の予約が完了しました。')
            except Exception:
                messages.error(request, '予約に失敗しました。すでに予約済みの可能性があります。')
        else:
            try:
                Waitlist.objects.create(lesson_slot=lesson, student=student)
                messages.info(request, f'{student.name}を補欠登録しました。')
            except Exception:
                messages.error(request, '補欠登録に失敗しました。すでに登録済みの可能性があります。')
    return redirect('reservation_calendar')


@login_required
def cancel_reservation(request, reservation_id):
    if request.user.is_staff:
        return redirect('admin_dashboard')
    family = get_object_or_404(Family, user=request.user)
    reservation = get_object_or_404(Reservation, pk=reservation_id, student__family=family)
    from datetime import timedelta
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
