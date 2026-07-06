# data/

実在の個人情報(教員氏名・メールアドレス・写真URL等)を含むデータファイルを置く場所。
このディレクトリの中身(このREADME以外)はgit管理対象外。

## セットアップの流れ(初回・まとめ)

リポジトリ全体のセットアップ(`make install` / `make setup-auth` / `make dev`)は
ルートの [README.md](../README.md) 参照。DB起動後、実データを投入するまでの流れ:

```sh
make migrate       # テーブル作成
# data/seminar_teacher.csv と data/slack_member.csv をこのディレクトリに置く(下記参照)
make import-data   # ゼミ・教員・学生データをまとめて投入
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

## まとめて投入

デフォルトのファイル名(`seminar_teacher.csv`, `slack_member.csv`)で両方揃っていれば、

```sh
make import-data
```

で`import-seminars`→`import-users`の順にまとめて実行できる。
