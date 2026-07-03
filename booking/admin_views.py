from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import JsonResponse
from django.contrib import messages
from django.db.models import Q, Count, Prefetch
from datetime import timedelta, datetime
from .forms import LessonSlotCreateForm, LessonSlotEditForm, StudentForm, FamilyEditForm
from .models import LessonSlot, Reservation, Waitlist, Family, Student
from django.utils import timezone
from django.contrib.auth import get_user_model  # noqa: F401

def is_staff(user):
    """管理者権限チェック"""
    return user.is_staff


def _allowed_classrooms(user):
    """スタッフのアクセス可能な教室リストを返す（superuserは全教室）"""
    if user.is_superuser:
        return ['ishihara', 'yokogawa']
    classroom = getattr(user, 'classroom', 'all')
    if not classroom or classroom == 'all':
        return ['ishihara', 'yokogawa']
    return [classroom]

# 管理者トップページ
@login_required
@user_passes_test(is_staff)
def admin_dashboard(request):
    """管理者ダッシュボード"""
    allowed = _allowed_classrooms(request.user)
    lesson_qs = LessonSlot.objects.filter(classroom__in=allowed)

    total_lessons = lesson_qs.count()
    upcoming_lessons = lesson_qs.filter(start_time__gte=timezone.now()).count()
    total_reservations = Reservation.objects.filter(lesson_slot__classroom__in=allowed).count()
    total_students = Student.objects.count()
    total_families = Family.objects.count()

    next_lesson = (
        lesson_qs
        .filter(start_time__gte=timezone.now())
        .order_by('start_time')
        .first()
    )

    next_day_lessons = []
    if next_lesson:
        next_date = next_lesson.start_time.date()
        next_day_lessons = (
            lesson_qs
            .filter(start_time__date=next_date)
            .order_by('start_time')
            .prefetch_related('reservation_set__student__family__user')
        )

    context = {
        'next_lesson': next_lesson,
        'next_day_lessons': next_day_lessons,
        'stats': [
            ('総授業枠', total_lessons),
            ('今後の授業', upcoming_lessons),
            ('総予約数', total_reservations),
            ('生徒数', total_students),
            ('保護者数', total_families),
        ],
        'menu_items': [
            ('bi bi-calendar-plus', '/admin-dashboard/create-lesson/', '授業枠を一括作成', '期間と曜日を指定して一括作成'),
            ('bi bi-plus-circle', '/admin-dashboard/create-lesson-single/', '授業枠を個別作成', '1つの授業枠を個別に作成'),
            ('bi bi-list-ul', '/admin-dashboard/lessons/', '授業枠一覧・編集', '授業枠を確認・編集・削除'),
            ('bi bi-ticket-perforated', '/admin-dashboard/reservations/', '予約一覧', '全体の予約状況を確認'),
            ('bi bi-people', '/admin-dashboard/students/', '生徒管理', '保護者と生徒の情報を管理'),
            ('bi bi-calendar-range', '/admin-dashboard/calendar/', '予約カレンダー', 'カレンダー形式で予約を確認・作成'),
            ('bi bi-database', '/admin/', 'DB管理画面', '全データの閲覧・編集（Django管理）'),
        ],
    }
    return render(request, 'booking/admin/dashboard.html', context)

# 授業枠一括作成機能
@login_required
@user_passes_test(is_staff)
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
            classroom = data["classroom"]

            # 授業名が空の場合のデフォルト設定
            if not title:
                title = "書道教室"

            current_date = start_date
            created_count = 0
            
            # 時間スロットをパース（@1,2 形式の週指定に対応）
            import re
            time_pairs = []
            for line in time_slots.strip().split('\n'):
                line = line.strip()
                if not line or '-' not in line:
                    continue
                try:
                    week_spec = None
                    week_match = re.search(r'@([\d,]+)', line)
                    if week_match:
                        week_spec = [int(w) for w in week_match.group(1).split(',')]
                        line = line[:week_match.start()].strip()
                    start_str, end_str = line.split('-')
                    start_time = datetime.strptime(start_str.strip(), '%H:%M').time()
                    end_time = datetime.strptime(end_str.strip(), '%H:%M').time()
                    time_pairs.append((start_time, end_time, week_spec))
                except ValueError:
                    continue

            # 期間内の日付を反復処理
            while current_date <= end_date:
                if current_date.weekday() in days_of_week:
                    week_of_month = (current_date.day - 1) // 7 + 1
                    for start_time, end_time, week_spec in time_pairs:
                        if week_spec and week_of_month not in week_spec:
                            continue
                        lesson_start_dt = datetime.combine(current_date, start_time, tzinfo=timezone.get_current_timezone())
                        lesson_end_dt = datetime.combine(current_date, end_time, tzinfo=timezone.get_current_timezone())
                        LessonSlot.objects.create(
                            title=title,
                            classroom=classroom,
                            start_time=lesson_start_dt,
                            end_time=lesson_end_dt,
                            capacity=capacity,
                            reservation_start_time=reservation_start_datetime,
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
@user_passes_test(is_staff)
def lesson_list(request):
    """授業枠一覧"""
    allowed = _allowed_classrooms(request.user)
    lessons = LessonSlot.objects.filter(classroom__in=allowed).order_by('-start_time')

    context = {
        'lessons': lessons
    }
    return render(request, 'booking/admin/lesson_list.html', context)

# 授業枠個別編集
@login_required
@user_passes_test(is_staff)
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
@user_passes_test(is_staff)
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
@user_passes_test(is_staff)
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
@user_passes_test(is_staff)
def reservation_list(request):
    """予約一覧"""
    allowed = _allowed_classrooms(request.user)
    reservations = Reservation.objects.filter(
        lesson_slot__classroom__in=allowed
    ).order_by('-reserved_at')

    context = {
        'reservations': reservations
    }
    return render(request, 'booking/admin/reservation_list.html', context)

# 生徒管理一覧
@login_required
@user_passes_test(is_staff)
def student_management(request):
    """生徒管理一覧"""
    query = request.GET.get('q', '').strip()
    now = timezone.localtime(timezone.now())
    students_qs = Student.objects.annotate(
        month_reservation_count=Count(
            'reservation',
            filter=Q(
                reservation__lesson_slot__start_time__year=now.year,
                reservation__lesson_slot__start_time__month=now.month,
            ),
        )
    )
    families = Family.objects.all().select_related('user').prefetch_related(
        Prefetch('student_set', queryset=students_qs)
    )
    if query:
        families = families.filter(
            Q(user__name__icontains=query) |
            Q(phone_number__icontains=query) |
            Q(student__name__icontains=query)
        ).distinct()

    context = {
        'families': families,
        'query': query,
    }
    return render(request, 'booking/admin/student_management.html', context)

# 生徒追加
@login_required
@user_passes_test(is_staff)
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
@user_passes_test(is_staff)
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
@user_passes_test(is_staff)
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


# 保護者削除
@login_required
@user_passes_test(is_staff)
def delete_family_admin(request, family_id):
    """管理者による保護者削除（関連する生徒・予約もすべて削除）"""
    family = get_object_or_404(Family, pk=family_id)
    if request.method == 'POST':
        name = family.user.name
        family.user.delete()  # CASCADE で Family・Student・Reservation も削除
        messages.success(request, f"保護者「{name}」とその生徒・予約をすべて削除しました。")
        return redirect('admin_student_management')
    return render(request, 'booking/admin/delete_family.html', {'family': family})


# 保護者情報編集
@login_required
@user_passes_test(is_staff)
def edit_family_admin(request, family_id):
    """管理者による保護者情報編集"""
    family = get_object_or_404(Family, pk=family_id)
    if request.method == 'POST':
        form = FamilyEditForm(request.POST)
        if form.is_valid():
            family.user.name = form.cleaned_data['name']
            family.user.save()
            family.phone_number = form.cleaned_data['phone_number']
            family.access_yokogawa = form.cleaned_data['access_yokogawa']
            family.access_ishihara = form.cleaned_data['access_ishihara']
            family.save()
            messages.success(request, f"保護者「{family.user.name}」の情報を更新しました。")
            return redirect('admin_student_management')
    else:
        form = FamilyEditForm(initial={
            'name': family.user.name,
            'phone_number': family.phone_number,
            'access_yokogawa': family.access_yokogawa,
            'access_ishihara': family.access_ishihara,
        })
    return render(request, 'booking/admin/edit_family.html', {'form': form, 'family': family})


# 予約キャンセル(管理者用)
@login_required
@user_passes_test(is_staff)
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


# 管理者用予約カレンダー
@login_required
@user_passes_test(is_staff)
def admin_reservation_calendar(request):
    """管理者用予約カレンダー"""
    from collections import defaultdict
    
    # 全授業枠を取得（過去分も含む・担当教室でフィルタリング）
    allowed = _allowed_classrooms(request.user)
    lessons = LessonSlot.objects.filter(
        classroom__in=allowed,
    ).order_by('start_time')
    
    # 日付ごとにグループ化
    lessons_by_date = defaultdict(list)
    for lesson in lessons:
        date_key = lesson.start_time.date()
        lessons_by_date[date_key].append(lesson)
    
    # 日付順にソート
    sorted_lessons_by_date = sorted(lessons_by_date.items())
    
    # 全生徒を取得
    all_students = Student.objects.all().select_related('family__user').order_by('family__user__name', 'name')
    
    context = {
        'lessons_by_date': sorted_lessons_by_date,
        'all_students': all_students,
    }
    return render(request, 'booking/admin/calendar.html', context)

# 管理者による予約作成
@login_required
@user_passes_test(is_staff)
def admin_reserve_lesson(request, lesson_id):
    """管理者による全生徒の予約作成"""
    lesson = get_object_or_404(LessonSlot, pk=lesson_id)
    
    wants_json = request.headers.get('x-requested-with') == 'XMLHttpRequest'
    if request.method == 'POST':
        student_id = request.POST.get('student_id')
        student = get_object_or_404(Student, pk=student_id)
        
        # 予約処理（管理者は予約開始時刻の制限を受けない）
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
                        'student_name': student.name,
                        'family_name': student.family.user.name,
                    })
                messages.success(request, message)
            except Exception:
                message = '予約に失敗しました。すでに予約済みの可能性があります。'
                if wants_json:
                    return JsonResponse({'success': False, 'message': message}, status=400)
                messages.error(request, message)
        else:
            message = '満席のため予約できません。'
            if wants_json:
                return JsonResponse({'success': False, 'message': message, 'available_slots': lesson.available_slots()}, status=400)
            messages.error(request, message)

    return redirect('admin_reservation_calendar')
