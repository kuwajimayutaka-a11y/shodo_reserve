from django.urls import path
from . import views, admin_views

# 生徒用URL
urlpatterns = [
    path('signup/', views.SignUpView.as_view(), name='signup'),
    path('students/', views.view_students, name='view_students'),
    path('students/add/', views.add_student, name='add_student'),
    path('students/<int:student_id>/edit/', views.edit_student, name='edit_student'),
    path('students/<int:student_id>/delete/', views.delete_student, name='delete_student'),
    path('calendar/', views.reservation_calendar, name='reservation_calendar'),
    path('reserve/<int:lesson_id>/', views.reserve_lesson, name='reserve_lesson'),
    path('reservations/<int:reservation_id>/cancel/', views.cancel_reservation, name='cancel_reservation'),
]

# 管理者用URL
admin_urlpatterns = [
    path('admin-dashboard/', admin_views.admin_dashboard, name='admin_dashboard'),
    path('admin-dashboard/create-lesson/', admin_views.create_lesson_slots, name='admin_create_lesson_slots'),
    path('admin-dashboard/create-lesson-single/', admin_views.create_lesson_single, name='admin_create_lesson_single'),
    path('admin-dashboard/lessons/', admin_views.lesson_list, name='admin_lesson_list'),
    path('admin-dashboard/lessons/<int:lesson_id>/edit/', admin_views.edit_lesson_slot, name='admin_edit_lesson_slot'),
    path('admin-dashboard/lessons/<int:lesson_id>/delete/', admin_views.delete_lesson_slot, name='admin_delete_lesson_slot'),
    path('admin-dashboard/reservations/', admin_views.reservation_list, name='admin_reservation_list'),
    path('admin-dashboard/students/', admin_views.student_management, name='admin_student_management'),
    path('admin-dashboard/students/add/<int:family_id>/', admin_views.add_student_admin, name='admin_add_student'),
    path('admin-dashboard/students/<int:student_id>/edit/', admin_views.edit_student_admin, name='admin_edit_student'),
    path('admin-dashboard/students/<int:student_id>/delete/', admin_views.delete_student_admin, name='admin_delete_student'),
    path('admin-dashboard/reservations/<int:reservation_id>/cancel/', admin_views.cancel_reservation_admin, name='admin_cancel_reservation'),
]

urlpatterns += admin_urlpatterns
