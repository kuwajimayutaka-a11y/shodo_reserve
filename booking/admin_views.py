from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import JsonResponse
from django.contrib import messages
from django.core.paginator import Paginator
from django.db import IntegrityError
from django.db.models import Q, Count, Prefetch
from django.db.models.functions import ExtractHour, ExtractMinute
from datetime import timedelta, datetime
from .forms import (
    LessonSlotCreateForm, LessonSlotEditForm, LessonSlotSingleCreateForm,
    LessonTimeSlotFormSet, StudentForm, StudentGroupForm, FamilyEditForm,
)
from .models import LessonSlot, Reservation, Waitlist, Family, Student, StudentGroup
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


def _student_list_url(request):
    """生徒管理一覧に戻るURL。絞り込み・ページ番号を保った状態で戻れるようにする。

    一覧の各リンクが付ける back（一覧のクエリ文字列）を引き継ぐ。POST で消えないよう
    フォーム側の hidden も見る。クエリ文字列以外が入っていたら安全側に捨てる。
    """
    back = (request.POST.get('back') or request.GET.get('back') or '').lstrip('?')
    if any(ch in back for ch in '/\\:\r\n '):
        back = ''
    url = reverse('admin_student_management')
    return f'{url}?{back}' if back else url


def _reserve_group_for_lesson(lesson, group):
    """指定グループの生徒をまとめて授業枠に予約する。

    定員を超える分は予約せずスキップする（管理者操作のため予約開始時刻は無視）。
    戻り値: (予約できた人数, 定員超過でスキップした人数)
    """
    reserved = 0
    skipped = 0
    for student in group.students.all():
        if lesson.available_slots() <= 0:
            skipped += 1
            continue
        try:
            Reservation.objects.create(lesson_slot=lesson, student=student)
            reserved += 1
        except IntegrityError:
            pass
    return reserved, skipped

# 管理者トップページ
@login_required
@user_passes_test(is_staff)
def admin_dashboard(request):
    """管理者ダッシュボード"""
    allowed = _allowed_classrooms(request.user)
    lesson_qs = LessonSlot.objects.filter(classroom__in=allowed)

    total_students = Student.objects.count()
    total_families = Family.objects.count()

    # 今月の増加数（保護者アカウントの登録日で集計。生徒は保護者の登録月で近似）
    now = timezone.localtime(timezone.now())
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    new_families = Family.objects.filter(user__date_joined__gte=month_start).count()
    new_students = Student.objects.filter(family__user__date_joined__gte=month_start).count()

    # 今週（月曜〜日曜）の席の埋まり具合（予約席数 / 総定員）
    week_start = (now - timedelta(days=now.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)
    week_end = week_start + timedelta(days=7)
    week_lessons = lesson_qs.filter(
        start_time__gte=week_start, start_time__lt=week_end
    ).annotate(res_count=Count('reservation'))
    week_capacity = 0
    week_booked = 0
    for lesson in week_lessons:
        week_capacity += lesson.capacity
        week_booked += lesson.res_count
    week_occupancy = {
        'booked': week_booked,
        'capacity': week_capacity,
        'percent': round(week_booked / week_capacity * 100) if week_capacity else 0,
    }

    # 今日の0時以降で最も早い授業枠を「直近の授業」とする。
    # これにより、開始時刻を過ぎた授業も当日中（翌0時まで）は表示され続ける。
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    next_lesson = (
        lesson_qs
        .filter(start_time__gte=today_start)
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
        'week_occupancy': week_occupancy,
        'stats': [
            {'label': '生徒数', 'value': total_students, 'delta': new_students},
            {'label': '保護者数', 'value': total_families, 'delta': new_families},
        ],
        'menu_items': [
            ('bi bi-calendar-plus', '/admin-dashboard/create-lesson/', '授業枠を一括作成', '期間と曜日を指定して一括作成'),
            ('bi bi-plus-circle', '/admin-dashboard/create-lesson-single/', '授業枠を個別作成', '1つの授業枠を個別に作成'),
            ('bi bi-list-ul', '/admin-dashboard/lessons/', '授業枠一覧・編集', '授業枠を確認・編集・削除'),
            ('bi bi-ticket-perforated', '/admin-dashboard/reservations/', '予約一覧', '全体の予約状況を確認'),
            ('bi bi-people', '/admin-dashboard/students/', '生徒管理', '保護者と生徒の情報を管理'),
            ('bi bi-collection', '/admin-dashboard/student-groups/', '生徒グループ管理', '授業作成時に自動予約するグループを管理'),
            ('bi bi-calendar-range', '/admin-dashboard/calendar/', '予約カレンダー', 'カレンダー形式で予約を確認・作成'),
            ('bi bi-database', '/admin/', 'DB管理画面', '全データの閲覧・編集（Django管理）'),
        ],
    }
    return render(request, 'booking/admin/dashboard.html', context)

# 授業枠一括作成機能
@login_required
@user_passes_test(is_staff)
def create_lesson_slots(request):
    """授業枠一括作成。曜日×コマ（時間帯）の直積で授業枠をまとめて作成する。

    コマごとに自動予約グループを紐づけられ、生成される全ての回にそのグループの
    生徒を自動予約する（定員超過分はスキップし、まとめて警告表示）。
    """
    if request.method == "POST":
        form = LessonSlotCreateForm(request.POST)
        formset = LessonTimeSlotFormSet(request.POST, prefix='timeslot')
        if form.is_valid() and formset.is_valid():
            data = form.cleaned_data

            start_date = data["start_date"]
            end_date = data["end_date"]
            days_of_week = [int(d) for d in data["days_of_week"]]
            capacity = data["capacity"]
            title = data["title"] or "書道教室"
            reservation_start_datetime = data["reservation_start_datetime"]
            classroom = data["classroom"]

            time_rows = [
                f.cleaned_data for f in formset.forms
                if f.cleaned_data and not f.cleaned_data.get('DELETE')
            ]

            current_date = start_date
            created_count = 0
            # グループごとの自動予約結果を集計してからまとめてメッセージ表示する
            group_stats = {}  # group_name -> {'reserved': int, 'skipped': int}

            while current_date <= end_date:
                if current_date.weekday() in days_of_week:
                    week_of_month = (current_date.day - 1) // 7 + 1
                    for row in time_rows:
                        weeks_of_month = row["weeks_of_month_list"]
                        if weeks_of_month and week_of_month not in weeks_of_month:
                            continue
                        lesson_start_dt = datetime.combine(current_date, row["start_time"], tzinfo=timezone.get_current_timezone())
                        lesson_end_dt = datetime.combine(current_date, row["end_time"], tzinfo=timezone.get_current_timezone())
                        lesson = LessonSlot.objects.create(
                            title=title,
                            classroom=classroom,
                            start_time=lesson_start_dt,
                            end_time=lesson_end_dt,
                            capacity=capacity,
                            reservation_start_time=reservation_start_datetime,
                        )
                        created_count += 1

                        group = row.get("student_group")
                        if group:
                            reserved, skipped = _reserve_group_for_lesson(lesson, group)
                            stats = group_stats.setdefault(group.name, {'reserved': 0, 'skipped': 0})
                            stats['reserved'] += reserved
                            stats['skipped'] += skipped

                current_date += timedelta(days=1)

            messages.success(request, f"授業枠を {created_count} 件作成しました。")
            for group_name, stats in group_stats.items():
                msg = f"「{group_name}」から合計{stats['reserved']}件の予約を自動作成しました。"
                if stats['skipped']:
                    messages.warning(request, msg + f" 定員超過のため{stats['skipped']}件は予約できませんでした。")
                else:
                    messages.success(request, msg)
            return redirect("admin_lesson_list")
    else:
        form = LessonSlotCreateForm()
        formset = LessonTimeSlotFormSet(prefix='timeslot', initial=[{}])

    context = {
        "form": form,
        "formset": formset,
    }
    return render(request, "booking/admin/create_lesson.html", context)

# 授業枠一覧表示
@login_required
@user_passes_test(is_staff)
def lesson_list(request):
    """授業枠一覧。既定は今日以降のみ表示（過去は scope=past で切替）。

    間違って作成した枠をチェックボックスで選び、一括削除できる。
    予約数は annotate で取得し行ごとの N+1 を避ける。
    """
    allowed = _allowed_classrooms(request.user)
    scope = request.GET.get('scope', 'upcoming')

    lessons = LessonSlot.objects.filter(classroom__in=allowed).annotate(
        reserved_count=Count('reservation'),
    )

    today = timezone.localtime(timezone.now()).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    if scope == 'past':
        lessons = lessons.filter(start_time__lt=today).order_by('-start_time')
    else:
        scope = 'upcoming'
        lessons = lessons.filter(start_time__gte=today).order_by('start_time')

    context = {
        'lessons': lessons,
        'scope': scope,
    }
    return render(request, 'booking/admin/lesson_list.html', context)


# 授業枠一括削除
@login_required
@user_passes_test(is_staff)
def bulk_delete_lesson_slots(request):
    """選択された授業枠をまとめて削除する（予約も CASCADE で削除）。

    権限のある教室の枠のみを対象にする。scope はメッセージ後の
    リダイレクト先タブを保つために引き継ぐ。
    """
    scope = request.POST.get('scope') or request.GET.get('scope') or 'upcoming'
    redirect_url = f"{reverse('admin_lesson_list')}?scope={scope}"

    if request.method != 'POST':
        return redirect(redirect_url)

    allowed = _allowed_classrooms(request.user)
    ids = request.POST.getlist('lesson_ids')
    lessons = LessonSlot.objects.filter(pk__in=ids, classroom__in=allowed)

    lesson_count = lessons.count()
    if lesson_count == 0:
        messages.error(request, "削除する授業枠が選択されていません。")
        return redirect(redirect_url)

    reservation_count = Reservation.objects.filter(lesson_slot__in=lessons).count()
    lessons.delete()  # 予約は CASCADE で削除

    if reservation_count:
        messages.success(
            request,
            f"授業枠 {lesson_count} 件を削除しました（予約 {reservation_count} 件も削除されました）。",
        )
    else:
        messages.success(request, f"授業枠 {lesson_count} 件を削除しました。")
    return redirect(redirect_url)

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
    """授業枠個別作成。自動予約グループを選ぶと、作成した授業枠にその生徒を自動予約する。"""
    if request.method == "POST":
        form = LessonSlotSingleCreateForm(request.POST)
        if form.is_valid():
            lesson = form.save()
            message = "授業枠を作成しました。"
            group = form.cleaned_data.get("student_group")
            skipped = 0
            if group:
                reserved, skipped = _reserve_group_for_lesson(lesson, group)
                message += f" 「{group.name}」から{reserved}件の予約を自動作成しました。"
            messages.success(request, message)
            if skipped:
                messages.warning(request, f"定員超過のため{skipped}件は予約できませんでした。")
            return redirect("admin_lesson_list")
    else:
        form = LessonSlotSingleCreateForm()

    context = {
        "form": form
    }
    return render(request, "booking/admin/create_lesson_single.html", context)

# 予約一覧表示
@login_required
@user_passes_test(is_staff)
def reservation_list(request):
    """予約一覧。授業枠ごとにまとめ、授業日順に表示する。

    既定では「今日以降の授業」のみ表示（過去の予約は溜まる一方なので
    scope=past で切り替える）。生徒名/保護者名・日付・時間で絞り込め、
    絞り込み中は scope をまたいで（過去も含めて）検索する。
    予約は授業日時の昇順・同一授業内は生徒名順。
    """
    allowed = _allowed_classrooms(request.user)
    scope = request.GET.get('scope', 'upcoming')
    q = request.GET.get('q', '').strip()
    date_str = request.GET.get('date', '').strip()
    time_str = request.GET.get('time', '').strip()

    base_qs = Reservation.objects.filter(
        lesson_slot__classroom__in=allowed
    ).select_related('lesson_slot', 'student__family__user')

    # プルダウンの選択肢は「予約が入っている日／時間」だけを提示する
    # （空振りする日時を選べないようにする）。ローカルタイムゾーンで抽出。
    date_options = list(base_qs.dates('lesson_slot__start_time', 'day', order='ASC'))
    time_options = [
        '%02d:%02d' % (h, m)
        for h, m in base_qs.annotate(
            _h=ExtractHour('lesson_slot__start_time'),
            _m=ExtractMinute('lesson_slot__start_time'),
        ).values_list('_h', '_m').distinct().order_by('_h', '_m')
    ]

    reservations = base_qs

    # 名前で絞り込み（生徒名 or 保護者名）
    if q:
        reservations = reservations.filter(
            Q(student__name__icontains=q) |
            Q(student__family__user__name__icontains=q)
        )

    # 日付で絞り込み（授業の開催日）
    date_val = None
    if date_str:
        try:
            date_val = datetime.strptime(date_str, '%Y-%m-%d').date()
            reservations = reservations.filter(lesson_slot__start_time__date=date_val)
        except ValueError:
            date_str = ''

    # 時間で絞り込み（授業の開始時刻 HH:MM）
    time_val = None
    if time_str:
        try:
            time_val = datetime.strptime(time_str, '%H:%M').time()
            reservations = reservations.filter(
                lesson_slot__start_time__hour=time_val.hour,
                lesson_slot__start_time__minute=time_val.minute,
            )
        except ValueError:
            time_str = ''

    filters_active = bool(q or date_val or time_val)

    if filters_active:
        # 絞り込み時は scope を無視し、全期間から昇順で表示
        reservations = reservations.order_by('lesson_slot__start_time', 'student__name')
    else:
        today = timezone.localtime(timezone.now()).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        if scope == 'past':
            reservations = reservations.filter(lesson_slot__start_time__lt=today)
            # 過去は新しい授業が上に来るよう降順
            reservations = reservations.order_by('-lesson_slot__start_time', 'student__name')
        else:
            scope = 'upcoming'
            reservations = reservations.filter(lesson_slot__start_time__gte=today)
            reservations = reservations.order_by('lesson_slot__start_time', 'student__name')

    # 授業枠ごとにグルーピング（クエリ順を保つため通常の dict を使う）
    groups = {}
    for reservation in reservations:
        groups.setdefault(reservation.lesson_slot_id, {
            'lesson': reservation.lesson_slot,
            'reservations': [],
        })['reservations'].append(reservation)

    context = {
        'lesson_groups': list(groups.values()),
        'scope': scope,
        'q': q,
        'date': date_str,
        'time': time_str,
        'date_options': date_options,
        'time_options': time_options,
        'filters_active': filters_active,
        'total_count': len(reservations),
    }
    return render(request, 'booking/admin/reservation_list.html', context)

# 生徒管理一覧
STUDENTS_PER_PAGE = 50


@login_required
@user_passes_test(is_staff)
def student_management(request):
    """生徒管理一覧。

    生徒1人=1行のテーブルで表示する。生徒数が増えても探せるよう、
    名前順に並べ、教室での絞り込み・名前/電話での検索・ページ分割に対応する。
    生徒が未登録の保護者は生徒の表に出てこないため、表の下にまとめて表示する。
    """
    query = request.GET.get('q', '').strip()
    now = timezone.localtime(timezone.now())

    # 教室絞り込み。担当教室が1つに限定されているスタッフは、その教室に固定する。
    allowed = _allowed_classrooms(request.user)
    room_locked = len(allowed) == 1
    room = allowed[0] if room_locked else request.GET.get('room', '').strip()
    if room not in ('yokogawa', 'ishihara'):
        room = 'all'

    families = Family.objects.all()
    if room == 'yokogawa':
        families = families.filter(access_yokogawa=True)
    elif room == 'ishihara':
        families = families.filter(access_ishihara=True)

    students = Student.objects.filter(family__in=families).select_related(
        'family', 'family__user'
    ).annotate(
        month_reservation_count=Count(
            'reservation',
            filter=Q(
                reservation__lesson_slot__start_time__year=now.year,
                reservation__lesson_slot__start_time__month=now.month,
            ),
        )
    # 生徒名を第1キーにすると同姓（兄弟姉妹）が隣り合う。id はページ分割を安定させるため
    ).order_by('name', 'family__user__name', 'id')

    if query:
        students = students.filter(
            Q(name__icontains=query)
            | Q(family__user__name__icontains=query)
            | Q(family__phone_number__icontains=query)
        )

    total_count = students.count()
    paginator = Paginator(students, STUDENTS_PER_PAGE)
    page_obj = paginator.get_page(request.GET.get('page'))

    # 生徒が未登録の保護者（本番で8件程度）。生徒の表からは漏れるので別枠で出す。
    empty_families = families.filter(student__isnull=True).select_related('user')
    if query:
        empty_families = empty_families.filter(
            Q(user__name__icontains=query) | Q(phone_number__icontains=query)
        )
    empty_families = empty_families.order_by('user__name')

    # ページ送りのリンクで q / room を保つためのクエリ文字列
    params = request.GET.copy()
    params.pop('page', None)
    base_query = params.urlencode()
    # 編集・削除から戻ってきたときに同じ絞り込み・同じページを再現するための現在地
    current_query = request.GET.urlencode()

    context = {
        'page_obj': page_obj,
        'students': page_obj.object_list,
        'total_count': total_count,
        'empty_families': empty_families,
        'query': query,
        'room': room,
        'room_locked': room_locked,
        'base_query': base_query,
        'current_query': current_query,
        'per_page': STUDENTS_PER_PAGE,
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
            return redirect(_student_list_url(request))
    else:
        form = StudentForm()

    context = {
        'form': form,
        'family': family,
        'back': request.GET.get('back', ''),
        'back_url': _student_list_url(request),
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
            return redirect(_student_list_url(request))
    else:
        form = StudentForm(instance=student)

    context = {
        'form': form,
        'student': student,
        'back': request.GET.get('back', ''),
        'back_url': _student_list_url(request),
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
        return redirect(_student_list_url(request))

    context = {
        'student': student,
        'back': request.GET.get('back', ''),
        'back_url': _student_list_url(request),
    }
    return render(request, 'booking/admin/delete_student.html', context)


# 生徒グループ一覧
@login_required
@user_passes_test(is_staff)
def student_group_list(request):
    """生徒グループ一覧。授業作成時に自動予約するグループを管理する。"""
    groups = StudentGroup.objects.prefetch_related('students__family__user').annotate(
        student_count=Count('students', distinct=True)
    )
    context = {'groups': groups}
    return render(request, 'booking/admin/student_group_list.html', context)


# 生徒グループ追加
@login_required
@user_passes_test(is_staff)
def add_student_group(request):
    """生徒グループ追加"""
    if request.method == 'POST':
        form = StudentGroupForm(request.POST)
        if form.is_valid():
            group = form.save()
            messages.success(request, f"グループ「{group.name}」を作成しました。")
            return redirect('admin_student_group_list')
    else:
        form = StudentGroupForm()

    context = {'form': form}
    return render(request, 'booking/admin/student_group_form.html', context)


# 生徒グループ編集
@login_required
@user_passes_test(is_staff)
def edit_student_group(request, group_id):
    """生徒グループ編集"""
    group = get_object_or_404(StudentGroup, pk=group_id)

    if request.method == 'POST':
        form = StudentGroupForm(request.POST, instance=group)
        if form.is_valid():
            form.save()
            messages.success(request, f"グループ「{group.name}」を更新しました。")
            return redirect('admin_student_group_list')
    else:
        form = StudentGroupForm(instance=group)

    context = {'form': form, 'group': group}
    return render(request, 'booking/admin/student_group_form.html', context)


# 生徒グループ削除
@login_required
@user_passes_test(is_staff)
def delete_student_group(request, group_id):
    """生徒グループ削除"""
    group = get_object_or_404(StudentGroup, pk=group_id)

    if request.method == 'POST':
        group_name = group.name
        group.delete()
        messages.success(request, f"グループ「{group_name}」を削除しました。")
        return redirect('admin_student_group_list')

    context = {'group': group}
    return render(request, 'booking/admin/delete_student_group.html', context)


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
        return redirect(_student_list_url(request))
    return render(request, 'booking/admin/delete_family.html', {
        'family': family,
        'back': request.GET.get('back', ''),
        'back_url': _student_list_url(request),
    })


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
            return redirect(_student_list_url(request))
    else:
        form = FamilyEditForm(initial={
            'name': family.user.name,
            'phone_number': family.phone_number,
            'access_yokogawa': family.access_yokogawa,
            'access_ishihara': family.access_ishihara,
        })
    return render(request, 'booking/admin/edit_family.html', {
        'form': form,
        'family': family,
        'back': request.GET.get('back', ''),
        'back_url': _student_list_url(request),
    })


# 予約キャンセル(管理者用)
@login_required
@user_passes_test(is_staff)
def cancel_reservation_admin(request, reservation_id):
    """管理者による予約キャンセル。

    予約一覧からは XHR で呼ばれ JSON を返す（インライン削除）。
    それ以外は従来どおり確認ページ経由でリダイレクトする。
    """
    reservation = get_object_or_404(Reservation, pk=reservation_id)
    wants_json = request.headers.get('x-requested-with') == 'XMLHttpRequest'

    if request.method == 'POST':
        student_name = reservation.student.name
        lesson_title = reservation.lesson_slot.title or '書道教室'
        lesson_id = reservation.lesson_slot_id
        reservation.delete()
        message = f'{student_name}の"{lesson_title}"への予約をキャンセルしました。'
        if wants_json:
            return JsonResponse({
                'success': True,
                'message': message,
                'reservation_id': reservation_id,
                'lesson_id': lesson_id,
            })
        messages.success(request, message)
        return redirect('admin_reservation_list')

    context = {
        'reservation': reservation
    }
    return render(request, 'booking/admin/cancel_reservation.html', context)


def _calendar_lessons_by_date(allowed, start=None, end=None):
    """カレンダー用に授業枠を [start, end) で取得し、日付ごとにまとめて返す。
    予約の N+1 を避けるため予約・生徒・保護者をまとめて取得し、
    残り枠数はアノテーション(_reserved_count)で算出する。"""
    from collections import defaultdict

    lessons = LessonSlot.objects.filter(classroom__in=allowed)
    if start is not None:
        lessons = lessons.filter(start_time__gte=start)
    if end is not None:
        lessons = lessons.filter(start_time__lt=end)
    lessons = lessons.prefetch_related(
        Prefetch(
            'reservation_set',
            queryset=Reservation.objects.select_related('student__family__user'),
        ),
    ).annotate(
        _reserved_count=Count('reservation'),
    ).order_by('start_time')

    lessons_by_date = defaultdict(list)
    for lesson in lessons:
        lessons_by_date[lesson.start_time.date()].append(lesson)
    return sorted(lessons_by_date.items())


# 管理者用予約カレンダー
@login_required
@user_passes_test(is_staff)
def admin_reservation_calendar(request):
    """管理者用予約カレンダー。

    初回描画は前月頭〜未来のみ（軽量化のため）。それより過去は
    ミニカレンダーの月移動時に admin_calendar_month で月単位に取得する。
    """
    allowed = _allowed_classrooms(request.user)

    # 表示開始を「前月の1日」に揃える。オンデマンド取得の境界を月単位に
    # 合わせることで、境界月の取りこぼしを防ぐ。
    now = timezone.now()
    first_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    since = (first_of_month - timedelta(days=1)).replace(day=1)

    sorted_lessons_by_date = _calendar_lessons_by_date(allowed, start=since)

    # 全生徒を取得
    all_students = Student.objects.all().select_related('family__user').order_by('family__user__name', 'name')

    context = {
        'lessons_by_date': sorted_lessons_by_date,
        'all_students': all_students,
        'since': since,
    }
    return render(request, 'booking/admin/calendar.html', context)


@login_required
@user_passes_test(is_staff)
def admin_calendar_month(request):
    """指定した年月の授業枠を、カレンダー日付ブロックのHTMLとして返す（過去月のオンデマンド読み込み用）。"""
    from django.template.loader import render_to_string

    allowed = _allowed_classrooms(request.user)
    try:
        year = int(request.GET.get('year'))
        month = int(request.GET.get('month'))
    except (TypeError, ValueError):
        return JsonResponse({'error': 'invalid parameters'}, status=400)
    if not (1 <= month <= 12):
        return JsonResponse({'error': 'invalid month'}, status=400)

    start = timezone.make_aware(datetime(year, month, 1))
    if month == 12:
        end = timezone.make_aware(datetime(year + 1, 1, 1))
    else:
        end = timezone.make_aware(datetime(year, month + 1, 1))

    sorted_lessons_by_date = _calendar_lessons_by_date(allowed, start=start, end=end)

    rooms = {
        date.strftime('%Y-%m-%d'): [lesson.classroom for lesson in lessons]
        for date, lessons in sorted_lessons_by_date
    }
    all_students = Student.objects.all().select_related('family__user').order_by('family__user__name', 'name')
    html = render_to_string(
        'booking/partials/_calendar_date_blocks.html',
        {
            'lessons_by_date': sorted_lessons_by_date,
            'all_students': all_students,
        },
        request=request,
    )
    return JsonResponse({'rooms': rooms, 'html': html})

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
