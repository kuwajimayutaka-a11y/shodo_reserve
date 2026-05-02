# 補欠登録機能 仕様書

## 概要

授業枠が満席の場合、保護者が生徒を補欠リストに登録できる機能。
キャンセルが発生した際に、補欠リスト順に繰り上がり予約が確定する。

---

## ユーザーストーリー

- **保護者**: 満席の授業に補欠登録し、キャンセルが出た場合に自動で予約が確定する
- **管理者**: 補欠リストを確認・操作できる

---

## 機能仕様

### 補欠登録

- 条件: `lesson.available_slots() <= 0`（満席）かつ予約開始時刻を過ぎている
- 操作: 生徒を選択して「補欠登録」ボタンを押す
- 制約: 同じ授業に同じ生徒は1件のみ（`unique_together` 済み）
- 表示: 登録後に補欠順位（例: 補欠2番目）を表示する

### 繰り上がり処理

- トリガー: 保護者または管理者が予約をキャンセルした時
- 処理順:
  1. キャンセルされた予約を削除
  2. 対象授業の補欠リストを `waitlisted_at` 昇順で取得
  3. 先頭の `Waitlist` レコードを `Reservation` に昇格
  4. 対応する `Waitlist` レコードを削除
  5. メール通知を送信（任意）

### メール通知（任意）

- 送信タイミング: 繰り上がり確定時
- 宛先: 補欠から繰り上がった生徒の保護者
- 内容: 授業名・日時・「予約が確定しました」

---

## データモデル（実装済み）

```python
class Waitlist(models.Model):
    lesson_slot = models.ForeignKey(LessonSlot, on_delete=models.CASCADE)
    student    = models.ForeignKey(Student, on_delete=models.CASCADE)
    waitlisted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['waitlisted_at']
        unique_together = ('lesson_slot', 'student')
```

---

## 実装場所（予定）

| ファイル | 変更内容 |
|---|---|
| `booking/views.py` | `reserve_lesson` の `else` 節に補欠登録ロジックを追加 |
| `booking/views.py` | `cancel_reservation` のキャンセル処理後に繰り上がり処理を追加 |
| `booking/admin_views.py` | `cancel_reservation_admin` にも同じ繰り上がり処理を追加 |
| `booking/templates/booking/calendar.html` | 満席時に補欠登録フォームを表示。補欠順位も表示 |

---

## 未解決事項

- 繰り上がり時のメール通知を実装するか（`EMAIL_HOST_USER` が設定されている場合のみ送信でよいか）
- 補欠の上限人数を設けるか
- 保護者が自分で補欠を取り消せるようにするか
