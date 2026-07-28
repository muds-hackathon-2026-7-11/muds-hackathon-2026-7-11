# 志望理由データのスプレッドシート自動連携(#223)

管理者が用意したGoogleスプレッドシートに、志望理由データ(全ゼミ横断)を
定期的に自動反映する仕組み。既存の「教員が手動でCSVダウンロードする」
機能(`/teacher/applicants/all.csv`)と同じデータを、Google Apps Script
経由で数分おきに自動取得してシートに書き込む(プル型)。

対象読者は管理者(スプレッドシートを用意する人)。

## 仕組み

- スプレッドシートに紐付けたGoogle Apps Scriptが時間トリガー(例: 5分おき)
  で動く
- Apps Scriptがこのシステムの専用エンドポイント(`GET /teacher/applicants/export`)
  を呼び出し、JSONで全ゼミ横断の志望理由データを取得する
- 取得したデータでシートの内容を上書きする(差分反映ではなく、毎回全件で
  作り直す。実装がシンプルで、削除・変更も自然に反映されるため)
- 認証はGoogleアカウントのOAuthではなく、専用の固定キーをリクエストヘッダに
  載せる方式(Apps Script側でJWT/OAuthを組むのは煩雑なため)
- このキーは管理者画面(`/admin/sheets-export`)から発行・再発行する。
  開発者に頼らず管理者が自己完結できる(`.env`への設定は不要)

## 管理者側の準備(1回だけ)

1. `/admin/sheets-export` を開き、「発行する」ボタンでキーを発行する
2. データを入れたいGoogleスプレッドシートを新規作成する(または既存のものを用意する)
3. スプレッドシートのメニューから「拡張機能 → Apps Script」を開く
4. デフォルトで開かれる `コード.gs` の中身を全部消し、下記のスクリプトを貼り付ける
5. 左メニューの歯車アイコン(プロジェクトの設定)→「スクリプト プロパティ」で、
   以下の2つを追加する:
   - `API_URL`: `https://<本番ドメイン>/backend/teacher/applicants/export`
   - `EXPORT_KEY`: 手順1で発行したキー(管理者画面からコピーできる)
6. 上部の「実行」ボタンを1回押し、Googleアカウントへのアクセス許可を承認する
   (スプレッドシートへの書き込み権限を求められる)
7. 左メニューの時計アイコン(トリガー)→「トリガーを追加」で、
   関数 `syncApplicants`・イベントのソース「時間主導型」・
   「分ベースのタイマー」→「5分おき」等を選んで保存する

これで、以降は放っておけば自動的にシートが更新され続ける。

### Apps Scriptのひな形

```javascript
function syncApplicants() {
  const props = PropertiesService.getScriptProperties();
  const apiUrl = props.getProperty("API_URL");
  const exportKey = props.getProperty("EXPORT_KEY");

  const response = UrlFetchApp.fetch(apiUrl, {
    headers: { "X-Sheets-Export-Key": exportKey },
    muteHttpExceptions: true,
  });
  if (response.getResponseCode() !== 200) {
    throw new Error(
      "取得に失敗しました: " + response.getResponseCode() + " " + response.getContentText()
    );
  }

  const seminars = JSON.parse(response.getContentText());
  const rows = [
    ["ゼミ", "志望順位", "学年", "学籍番号", "氏名", "研究タイトル", "研究概要", "志望理由"],
  ];
  for (const seminar of seminars) {
    for (const applicant of seminar.applicants) {
      rows.push([
        seminar.seminar_name,
        applicant.priority,
        applicant.grade || "",
        applicant.student_id || "",
        applicant.name,
        applicant.research_title || "",
        applicant.research_theme || "",
        applicant.reason,
      ]);
    }
  }

  const sheet = SpreadsheetApp.getActiveSpreadsheet().getSheets()[0];
  sheet.clearContents();
  sheet.getRange(1, 1, rows.length, rows[0].length).setValues(rows);
}
```

## キーを失効させたい場合

`/admin/sheets-export` で「再発行する」を押すと、古いキーはその場で
無効になる(DBには常に最新の1件しか残らない)。再発行後は、Apps Script側の
`EXPORT_KEY`(スクリプト プロパティ)を新しい値に更新する必要がある。
