# data/

実在の個人情報(教員氏名・メールアドレス・写真URL等)を含むデータファイルを置く場所。
このディレクトリの中身(このREADME以外)はgit管理対象外。

## ゼミ・教員データ

1. `data/seminar_teacher.csv`という名前のcsvを置く
   (列: `ゼミ名, ゼミ紹介文, 教員写真URL, 定員, 対象年度, 教員氏名, 教員メールアドレス`)
2. DBに投入する:

   ```sh
   make import-seminars
   ```

   別名のファイルを使う場合は `make import-seminars csv=data/<ファイル名>.csv` のように指定する。

## 学生・教員データ(Slackメンバー一覧)

1. Slack管理画面のメンバー一覧をCSVエクスポートし、`data/users.csv`という名前で置く
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
