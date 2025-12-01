from django import template
from django.utils.safestring import mark_safe
import json

register = template.Library()

@register.filter
def get_item(dictionary, key):
    """辞書からキーに対応する値を取得する"""
    return dictionary.get(key)

@register.filter
def make_list(value):
    """整数を1からその値までのリストに変換する"""
    try:
        return range(1, int(value) + 1)
    except ValueError:
        return []

@register.filter
def get_reservable_count(lessons):
    """レッスンリスト内の予約可能な枠の合計数を計算する"""
    count = 0
    for lesson in lessons:
        # lessonオブジェクトにavailable_slots()の結果がlesson.available_slotsとして付加されている前提
        if hasattr(lesson, 'available_slots'):
            count += lesson.available_slots
    return count

@register.filter
def to_json(value):
    """PythonオブジェクトをJSON文字列に変換する"""
    return mark_safe(json.dumps(value, default=str))
