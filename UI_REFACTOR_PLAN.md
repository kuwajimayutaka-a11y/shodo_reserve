# UI統一 改修計画書

> ✅ **実装完了（2026-07-03）** — Phase 0〜4すべて完了。base.htmlにデザインシステムを一元化、
> partials/ に共通部品8点を新設、全27テンプレートを移行。`manage.py check` パス、全画面レンダリング200確認済み。
> views/models/URL/JSロジックは非変更。


## 背景・目的
現在、画面ごとにデザイン言語が3系統混在し、統一感がない。
- **wa テーマ（茶系）**: `base.html` に全CSS定義があるが、実使用は `admin/dashboard.html` のみ（実質デッドコード）
- **Bootstrap + ティール（#0d9488）**: 大半のページ。独自 `<style>` ブロックとインラインstyleが散在
- **目標のスレート/ネイビー**: 提供スクショのモダンな配色。未実装

色のハードコードがファイルごとにバラバラ（`#2c3e50 #0d9488 #7c3aed #be123c ...`）、
インラインstyleが最大27箇所/ファイル、ページ独自`<style>`が4ファイル。

**ゴール**: スクショの配色を基調にしたデザインシステムを `base.html` に一元化し、
全テンプレートを共通クラスへ移行。ヘッダーは現状維持。

## 決定事項（確認済み）
- スコープ: **計画→承認後に実装**
- 教室バッジ: **横川=ティール / 石原=パープル の色分けを維持**（新パレットへ調和）
- アクセント: **ネイビー=構造（見出し・選択日・カレンダー）/ ブルー=操作（CTAボタン）**

---

## デザイントークン（`base.html` の `:root` に定義）

```
/* 面 */
--bg:#eef2f7;         /* アプリ背景（淡いスレート） */
--surface:#ffffff;    /* カード */
--surface-2:#f8fafc;  /* カードヘッダー等の淡い塗り */

/* 文字 */
--ink:#0f172a;        /* 見出し・主要テキスト */
--ink-2:#475569;      /* 副次テキスト */
--muted:#94a3b8;      /* 補助・プレースホルダ */
--border:#e2e8f0;
--border-strong:#cbd5e1;

/* アクセント */
--navy:#1e1b4b;       /* 構造（ヘッダー#1a1535と調和） */
--navy-2:#2e2a5d;
--blue:#3b82f6;       /* 操作（CTA） */
--blue-hover:#2563eb;
--blue-soft:#eff6ff;

/* 意味色 */
--success:#059669; --success-soft:#ecfdf5;
--danger:#e11d48;  --danger-soft:#fff1f2;   /* 「残りN枠」「満席」「エラー」 */
--warning:#d97706; --warning-soft:#fffbeb;  /* 補欠 */

/* 曜日 */
--sat:#3b82f6; --sun:#ef4444;

/* 教室（維持） */
--room-yokogawa:#0d9488; --room-yokogawa-soft:#ccfbf1;
--room-ishihara:#7c3aed; --room-ishihara-soft:#ede9fe;

/* 形状 */
--radius-card:20px; --radius-md:12px; --radius-sm:8px;
--shadow-card:0 4px 20px rgba(15,23,42,.06);
```

## 共通コンポーネントクラス（`base.html` に定義し、wa-* を置換）
- **ページ見出し**: `.page-head`（大きな太字タイトル + サブ説明）← スクショの「予約可能な授業／日付を選んで空き枠を予約」
- **カード**: `.card` / `.card-head` / `.card-body`（角丸20・ソフト影）
- **ボタン**: `.btn` `.btn-primary`(ブルー) `.btn-navy` `.btn-outline` `.btn-danger` `.btn-sm`
- **ピル/バッジ**: `.pill-danger`(残り枠) `.pill-success` `.pill-muted` `.pill-room-yokogawa` `.pill-room-ishihara`
- **フォーム**: `.field` `.label` `.input` `.select`
- **通知**: `.alert` (success/error/warning/info) ← `wa-msg` と Bootstrap `alert` を統合
- **メタ情報行**: `.meta`（アイコン+ラベル+値）
- **カレンダー**: `.cal` `.cal-nav` `.cal-grid` `.cal-cell`（状態: `today/selected/has-lesson/sat/sun`）
- **授業カード**: `.lesson-card`
- **一覧テーブル**: `.wtable`（管理画面のリスト用）

Bootstrap CDN はグリッド/ユーティリティ用に残し、ボタン・バッジ・アラート等のデフォルトは
新パレットに合わせて override（既存 override を刷新）。

## 共通化（DRY）方針
CSSクラスの共通化に加え、**繰り返し登場するマークアップをDjangoテンプレート部品**
（`booking/templates/booking/partials/`）に切り出し、`{% include %}` で再利用する。

| 部品 | `partials/` ファイル | 使用箇所 |
|------|--------------------|---------|
| ページ見出し(タイトル+サブ) | `_page_head.html` | 全ページ |
| 教室バッジ（横川/石原の色分け） | `_classroom_badge.html` | calendar, admin/calendar, cancel系, lesson_list ほか多数 |
| 授業カード | `_lesson_card.html` | calendar, admin/calendar |
| ミニカレンダー | `_mini_calendar.html`(+JS) | calendar, admin/calendar |
| 空き状況ピル（残りN枠/満席） | `_availability_pill.html` | calendar, admin系一覧 |
| フォーム項目（label+input+error） | `_field.html` | add/edit_student, create/edit_lesson, ユーザー作成 等 |
| 確認ダイアログ枠（削除/キャンセル） | `_confirm_panel.html` | delete_*, cancel_reservation(両方) |
| 空状態プレースホルダ | `_empty_state.html` | 一覧・カレンダーの0件時 |

- 教室バッジ・授業カード等は現在**各ファイルに同一markupがコピペ**されているため、
  部品化で重複を排除し、今後の色/文言変更を1箇所に集約する。
- `{% include %}` へは必要な変数（`lesson`, `classroom` 等）を明示的に渡す。
- カレンダー生成JSも共通化し、ユーザー/管理の両カレンダーで1実装を共有。

---

## 実装フェーズ

### Phase 0 — デザインシステム構築（`base.html`）
- `:root` トークンを上記に差し替え、`wa-*` コンポーネント群を新クラスへ刷新
- Bootstrap override を新パレットに更新
- ヘッダー markup / CSS は**変更しない**
- `messages` 表示を `.alert` に統一

### Phase 1 — `calendar.html`（リファレンス実装 = スクショ再現）
- ミニカレンダーをスクショ通りに: 大見出し、曜日色（土=青/日=赤）、開催日ドット、選択日ネイビー、影
- 授業カードを刷新: 時刻太字 + 時計アイコン、「残りN枠」赤ピル、教室ピル、定員アイコン、生徒select、ブルーCTA
- ページ独自 `<style>` を最小化（共通クラスへ寄せる）、AjaxのJSロジックは維持

### Phase 2 — ユーザー向けページ
`view_students / edit_student / add_student / cancel_reservation /
registration/(login, signup, email_sent, verify_success, verify_error) / logged_out`
- インラインstyle・ハードコード色を撤去し共通クラスへ

### Phase 3 — 管理画面
`admin/dashboard / calendar / create_lesson / create_lesson_single / edit_lesson /
lesson_list / reservation_list / student_management / add_student / edit_student /
delete_student / edit_family / delete_family / delete_lesson / cancel_reservation`
- 一覧は `.wtable`、フォームは共通フォームクラス、独自 `<style>` 撤去

### Phase 4 — 仕上げ・検証
- 残存インラインstyle / ページ独自 `<style>` の掃除
- 主要画面を実際に起動してスクショ確認（`/run` skill）
- デッドコード（旧 `wa-*` 定義など）削除

---

## 影響範囲・リスク
- **変更はテンプレート/CSSのみ**。views・models・URL・JSロジックは非変更（Ajax等はそのまま）
- 教室色分けロジック（`classroom == 'ishihara'`）はクラス名に置換するだけで挙動不変
- Bootstrap を残すため、グリッド崩れリスクは小。override差し替え時のみ全画面確認が必要

## 検証項目
- [ ] 全画面でヘッダーが従来通り表示される
- [ ] calendar がスクショと同等の見た目
- [ ] 予約Ajax・スナックバーが従来通り動作
- [ ] 教室バッジ（横川/石原）の色分けが維持される
- [ ] messages（成功/エラー/警告）が統一デザインで表示
- [ ] モバイル幅でカレンダー・フォームが崩れない
- [ ] 教室バッジ・授業カード・カレンダー等の重複markupが `partials/` に集約されている
- [ ] インラインstyle / ページ独自 `<style>` がほぼ残っていない
