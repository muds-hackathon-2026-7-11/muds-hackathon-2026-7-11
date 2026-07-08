# Virachゼミ（合同）

- **正式ゼミ名**：Virachゼミ（Virach・Thatsanee・佐々木・神崎・小林・Titi合同）
- **学部**：データサイエンス学部
- **担当教員（6名合同）**：Virach Sornlertlamvanich／Thatsanee Charoenporn／佐々木 史織／神崎 享子／小林 周／Titipakorn Prakayaphun
- **出典**：各教員の配布資料（`Virach.pdf` 全12ページ／`Thatsanee.pdf` 全4ページ／`Sasaki.pdf` 全7ページ）

> ⚠️ 本ドキュメントは配布資料に記載された事実のみをまとめています。資料に無い情報は補完していません。
>
> ⚠️ **神崎 享子・小林 周・Titipakorn Prakayaphun の3教員の資料は配布資料に含まれておらず、本ドキュメントには未反映です。** 以下は資料が提供された Virach・Thatsanee・佐々木 の3名分のみを記載しています。

## ゼミ全体像
AI・データサイエンスを社会課題の解決や社会イノベーションにつなげる点で各教員が共通する、6名合同のゼミ。資料のある3名は、(1)人間の行動・感情の認識（自然言語処理・センシング）、(2)社会イノベーションのプロトタイプ設計、(3)時空間データの可視化と社会実装、という相互に関連するテーマを扱う。タイをはじめとするアジアの大学・機関との国際共同研究が全体に共通する特徴。

---

## 1. Virach Sornlertlamvanich 教員（`Virach.pdf`）

### プロジェクト
- **未来創造プロジェクト P2-[Human_Behavior]**：Human Behavior Recognition and Social Innovation（人間行動認識と社会イノベーション）。

### 研究範囲・目的
- 人間の知的活動／会話分析によってメディアの内容・意思・感情を把握する。
- 人間の知的活動／会話の予測支援を行い、社会イノベーションにつなげる。
- 知識表現、知的活動、言語理解を扱う。
- 学際的な協力によるオープンイノベーションの構築。
- 中核概念：社会イノベーション、人間の行動、推論、知識、自然言語処理（テキスト）、環境（データ）、行動（信号）、画像／音声。

### 研究課題・手法
- **自然言語処理の基本と応用**
  - チャットボット：ドメインデータの収集・調査・分析・実装・評価を戦略的に行う。
  - SNS分析：感情分析、動向分析。
  - 連携学習：学習者向け教育ビデオの要約・キーワード抽出・場面／字幕による検索。
- **AI・データ分析の応用**
  - 介護センサーの活用：センサーデータ分析・モデル化。
  - データの見える化：画像認識、表情認識、ヒートマップ等での可視化。
- **感情の認識と行動分析**：Blockly-TEMI、7つの基本感情（Joy／Surprise／Anger／Sadness／Fear／Contempt／Disgust）、低リソース言語向けEnd-to-End音声感情認識（VAD、VTLP Augmentation、Wav2Vec2/XLSR等）、Verbal/Non-Verbalの感情コーパス構築。

### 応用テーマ・システム
- **健康情報基盤における介護ロボット**：Motion／Door／Vital／Pressure & Piezoelectric Bed 各センサー＋MQTT broker、Temiロボット操作、介護の通知・対話。
- **快適/安全な距離（Comfortable/Safe Distance）**：YOLO3による人体検出、位置計算、透視変換、座席検出、線形回帰、ソーシャルディスタンス検出とログ再生。
- **国際協力AI City／AKUD Model**：Health & Elderly care／Environment／Mobility／Economy を統合するスマートシティ基盤（PDPA準拠、Digital Twin、5DWM等）を、完全結合ネットワークのディープインテリジェントIoTとして構成。
- タイの都市住民の感情・メンタルヘルス解釈を目的とした感情コーパス構築（青年期うつのリスク統計に言及）。

### 公開物・実績
- タマサート大学Rangsitキャンパスのスマート照明ダッシュボード、AIシティAPIポータル（Baby AI Hub）。
- LLMの知識不足による欠陥（AI Model Deficiency in Knowledge Insufficiency）を、System1（LLM）×System2（真実知識）のSemantically Aware Reasoning(SAR)で補う研究。

---

## 2. Thatsanee Charoenporn 教員（`Thatsanee.pdf`）

### プロジェクト
- **Social Innovation Approach: Shaping a Balanced and sustainable world**（社会イノベーションによる、バランスが取れ持続可能な世界の形成）。

### 研究目的
- 成功した社会イノベーションに共通する新興パターンの特定・分析。
- 社会イノベーションによる構造的不平等（systemic inequalities）への対処の検討。
- 社会イノベーションにおけるコミュニティ参加の役割の調査。
- 協働デザイン（collaborative design）による革新的な社会的ソリューションのプロトタイプ開発。
- 実際のコミュニティ環境での選定プロトタイプの実装・テスト。
- 成功したプロトタイプ実装をスケールさせるためのフレームワーク構築。
- 実装したプロトタイプのインパクトの評価・文書化。

### 扱う内容（Focus Contents）
- **Data Innovation**：データ収集手法、データ分析、データガバナンス、可視化。
- **Social Innovation**：コミュニティニーズ評価、ソリューション設計、インパクト評価、スケーリング戦略、持続可能なイノベーション実践、コミュニティエンゲージメントモデル。
- **対象ドメイン**：ヘルスケア、教育、環境、食、経済的エンパワーメント など。
- **ツール**：デジタルプラットフォーム、モバイル/Webアプリ、デザインソフト、インパクト測定ツール、デザイン思考、World Balancing Concept。
- **プレゼンテーション**：ストーリーテリング、ビジュアルコミュニケーション、知識共有プラットフォーム、インパクトレポーティングのフレームワーク。
- **倫理（Ethics）**：原則と実装。

### 研究協力
- タイをはじめアジアの大学・機関との国際的な共同研究。

---

## 3. 佐々木 史織 教員（`Sasaki.pdf`）

### プロジェクト
- **デジタルビジネスイノベーション、IoT, ロボティクス**（Digital Business Innovation, IoT-Robotics）。

### プロジェクト型実習・実験の中核：5D World Map System
- **Sensing（入力）**：センサーデータ、統計データ、地理・空間データ、テキスト／画像／動画／音声データ、衛星写真、小型UAV＋マルチスペクトラルカメラ（動画＋写真）。
- **Processing（分析・可視化）**：(1)リアルタイムマッピング、(2)変化量・差分・類似性計量・探知、(3)分析的可視化、時空間データ可視化、マルチメディア検索。
- **保持DB**：メディアDB、ユーザDB、地理・空間DB、センサーDB。
- **Actuation（出力）**：(4)リアルタイム配信、アラート配信。
- **位置づけ（UN ESCAP文脈）**：Data／Statistics／Knowledge Sharing を核に、有効なデータと分析ツールの提供、世界・国・ローカルレベルのデータギャップ解消、エビデンスに基づく政策決定支援（Decision Support／Policy Makers）。

### 関連する技術要素（Sensing-Processing-Actuation）
- **IoT（Sensing）**：リアルタイム・センシング（Small Sensor - 5D）、センサーデータ・アノテーション（Data Labelling）。
- **Multimedia（Processing）**：自然言語処理・テキストマイニング、TF*IDF、画像処理・画像DB、ベクトル空間モデルによるメディア相関量計算、時空間データベース構築（PostgreSQL）。
- **Visualization（Actuation）**：地理情報データ可視化（GIS）、Warning Messaging（5D-IFTTT）によるプッシュ系メッセージ送信。
- Cyber Space × Real Space のS-P-Aループとして構成。

### 演習・応用研究
- センシング＋DB構築＋可視化の演習、感性・異文化マルチメディアコンピューティング（"Kansei" & Cross-cultural Multimedia Computing）、5Dアラート送信の実証実験、時空間・差分計量データ可視化演習。
- Web Service連携：IFTTT経由でGmail／LINE／WhatsApp／Telegramへ通知。IoTツール（Raspberry Pi、ドローン、各種センサー）を活用し、社会実装（Social Implementation／SDGs）へつなげる。
- 応用研究テーマ例：世界のニュース、絶滅危惧種、国際テロ、環境異常検知、ヘルスデータ、世界遺産・観光、世界のアート・工芸・音楽・料理、感性メディア生成 など。

---

## ゼミ選びの観点まとめ
- **共通キーワード**：AI・データサイエンス、社会イノベーション、社会実装、SDGs、国際共同研究（アジア）。
- **Virach 教員向き**：自然言語処理・チャットボット・感情/表情認識・介護AI・スマートシティに関心がある人。
- **Thatsanee 教員向き**：社会課題（不平等・コミュニティ）へのソリューションを協働デザインし、プロトタイプで検証したい人。
- **佐々木 教員向き**：IoTセンシング〜時空間データの可視化・アラート配信までを手を動かして作りたい人、感性・異文化マルチメディアに関心がある人。
- **注意**：神崎 享子・小林 周・Titipakorn Prakayaphun の3教員のテーマは配布資料が無く本書には未反映。実際のゼミ選択時は別途確認が必要。
