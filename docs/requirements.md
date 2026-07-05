# ゼミ選択・配属支援プラットフォーム

## アプリ概要

学生が研究内容や将来の興味に合ったゼミを見つけられるよう支援し、教員側の応募管理・選考業務も効率化するWebシステム。

従来のGoogleフォームによる志望調査では、

- ゼミの情報が不足している
- 志望理由を書く前に相談できない
- 他の学生の志望理由が見えてしまう
- 教員側が応募者を管理しづらい

といった課題がある。

本システムでは、

- ゼミ情報の集約
- マッチ度診断
- AI相談機能
- 現役ゼミ生とのQ&A
- 志望提出
- 教員向け応募管理

を一元化し、学生と教員双方を支援する。

## 想定ユーザー

### 学生
- どのゼミに入るか悩んでいる学生
- 志望理由を作成する学生
- ゼミの雰囲気や研究内容を知りたい学生

### 現役ゼミ生
- ゼミ紹介
- Q&A回答
- 自身の研究内容の公開

### 教員
- 応募者の確認
- 志望理由の閲覧
- ゼミ情報の管理

### 運営
- ゼミ管理
- 教員管理
- 配属結果管理

## システムの特徴

### 1. ゼミマッチング診断

学生が興味分野や研究したい内容を入力すると、各ゼミとの適合度を算出する。

例:
- AIゼミ: マッチ度 92%
- データベースゼミ: マッチ度 71%
- 知識工学ゼミ: マッチ度 64%

診断には

- 教員の研究分野
- ゼミ生の研究テーマ
- 過去の研究実績
- 志望理由

などを利用する。

### 2. AIゼミ相談アシスタント

学生が「Webアプリ開発と推薦システムに興味があります」などと相談すると、

おすすめ:
- ○○研究室
- △△研究室

理由:
- 推薦システム研究あり
- Web開発経験者多数

のように推薦を行う。

### 3. 志望理由作成支援

学生が志望理由を書くと

- 文字数チェック
- 不足項目の指摘
- ゼミとのマッチ度表示

を行う。

例:
- 現在のマッチ度: 82%
- 不足している要素:
  - 研究テーマの具体性
  - ゼミを選んだ理由

## ゼミ紹介機能

各ゼミごとに専用ページを持つ。

掲載内容例:
- 教員紹介
- 研究テーマ
- 募集人数
- 研究室写真
- DS学紹介動画要約
- 過去の研究テーマ
- 論文一覧
- 成果物一覧

## ゼミ生情報

現役ゼミ生が公開できる。

プロフィール:
- 名前
- 学年
- 研究テーマ
- 興味分野タグ

例: 機械学習、推薦システム、自然言語処理

## 分野分析

例(AIゼミ):
- 機械学習 15人
- 画像処理 8人
- 自然言語処理 5人

を可視化。

## 口コミ・レビュー機能

現役ゼミ生による口コミ。

例:
- 雰囲気: ★★★★★
- 自由度: ★★★★☆
- 忙しさ: ★★★☆☆

## ゼミQ&A機能

学生が匿名で質問可能。

例:
```
Q. プログラミング未経験でも大丈夫ですか？
  ↓
現役ゼミ生・教員が回答。
```

### Slack連携

質問投稿時:
```
Slack → 質問チャンネル → スレッド回答 → サイトへ自動反映
```

質問と回答はFAQとして蓄積される。

## 志望提出機能

学生は第1志望・第2志望・第3志望を登録する。各志望ごとに志望理由・マッチ度を確認可能。

- **下書き保存**: 自動保存対応。
- **提出状況確認**: 提出後も提出日時・志望内容を閲覧可能。

## 教員向け機能

### 応募者管理

応募者一覧の表示項目:
- 学籍番号
- 氏名
- 現在所属ゼミ
- 研究内容
- 志望順位
- 志望理由

志望順位別表示の例(AIゼミ):
- 第1志望 10人
- 第2志望 8人
- 第3志望 5人

### 応募状況分析

- 倍率
- 志望人数推移
- 学年別人数
- 継続選択率

などを表示。

### CSV出力

出力項目例:
- 学籍番号
- 氏名
- 学年
- 前回所属ゼミ
- 研究内容
- 志望順位
- 志望理由

## 運営向け機能

### 教員管理
- 教員追加
- 教員削除
- ゼミ移動

### ゼミ管理
- 定員設定
- 募集期間設定
- 紹介ページ編集

### 配属結果登録

CSVから一括登録。

### 配属履歴管理

過去の所属ゼミを閲覧可能。例: 2024年度、2025年度、2026年度

## このシステムの価値

従来の「志望理由提出システム」ではなく、**学生が研究テーマからゼミを探し、現役ゼミ生や教員の情報を参考にしながら、自分に合った研究室を見つけるためのゼミ選択支援プラットフォーム**として位置付けられる。

さらに教員側には、**応募者管理・志望理由管理・応募分析を一元化する選考支援システム**として機能する。これにより、学生・教員・運営の三者が同じプラットフォーム上でゼミ配属を進められる。

## DB設計

改訂版(2026-07-03)。募集期間・定員を「ゼミ」から切り離し、年度単位の募集ラウンドとして管理する構成に変更。

### 設計方針

- 募集期間・年度は `recruitment_terms` で全ゼミ共通に一元管理
- 定員は年度×ゼミ(`seminar_recruitments`)で管理し、教員・管理者がUIから設定可能
- 配属結果テーブルは持たず、`seminar_members` に一本化(CSVインポートの投入先もここ)
- 質問はSlack Bot経由で投稿、回答候補者へBotがDM通知し、DM内(ボタン→モーダル)で回答
- 匿名質問は `user_id` をDBに保持しつつAPIで返さない表示制御で実現(不適切発言時は管理者がDBを直接確認)
- マッチ度はLLM呼び出しを入力ハッシュでキャッシュし、提出時のスコアを志望レコードにスナップショット保存

### テーブル定義

#### recruitment_terms(募集期間・年度)

全ゼミ共通の募集期間を年度単位で管理する。

| カラム | 型 | 制約 | 説明 |
|---|---|---|---|
| id | UUID | PK | |
| academic_year | int | UNIQUE, NOT NULL | 対象年度(例: 2026) |
| starts_at | date | NOT NULL | 募集開始日 |
| ends_at | date | NOT NULL | 募集終了日(提出締切) |
| status | enum | NOT NULL | preparing / open / closed |
| created_at | timestamp | NOT NULL | |
| updated_at | timestamp | NOT NULL | |

- 提出可否の判定は `status = open` かつ `ends_at` 以前で行う
- 運営の「募集期間設定」画面はこのテーブルを編集する

#### seminars(ゼミ)

| カラム | 型 | 制約 | 説明 |
|---|---|---|---|
| id | UUID | PK | |
| name | varchar | NOT NULL | ゼミ名 |
| description | text | NULL | 研究内容・ゼミ紹介文 |
| photo_url | varchar | NULL | 研究室写真 |
| created_at | timestamp | NOT NULL | |
| updated_at | timestamp | NOT NULL | |

- 定員・募集期間は持たない(年度で変わるため `seminar_recruitments` へ)

#### seminar_recruitments(年度ごとの募集設定)

| カラム | 型 | 制約 | 説明 |
|---|---|---|---|
| id | UUID | PK | |
| term_id | UUID | FK(recruitment_terms), NOT NULL | 対象年度 |
| seminar_id | UUID | FK(seminars), NOT NULL | 対象ゼミ |
| capacity | int | NOT NULL | 募集定員 |
| is_recruiting | boolean | NOT NULL DEFAULT true | その年度に募集するか |
| | | UNIQUE(term_id, seminar_id) | |

- 定員は教員または管理者がUIから設定
- 年度作成時に前年度からコピーする機能を用意すると運用が楽

#### users(ユーザー)

| カラム | 型 | 制約 | 説明 |
|---|---|---|---|
| id | UUID | PK | |
| google_id | varchar | UNIQUE, NOT NULL | Google OAuth ID |
| slack_user_id | varchar | UNIQUE, NULL | SlackユーザーID(未連携はNULL) |
| email | varchar | UNIQUE, NOT NULL | 大学メールアドレス |
| student_id | varchar | NULL | 学籍番号(教員・運営はNULL) |
| name | varchar | NOT NULL | 氏名 |
| role | enum | NOT NULL | student / teacher / admin |
| grade | varchar | NULL | 学年(例: "B3", "MIDS/B1") |
| research_theme | varchar | NULL | 研究テーマ・研究概要(学生本人が記入。教員はNULL) |
| photo_url | varchar | NULL | 本人の写真(教員向け) |
| is_active | boolean | NOT NULL DEFAULT true | ソフトデリート用(教員削除等) |
| created_at | timestamp | NOT NULL | |
| updated_at | timestamp | NOT NULL | |

- `grade` はSlack表示名(`[B3] 氏名` 形式)からパースして同期。Slack連携時とログイン時に再取得すれば進級時の一括更新は不要
- パース失敗時は NULL のままにし、マイページから本人が手動設定できる逃げ道を用意する
- ユーザー削除は物理削除せず `is_active = false`(answers 等がFK参照しているため)
- `photo_url` はゼミ詳細ページの教員紹介欄で使う。担当ゼミの `seminars.photo_url`(研究室写真)が設定されていればそちらを優先表示し、未設定の場合のみこの教員写真にフォールバックする

#### seminar_teachers(担当教員)

| カラム | 型 | 制約 | 説明 |
|---|---|---|---|
| id | UUID | PK | |
| seminar_id | UUID | FK(seminars), NOT NULL | 担当ゼミ |
| teacher_id | UUID | FK(users), NOT NULL | 担当教員 |
| | | UNIQUE(seminar_id, teacher_id) | |

- 教員の複数ゼミ担当・ゼミの複数教員に対応

#### seminar_materials(ゼミ紹介資料)

| カラム | 型 | 制約 | 説明 |
|---|---|---|---|
| id | UUID | PK | |
| seminar_id | UUID | FK(seminars), NOT NULL | 対象ゼミ |
| url | varchar | NOT NULL | 資料URL |
| type | enum | NOT NULL | slide / pdf / video |

#### seminar_members(所属ゼミ生 = 配属結果)

配属結果と所属履歴を兼ねる。運営のCSVインポートはこのテーブルに直接登録する。

| カラム | 型 | 制約 | 説明 |
|---|---|---|---|
| id | UUID | PK | |
| seminar_id | UUID | FK(seminars), NOT NULL | 所属ゼミ |
| student_id | UUID | FK(users), NOT NULL | 学生 |
| academic_year | int | NOT NULL | 所属年度 |
| | | UNIQUE(seminar_id, student_id, academic_year) | |

- 現所属は「academic_year = 現在の年度」で導出(`is_current` フラグは持たない)
- マイページの「現在所属ゼミ」、ゼミ詳細の「現在のゼミ生」、配属履歴(過去年度)はすべてこのテーブルから取得

#### application_forms(志望提出)

| カラム | 型 | 制約 | 説明 |
|---|---|---|---|
| id | UUID | PK | |
| term_id | UUID | FK(recruitment_terms), NOT NULL | 対象年度 |
| student_id | UUID | FK(users), NOT NULL | 提出者 |
| status | enum | NOT NULL | draft / submitted |
| submitted_at | timestamp | NULL | 最終提出日時 |
| created_at | timestamp | NOT NULL | |
| updated_at | timestamp | NOT NULL | |
| | | UNIQUE(term_id, student_id) | |

- 学生1人×1年度につき1レコード(複数年度の再提出に対応)
- 取り下げはなし。status は draft → submitted の一方向
- 提出後も締切前なら上書き可能: choices を差し替えて `submitted_at` を更新する

#### application_choices(志望内容)

| カラム | 型 | 制約 | 説明 |
|---|---|---|---|
| id | UUID | PK | |
| application_form_id | UUID | FK(application_forms), NOT NULL | 提出データ |
| seminar_id | UUID | FK(seminars), NOT NULL | 志望ゼミ |
| priority | int | NOT NULL, CHECK (priority BETWEEN 1 AND 3) | 志望順位 |
| reason | text | NOT NULL | 志望理由 |
| match_score | int | NULL | 提出時点のマッチ度スナップショット(0-100) |
| match_feedback | jsonb | NULL | 不足要素などLLMの指摘内容 |
| | | UNIQUE(application_form_id, priority) | 同順位の重複防止 |
| | | UNIQUE(application_form_id, seminar_id) | 同一ゼミの重複志望防止 |

- 上書き時は同一 form の choices を delete & insert(または upsert)で差し替え
- 提出時に `match_evaluations` の最新値を `match_score` / `match_feedback` にコピーして確定(履歴として保持)

#### match_evaluations(マッチ度キャッシュ)

LLM呼び出し回数を減らすためのキャッシュ。消えても再計算できる設計。

| カラム | 型 | 制約 | 説明 |
|---|---|---|---|
| id | UUID | PK | |
| user_id | UUID | FK(users), NOT NULL | 学生 |
| seminar_id | UUID | FK(seminars), NOT NULL | 対象ゼミ |
| input_hash | varchar | NOT NULL | 入力(志望理由+研究概要+ゼミ情報バージョン)のハッシュ |
| score | int | NOT NULL | マッチ度(0-100) |
| feedback | jsonb | NULL | 不足要素などの指摘 |
| created_at | timestamp | NOT NULL | |

INDEX: `(user_id, seminar_id, input_hash)`

- 同一ハッシュがあればキャッシュを返し、LLMを呼ばない(文面が変わったときだけ計算)
- フロント側でも「前回チェックから本文が変わっていなければボタン無効化」+ デバウンスを入れ、実質1文面1回にする

#### questions(質問)

Slack Bot経由で投稿される。公開チャンネルには投稿しない。

| カラム | 型 | 制約 | 説明 |
|---|---|---|---|
| id | UUID | PK | |
| seminar_id | UUID | FK(seminars), NOT NULL | 対象ゼミ |
| user_id | UUID | FK(users), NOT NULL | 質問者(常に保持) |
| content | text | NOT NULL | 質問内容 |
| status | enum | NOT NULL | waiting / answered / closed |
| created_at | timestamp | NOT NULL | |

- 匿名化はAPIレスポンスで `user_id` を返さない表示制御で実現(一般ユーザー・教員には見せない)
- 不適切発言があった場合、管理者はDBを直接クエリして投稿者を特定できる(専用UIは不要)

#### answer_requests(回答依頼)

質問投稿時に、対象ゼミの現役ゼミ生(現年度の seminar_members)+ 担当教員のうちSlack連携済みユーザーへBotがDM通知し、その対応付けを管理する。

| カラム | 型 | 制約 | 説明 |
|---|---|---|---|
| id | UUID | PK | |
| question_id | UUID | FK(questions), NOT NULL | 対象質問 |
| user_id | UUID | FK(users), NOT NULL | 通知を受けた回答候補者 |
| slack_dm_channel_id | varchar | NOT NULL | BotとのDMチャンネルID |
| slack_message_ts | varchar | NOT NULL | 通知メッセージのts |
| status | enum | NOT NULL | pending / answered / skipped |
| responded_at | timestamp | NULL | 回答・スキップ日時 |
| created_at | timestamp | NOT NULL | |
| | | UNIQUE(question_id, user_id) | |

- 通知メッセージには「回答する」ボタンを付け、モーダルの `private_metadata` に question_id を埋め込んで対応付ける
- `slack_message_ts` により、回答が付いた後に他の候補者の通知メッセージを `chat.update` で「回答済み」表示に更新できる
- 未回答リマインド(例: 24時間後に再通知)もこのテーブルの `status = pending` を見て実装

#### answers(回答)

| カラム | 型 | 制約 | 説明 |
|---|---|---|---|
| id | UUID | PK | |
| question_id | UUID | FK(questions), NOT NULL | 対象質問 |
| user_id | UUID | FK(users), NOT NULL | 回答者 |
| content | text | NOT NULL | 回答内容 |
| source | enum | NOT NULL | web / slack |
| created_at | timestamp | NOT NULL | |

- Slackモーダル経由の回答は通常のAPI書き込みと同じ経路になるため、重複取り込み防止用のカラムは不要
- 回答者は必ずSlack連携済みユーザーなので `users.slack_user_id` で解決できる
- 最初の回答が付いた時点で `questions.status = answered` に更新(追加回答も可能)
- 質問と回答はFAQとしてサイトに蓄積・表示される

#### notifications(通知履歴)

| カラム | 型 | 制約 | 説明 |
|---|---|---|---|
| id | UUID | PK | |
| user_id | UUID | FK(users), NOT NULL | 通知対象 |
| type | enum | NOT NULL | deadline / answer / application / question |
| message | text | NOT NULL | 通知内容 |
| related_type | varchar | NULL | 遷移先の種別(例: 'question') |
| related_id | UUID | NULL | 遷移先のID |
| read_at | timestamp | NULL | 既読日時(NULL = 未読) |
| created_at | timestamp | NOT NULL | |

- 「回答がありました」通知から質問詳細へ遷移するために `related_type` / `related_id` を使用

### ER図

```
recruitment_terms
├── seminar_recruitments ──── seminars
└── application_forms
         └── application_choices ── seminars

users
├── seminar_teachers ───────── seminars
├── seminar_members ────────── seminars   ← 配属結果を兼ねる
├── application_forms
├── questions ──────────────── seminars
│        ├── answer_requests ─ users(回答候補者)
│        └── answers
├── match_evaluations ──────── seminars
└── notifications

seminars
├── seminar_materials
└── seminar_teachers
```

### 主要フロー別のテーブル利用

#### 志望提出(上書き対応)

1. 学生が志望理由を編集 → `application_forms`(draft)+ `application_choices` に自動保存
2. マッチ度チェック → `match_evaluations` をハッシュで検索、なければLLM実行して保存
3. 提出 → status を submitted に、`submitted_at` を更新、最新マッチ度を choices にコピー
4. 締切前の上書き → choices を差し替え、`submitted_at` を更新(status は submitted のまま)

#### 質問〜回答(Slack DM完結)

1. 学生がSlack Botで質問投稿 → `questions` 作成
2. 対象ゼミの現役ゼミ生 + 担当教員(Slack連携済み)へDM通知 → `answer_requests` 作成
3. 回答者がDMの「回答する」ボタン → モーダルで回答 → `answers` 作成
4. `questions.status = answered`、該当 `answer_requests.status = answered`、他候補者の通知メッセージを更新
5. 質問者へ回答通知(`notifications` + Slack DM)、サイトのFAQに反映

#### 年度切り替え

1. 運営が新年度の `recruitment_terms` を作成
2. `seminar_recruitments` を前年度からコピーし、定員を調整
3. 配属確定後、CSVインポートで `seminar_members` に新年度の所属を登録

### Phase2で追加予定

- **reviews**(ゼミ口コミ): id, seminar_id, user_id, rating, comment, created_at
- **papers**(論文・成果物): id, seminar_id, title, url, published_year
- **research_tags**(研究分野マスタ)
- **seminar_tags**(ゼミ×研究分野)
- **user_interest_tags**(学生の興味分野)
- **chat_logs**(AIチャットボット履歴): id, user_id, message, response, created_at

## 画面設計

MVPをもとにすると、Slackを入口、Webをメイン画面とした構成が最も使いやすい。

### 全体の画面遷移

```
                   Googleログイン
                          │
                          ▼
                    Slackアカウント連携
                          │
                          ▼
                   Slack Bot(Home/DM)
      ┌──────────┼────────────┐
      │          │            │
      ▼          ▼            ▼
   質問する   通知確認    マイページ
                              │
                     （自動ログイン）
                              ▼
                    Web マイページ
      ┌──────────┼──────────────┐
      ▼          ▼              ▼
   ゼミ一覧    FAQ一覧      志望提出
      │          │              │
      ▼          ▼              ▼
ゼミ詳細     質問詳細      応募状況
```

### Slack画面

**① Home画面** — 最初に表示されるポータル。サービス名、アプリに飛ぶ用のボタン、質問ボタン。

**② 質問画面** — BotとのDM。

```
質問する
  ↓
ゼミを選択
  □ AIゼミ
  □ DBゼミ
  □ HCIゼミ
  ----------------
  質問内容
  [送信]
  ↓ 送信後
  送信しました！
  回答が届いたら通知します。
```

**③ 通知**
```
🔔 締切まで3日です
────────────
AIゼミへの質問に回答がありました
```

### Web画面

**① マイページ**
```
プロフィール
  名前
  学籍番号
  研究概要（変更可）
  現在所属ゼミ
----------------
提出状況
  未提出
  [志望提出]
  [応募状況]
  [FAQ]
```

**② ゼミ一覧**
```
AIゼミ
  倍率
  定員
----------------
DBゼミ
  倍率
  定員
クリック
  ↓
ゼミ詳細
```

**③ ゼミ詳細**
```
AIゼミ
  教員紹介
  研究内容
  募集人数
  継続人数
----------------
紹介資料
  PDF
  動画
----------------
現在のゼミ生
  研究概要一覧
  ↓ ここから質問する も押せる
```

**④ FAQ**
```
検索: AI
----------------
Python必須ですか？
  ↓
回答

ゼミごとの絞り込み
  AIゼミ / DBゼミ / HCIゼミ
```

**⑤ 志望提出**
```
第1志望
  理由
------------
第2志望
  理由
------------
第3志望
  理由
------------
文字数
マッチ度
------------
[下書き保存]
[提出]
```

**⑥ 応募状況**
```
AIゼミ
  第1志望 8
  第2志望 2
  倍率 1.5
──────────
DBゼミ
  ...
```

### 教員画面

```
担当ゼミ
  ↓
応募者一覧
----------------
山田
  第1志望
  理由
----------------
CSV出力
```

応募者詳細: 氏名、学籍番号、過去ゼミ、志望理由、研究概要

### 運営画面

```
募集期間
  ↓
ゼミ管理
  ↓
教員管理
  ↓
CSVインポート
```

### 画面遷移図

```
【Slack】
Home
├─ 質問する
├─ 通知
└─ マイページ
       │
       ▼
【Web】
マイページ
├─ ゼミ一覧
│      └─ ゼミ詳細
│              └─ FAQ
├─ FAQ一覧
├─ 志望提出
└─ 応募状況

【教員】
応募者一覧
└─ 応募者詳細

【運営】
管理画面
├─ 教員管理
├─ ゼミ管理
├─ 募集期間設定
└─ CSVインポート
```

### MVPで実装する画面一覧

**Slack**
- Home（ポータル）
- 質問投稿
- 通知

**Web（学生）**
- ログイン（初回のみ）
- マイページ
- ゼミ一覧
- ゼミ詳細
- FAQ一覧・詳細
- 志望提出
- 応募状況

**Web（教員）**
- 応募者一覧
- 応募者詳細

**Web（運営）**
- 管理画面
- 教員・ゼミ管理
- CSVインポート

この程度の画面数であれば、MVPとしては十分に機能を満たしつつ、実装規模も現実的です。

### 補足メモ

- メニューバー: マイページ、配属状況
- ゼミ一覧: 定員、倍率、継続率、それぞれの詳細へ
- 資料・ゼミ生一覧: ゼミ生がどんな研究してるか、質問ページへ（各ゼミごと）
- 教員向け: マッチ度いらない、継続表示いいね、学年ごと、CSVに出力（自分のゼミ、全体csv）
