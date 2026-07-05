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
