# data/

実在の個人情報(教員氏名・メールアドレス・写真URL等)を含むデータファイルを置く場所。
このディレクトリの中身(このREADME以外)はgit管理対象外。

## セットアップの流れ(初回・まとめ)

リポジトリ全体のセットアップ(`make install` / `make setup-auth` / `make dev`)は
ルートの [README.md](../README.md) 参照。DB起動後、実データを投入するまでの流れ:

```sh
make migrate       # テーブル作成
# data/seminar_teacher.csv, slack_member.csv, users_seminar.csv をこのディレクトリに置く(下記参照)
make import-data   # ゼミ・教員・学生＋ゼミ知識をまとめて投入
```

募集期間(recruitment_terms)・ゼミごとの定員(seminar_recruitments)は運営向けAPI/UI
([Backend] 運営: 募集ラウンド・定員設定API #57)から設定する。CSVインポートはゼミ・
教員・学生の基本情報のみを扱う。

## ゼミ・教員データ

1. `data/seminar_teacher.csv`という名前のcsvを置く
   (列: `ゼミ名, ゼミ紹介文, 教員写真URL, 教員氏名, 教員メールアドレス`)
2. DBに投入する:

   ```sh
   make import-seminars
   ```

   別名のファイルを使う場合は `make import-seminars csv=data/<ファイル名>.csv` のように指定する。

## 学生・教員データ(Slackワークスペースのメンバー一覧)

1. Slack管理画面から**ワークスペース全体**のメンバー一覧をCSVエクスポートし、
   `data/slack_member.csv`という名前で置く(部署・学科を絞る必要は無い。
   絞り込みはスクリプト側で行う)
   (列: `username, email, status, billing-active, has-2fa, has-sso, userid,
   fullname, displayname, expiration-timestamp`。`fullname`は
   `[学年] 氏名 / Romanized Name`形式、教員は`[教員] 氏名 / Romanized Name`)
2. DBに投入する:

   ```sh
   make import-users
   ```

   別名のファイルを使う場合は `make import-users csv=data/<ファイル名>.csv` のように指定する。
   ログイン前に投入しておけば、学生が実際にGoogleログインした際にメールアドレス
   一致で自動的にアカウントが紐付く。

   このスクリプトは以下を自動で行う:
   - `status`が`Deactivated`(Slackから退出済み)の行は無視する
     (`billing-active`は現役Memberでも0になるケースがあり信頼できないため見ない)
   - 学年が既知のパターン(`B1`-`B4`, `MIDS/B1`-`B4`, `M1`/`M2`/`D1`等、`guest`可)
     でない行(卒業生の「卒」、他学科、提携企業ゲスト、重複アカウント等)は無視する
   - CSVに存在しなくなった(卒業/退学した)**学生**を自動で非アクティブ化する
     (ログイン不可になる。再登場したら自動で復活)
   - **教員は非アクティブ化の対象外**(Slack在籍と実際の在職状況が一致しない
     ケースがあるため)。教員の退職時は手動で`is_active`を`false`にすること

## 学生の所属ゼミデータ

学生が現在どのゼミに所属しているかを投入する。マッチ度診断や、提出時の研究概要必須化
などの判定に使われる。

1. `data/users_seminar.csv`という名前のcsvを置く
   (列: `学籍番号, 名前, 配属先`)
   - `学籍番号`は数字のみ(例: `2522091`)。DBの`student_id`(`s`/`g`接頭辞付き)とは
     両方の接頭辞を試して照合する
   - `名前`は照合には使わず、学生が見つからない場合の警告表示にのみ使う
     (氏名の正本は`import_users`が管理する)
   - `配属先`はゼミ名と**完全一致**で照合する(先に`import-seminars`でゼミを作成しておくこと)
2. DBに投入する:

   ```sh
   make import-seminar-members
   ```

   別名のファイルを使う場合は `make import-seminar-members csv=data/<ファイル名>.csv`、
   年度を指定する場合は `make import-seminar-members year=2026` のように指定する
   (年度は既定で現在の暦年)。

   このスクリプトは以下を自動で行う:
   - 指定年度の募集期間(`recruitment_terms`)が無ければ作成する
   - 学生・ゼミのどちらかが見つからない行は、エラーで止めずスキップして警告を出す
   - 同一学生が当該年度に既に別ゼミへ登録されていればCSVの内容で上書きする
     (配属訂正・異動を想定したべき等処理)

## ゼミ資料(PDF) — AI用の要約知識

マッチ度診断・AIゼミ相談アシスタントが参照する「ゼミの要約知識」を、ゼミ紹介PDFから
生成して投入する。

1. `data/seminar_docs/` ディレクトリを作り、**ファイル名をゼミ名**にしたPDFを置く
   (例: `data/seminar_docs/AIゼミ.pdf`)。ファイル名(拡張子除く)が `seminars.name`
   と一致するゼミに紐づく(先に `import-seminars` でゼミを作成しておくこと)。
2. 投入する(OpenAIでPDFを要約し `seminars.knowledge` に保存する。**OpenAIの課金/quotaが必要**):

   ```sh
   make import-seminar-docs
   ```

   別ディレクトリを使う場合は `make import-seminar-docs dir=data/<ディレクトリ>` のように指定する。

- 要約はリクエスト時ではなくこの投入時に一度だけ生成し、DBに保存する(APIは実行時にPDFを読まない)。
- PDFを差し替えたら再実行すれば `knowledge` が上書きされる。

## まとめて投入

デフォルトのファイル名(`seminar_teacher.csv`, `slack_member.csv`, `users_seminar.csv`)が
揃っていれば、

```sh
make import-data
```

で`import-seminars`→`import-users`→`import-seminar-members`→`import-seminar-knowledge`
の順にまとめて実行できる。

- `import-seminar-knowledge`はリポジトリ管理下の`docs/seminars/knowledge/`を読むため、
  `data/`への追加配置は不要。
- OpenAIを使うPDF要約(`make import-seminar-docs`)は`import-data`に**含まれない**ため、
  必要な場合のみ個別に実行する。
