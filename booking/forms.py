from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import CustomUser, LessonSlot, Student


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
    time_slots = forms.CharField(
        label="授業時間 (1行に1つ、HH:MM-HH:MM形式)",
        widget=forms.Textarea(attrs={
            'rows': 5,
            'placeholder': '例:\n09:00-10:00\n10:30-11:30\n13:00-14:00'
        }),
        help_text="1日の複数の授業時間を入力してください。1行に1つ、「開始時刻-終了時刻」の形式で入力。"
    )
    capacity = forms.IntegerField(
        label="定員",
        min_value=1,
        initial=5,
        widget=forms.NumberInput(attrs={'min': 1})
    )
    reservation_start_datetime = forms.DateTimeField(
        label="予約開始日時",
        widget=forms.DateTimeInput(attrs={'type': 'datetime-local'}, format='%Y-%m-%dT%H:%M'),
        help_text="この日時から予約を受け付けます。"
    )

    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get("start_date")
        end_date = cleaned_data.get("end_date")
        time_slots = cleaned_data.get("time_slots")
        if start_date and end_date and start_date > end_date:
            raise forms.ValidationError("開始日は終了日よりも前の日付を設定してください。")
        if time_slots:
            for line in time_slots.strip().split('\n'):
                line = line.strip()
                if line and '-' not in line:
                    raise forms.ValidationError("時間は「HH:MM-HH:MM」の形式で入力してください。")
        return cleaned_data


class LessonSlotEditForm(forms.ModelForm):
    class Meta:
        model = LessonSlot
        fields = ['title', 'start_time', 'end_time', 'capacity', 'reservation_start_time']
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


class StudentForm(forms.ModelForm):
    class Meta:
        model = Student
        fields = ['name']
        labels = {'name': '生徒氏名'}
        widgets = {'name': forms.TextInput(attrs={'placeholder': '例: 山田太郎'})}
