import { AuthMenuBar } from "../../components/auth-menu-bar";

const quickActions = [
  {
    title: "ゼミ一覧を見る",
    description: "興味のある研究分野やゼミ紹介を探す。",
  },
  {
    title: "志望提出を続ける",
    description: "下書き保存済みの志望理由を編集して提出する。",
  },
  {
    title: "FAQを確認する",
    description: "プログラミング未経験や雰囲気の質問を確認する。",
  },
];

const currentApplication = [
  { label: "第1志望", value: "AIゼミ", status: "提出準備中" },
  { label: "第2志望", value: "データベースゼミ", status: "下書き保存済み" },
  { label: "第3志望", value: "知識工学ゼミ", status: "未入力" },
];

export default function StudentMyPage() {
  return (
    <main className="min-h-screen bg-[radial-gradient(circle_at_top,rgba(14,165,233,0.12),transparent_28%),linear-gradient(180deg,#f8fafc_0%,#eef2ff_100%)] text-slate-900">
      <section className="mx-auto flex min-h-screen w-full max-w-7xl flex-col px-6 py-6 md:px-10 lg:px-12">
        <header className="flex flex-col gap-4 rounded-[2rem] border border-white/70 bg-white/85 px-5 py-4 shadow-[0_12px_40px_rgba(15,23,42,0.08)] backdrop-blur md:flex-row md:items-center md:justify-between md:px-6">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.28em] text-slate-500">
              Student Dashboard
            </p>
            <h1 className="mt-1 text-lg font-semibold tracking-tight text-slate-950 md:text-xl">
              学生マイページ
            </h1>
          </div>
          <AuthMenuBar current="mypage" />
        </header>

        <div className="grid flex-1 gap-6 py-10 lg:grid-cols-[1.05fr_0.95fr] lg:py-14">
          <section className="space-y-6">
            <div className="rounded-[2rem] border border-white/80 bg-white/90 p-6 shadow-[0_18px_60px_rgba(15,23,42,0.08)] md:p-8">
              <div className="flex flex-col gap-5 md:flex-row md:items-start md:justify-between">
                <div>
                  <p className="text-sm font-semibold text-sky-700">ログイン中の学生</p>
                  <h2 className="mt-2 text-3xl font-semibold tracking-tight text-slate-950 md:text-4xl">
                    山田 太郎
                  </h2>
                  <p className="mt-3 max-w-2xl text-sm leading-7 text-slate-600 md:text-base">
                    研究テーマと興味分野をもとに、志望提出やゼミ探索へすぐ進める学生向けの起点画面。
                  </p>
                </div>
                <div className="rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-600">
                  <p className="font-medium text-slate-500">提出締切</p>
                  <p className="mt-1 text-lg font-semibold text-slate-950">7月18日 23:59</p>
                </div>
              </div>

              <div className="mt-6 grid gap-4 sm:grid-cols-3">
                <div className="rounded-3xl bg-slate-950 p-5 text-white">
                  <p className="text-sm text-slate-300">学籍番号</p>
                  <p className="mt-3 text-xl font-semibold">23CS0123</p>
                </div>
                <div className="rounded-3xl bg-slate-100 p-5">
                  <p className="text-sm text-slate-500">学年</p>
                  <p className="mt-3 text-xl font-semibold text-slate-950">B3</p>
                </div>
                <div className="rounded-3xl bg-slate-100 p-5">
                  <p className="text-sm text-slate-500">研究テーマ</p>
                  <p className="mt-3 text-lg font-semibold text-slate-950">推薦システムの比較研究</p>
                </div>
              </div>
            </div>

            <div className="grid gap-4 sm:grid-cols-3">
              {quickActions.map((action) => (
                <article
                  key={action.title}
                  className="rounded-[1.75rem] border border-white/75 bg-white/85 p-5 shadow-[0_10px_30px_rgba(15,23,42,0.06)] transition hover:-translate-y-0.5 hover:shadow-[0_16px_40px_rgba(15,23,42,0.08)]"
                >
                  <p className="text-sm font-semibold text-slate-950">{action.title}</p>
                  <p className="mt-2 text-sm leading-6 text-slate-600">{action.description}</p>
                </article>
              ))}
            </div>

            <div id="status" className="rounded-[2rem] border border-white/80 bg-white/90 p-6 shadow-[0_18px_60px_rgba(15,23,42,0.08)] md:p-8">
              <div className="flex flex-col gap-2 md:flex-row md:items-end md:justify-between">
                <div>
                  <p className="text-sm font-semibold text-sky-700">志望提出状況</p>
                  <h3 className="mt-1 text-2xl font-semibold text-slate-950">第1〜第3志望を確認する</h3>
                </div>
                <a className="text-sm font-semibold text-sky-700 transition hover:text-sky-900" href="#application">
                  志望入力へ進む
                </a>
              </div>

              <div className="mt-6 space-y-3">
                {currentApplication.map((item, index) => (
                  <div
                    key={item.label}
                    className="flex flex-col gap-3 rounded-3xl border border-slate-200 bg-slate-50 px-4 py-4 md:flex-row md:items-center md:justify-between"
                  >
                    <div>
                      <p className="text-sm font-medium text-slate-500">{item.label}</p>
                      <p className="mt-1 text-lg font-semibold text-slate-950">{item.value}</p>
                    </div>
                    <div className="flex items-center gap-3">
                      <span className="text-sm font-medium text-slate-500">{item.status}</span>
                      <span className="rounded-full bg-slate-900 px-3 py-1 text-xs font-semibold text-white">
                        {index === 0 ? "優先" : index === 1 ? "保存" : "未着手"}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </section>

          <aside className="space-y-6">
            <div className="rounded-[2rem] border border-slate-200 bg-white/90 p-6 shadow-[0_18px_60px_rgba(15,23,42,0.08)] md:p-8">
              <p className="text-sm font-semibold text-indigo-700">現在所属ゼミ</p>
              <h3 className="mt-2 text-2xl font-semibold tracking-tight text-slate-950">データベースゼミ</h3>
              <p className="mt-3 text-sm leading-7 text-slate-600">
                現在は3年次の所属ゼミとして、研究テーマ「推薦システムの比較研究」に関連するゼミを表示しています。
              </p>

              <div className="mt-6 grid gap-3 sm:grid-cols-2">
                <div className="rounded-2xl bg-slate-100 p-4">
                  <p className="text-sm text-slate-500">指導教員</p>
                  <p className="mt-2 text-base font-semibold text-slate-950">田中 先生</p>
                </div>
                <div className="rounded-2xl bg-slate-100 p-4">
                  <p className="text-sm text-slate-500">現在の状態</p>
                  <p className="mt-2 text-base font-semibold text-slate-950">配属済み</p>
                </div>
              </div>

              <div className="mt-4 rounded-2xl border border-sky-200 bg-sky-50 p-4 text-sm leading-7 text-sky-900">
                配属履歴やゼミ情報の詳細から、現在の所属ゼミの研究内容を確認できます。
              </div>
            </div>

            <div id="application" className="rounded-[2rem] border border-white/80 bg-slate-950 p-6 text-white shadow-[0_18px_60px_rgba(15,23,42,0.16)] md:p-8">
              <p className="text-sm font-semibold text-slate-300">次にやること</p>
              <h3 className="mt-2 text-2xl font-semibold">志望理由を仕上げる</h3>
              <p className="mt-3 text-sm leading-7 text-slate-300">
                現在のマッチ度、文字数、未入力項目を確認して、提出画面に進めるようにします。
              </p>

              <div className="mt-6 space-y-3">
                <div className="rounded-2xl bg-white/5 p-4">
                  <p className="text-sm text-slate-400">現在のマッチ度</p>
                  <p className="mt-1 text-2xl font-semibold text-white">82%</p>
                </div>
                <div className="rounded-2xl bg-white/5 p-4">
                  <p className="text-sm text-slate-400">不足している要素</p>
                  <ul className="mt-2 space-y-1 text-sm leading-6 text-slate-300">
                    <li>・研究テーマの具体性</li>
                    <li>・ゼミを選んだ理由</li>
                  </ul>
                </div>
              </div>

              <div className="mt-6 flex flex-col gap-3 sm:flex-row">
                <a
                  className="inline-flex items-center justify-center rounded-full bg-white px-5 py-3 text-sm font-semibold text-slate-950 transition hover:bg-slate-100"
                  href="#status"
                >
                  提出状況を確認する
                </a>
                <a
                  className="inline-flex items-center justify-center rounded-full border border-white/15 bg-white/5 px-5 py-3 text-sm font-semibold text-white transition hover:bg-white/10"
                  href="/haizoku"
                >
                  配属状況へ進む
                </a>
              </div>
            </div>
          </aside>
        </div>
      </section>
    </main>
  );
}