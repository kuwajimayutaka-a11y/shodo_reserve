from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import CustomUser, LessonSlot, Student, StudentGroup, CLASSROOM_CHOICES


class SignUpForm(UserCreationForm):
    class Meta:
        model = CustomUser
        fields = ('email', 'name', 'password1', 'password2')
        labels = {
            'email': 'メールアドレス',
            'name': '氏名',
        }
        widgets = {
            'email': forms.EmailInput(attrs={'placeholder': 'example@email.com', 'class': 'form-control'}),
            'name': forms.TextInput(attrs={'placeholder': '例: 山田 花子', 'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['password1'].widget.attrs.update({'class': 'form-control'})
        self.fields['password2'].widget.attrs.update({'class': 'form-control'})

    def clean_email(self):
        email = self.cleaned_data.get('email')
        # 未認証（is_active=False）の既存ユーザーは削除して再登録を許可
        CustomUser.objects.filter(email=email, is_active=False).delete()
        return email


class LessonSlotCreateForm(forms.Form):
    title = forms.CharField(
        max_length=200,
        required=False,
        label="授業名 (任意)",
        widget=forms.TextInput(attrs={'placeholder': '例: 書道教室'})
    )
    start_date = forms.DateField(
        label="開始日",
        widget=forms.DateInput(attrs={'type': 'date'})
    )
    end_date = forms.DateField(
        label="終了日 (この日を含む)",
        widget=forms.DateInput(attrs={'type': 'date'})
    )
    DAYS_OF_WEEK = [
        (0, '月曜日'), (1, '火曜日'), (2, '水曜日'), (3, '木曜日'),
        (4, '金曜日'), (5, '土曜日'), (6, '日曜日'),
    ]
    days_of_week = forms.MultipleChoiceField(
        choices=DAYS_OF_WEEK,
        widget=forms.CheckboxSelectMultiple,
        label="繰り返し設定 (曜日)",
    )
    capacity = forms.IntegerField(
        label="定員",
        min_value=1,
        initial=16,
        widget=forms.NumberInput(attrs={'min': 1})
    )
    reservation_start_datetime = forms.DateTimeField(
        label="予約開始日時",
        widget=forms.DateTimeInput(attrs={'type': 'datetime-local'}, format='%Y-%m-%dT%H:%M'),
        help_text="この日時から予約を受け付けます。"
    )
    classroom = forms.ChoiceField(
        choices=CLASSROOM_CHOICES,
        label='教室',
        initial='yokogawa',
        widget=forms.Select(),
    )

    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get("start_date")
        end_date = cleaned_data.get("end_date")
        if start_date and end_date and start_date > end_date:
            raise forms.ValidationError("開始日は終了日よりも前の日付を設定してください。")
        return cleaned_data


class LessonSlotEditForm(forms.ModelForm):
    class Meta:
        model = LessonSlot
        fields = ['title', 'classroom', 'start_time', 'end_time', 'capacity', 'reservation_start_time']
        widgets = {
            'title': forms.TextInput(attrs={'placeholder': '任意'}),
            'start_time': forms.DateTimeInput(attrs={'type': 'datetime-local'}, format='%Y-%m-%dT%H:%M'),
            'end_time': forms.DateTimeInput(attrs={'type': 'datetime-local'}, format='%Y-%m-%dT%H:%M'),
            'reservation_start_time': forms.DateTimeInput(attrs={'type': 'datetime-local'}, format='%Y-%m-%dT%H:%M'),
        }
        labels = {'title': '授業名 (任意)'}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['title'].required = False
        if self.instance and self.instance.pk:
            self.initial['start_time'] = self.instance.start_time.strftime('%Y-%m-%dT%H:%M')
            self.initial['end_time'] = self.instance.end_time.strftime('%Y-%m-%dT%H:%M')
            self.initial['reservation_start_time'] = self.instance.reservation_start_time.strftime('%Y-%m-%dT%H:%M')


class LessonSlotSingleCreateForm(LessonSlotEditForm):
    """授業枠個別作成用。作成後に自動予約するグループを選べる（編集画面では使わない）。"""
    student_group = forms.ModelChoiceField(
        queryset=StudentGroup.objects.all(),
        required=False,
        label="自動予約グループ (任意)",
        help_text="選択すると、作成した授業枠にこのグループの生徒を自動的に予約します。",
    )


class StudentModelMultipleChoiceField(forms.ModelMultipleChoiceField):
    def label_from_instance(self, obj):
        return f"{obj.name}（{obj.family.user.name}）"


class StudentGroupForm(forms.ModelForm):
    students = StudentModelMultipleChoiceField(
        queryset=Student.objects.select_related('family__user').order_by('family__user__name', 'name'),
        required=False,
        widget=forms.CheckboxSelectMultiple,
        label="生徒",
    )

    class Meta:
        model = StudentGroup
        fields = ['name', 'students']
        labels = {'name': 'グループ名'}
        widgets = {'name': forms.TextInput(attrs={'placeholder': '例: 水10:00グループ'})}


class LessonTimeSlotForm(forms.Form):
    """一括作成の1コマ分（時間帯・対象週・自動予約グループ）"""
    start_time = forms.TimeField(
        label="開始時刻",
        widget=forms.TimeInput(attrs={'type': 'time'}),
    )
    end_time = forms.TimeField(
        label="終了時刻",
        widget=forms.TimeInput(attrs={'type': 'time'}),
    )
    weeks_of_month = forms.CharField(
        required=False,
        label="対象週 (任意)",
        widget=forms.TextInput(attrs={'placeholder': '例: 1,2（空欄なら毎週）'}),
        help_text="第N週のみ開催する場合にカンマ区切りで指定（空欄なら毎週）。",
    )
    student_group = forms.ModelChoiceField(
        queryset=StudentGroup.objects.all(),
        required=False,
        label="自動予約グループ (任意)",
    )

    def clean(self):
        cleaned_data = super().clean()
        start_time = cleaned_data.get("start_time")
        end_time = cleaned_data.get("end_time")
        if start_time and end_time and start_time >= end_time:
            raise forms.ValidationError("終了時刻は開始時刻より後にしてください。")

        weeks_of_month = cleaned_data.get("weeks_of_month", "").strip()
        if weeks_of_month:
            try:
                cleaned_data["weeks_of_month_list"] = [
                    int(w) for w in weeks_of_month.split(',') if w.strip()
                ]
            except ValueError:
                raise forms.ValidationError("対象週は「1,2」のようにカンマ区切りの数字で入力してください。")
        else:
            cleaned_data["weeks_of_month_list"] = None
        return cleaned_data


LessonTimeSlotFormSet = forms.formset_factory(
    LessonTimeSlotForm, can_delete=True, extra=0, min_num=1, validate_min=True,
)


class StudentForm(forms.ModelForm):
    class Meta:
        model = Student
        fields = ['name']
        labels = {'name': '生徒氏名'}
        widgets = {'name': forms.TextInput(attrs={'placeholder': '例: 山田太郎'})}


class FamilyEditForm(forms.Form):
    name = forms.CharField(
        max_length=100, label='保護者氏名',
        widget=forms.TextInput(attrs={'placeholder': '例: 山田 花子'})
    )
    phone_number = forms.CharField(
        max_length=15, required=False, label='電話番号',
        widget=forms.TextInput(attrs={'placeholder': '例: 090-1234-5678'})
    )
    access_yokogawa = forms.BooleanField(
        required=False, label='通常教室（横川）',
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
    )
    access_ishihara = forms.BooleanField(
        required=False, label='石原教室',
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
    )
