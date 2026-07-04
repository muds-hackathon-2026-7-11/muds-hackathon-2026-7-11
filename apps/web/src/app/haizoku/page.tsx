import { AuthMenuBar } from "../../components/auth-menu-bar";

const statusRows = [
  {
    label: "AIゼミ",
    value: "第1志望 10人 / 第2志望 8人 / 第3志望 5人",
    detail: "定員 8名、倍率 1.6",
  },
  {
    label: "データベースゼミ",
    value: "第1志望 7人 / 第2志望 6人 / 第3志望 4人",
    detail: "定員 6名、倍率 1.2",
  },
  {
    label: "知識工学ゼミ",
    value: "第1志望 5人 / 第2志望 4人 / 第3志望 3人",
    detail: "定員 5名、倍率 1.0",
  },
];

export default function AssignmentStatusPage() {
  return (
    <main className="min-h-screen bg-[radial-gradient(circle_at_top,rgba(14,165,233,0.12),transparent_28%),linear-gradient(180deg,#f8fafc_0%,#eef2ff_100%)] text-slate-900">
      <section className="mx-auto flex min-h-screen w-full max-w-7xl flex-col px-6 py-6 md:px-10 lg:px-12">
        <header className="flex flex-col gap-4 rounded-[2rem] border border-white/70 bg-white/85 px-5 py-4 shadow-[0_12px_40px_rgba(15,23,42,0.08)] backdrop-blur md:flex-row md:items-center md:justify-between md:px-6">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.28em] text-slate-500">
              Assignment Status
            </p>
            <h1 className="mt-1 text-lg font-semibold tracking-tight text-slate-950 md:text-xl">
              配属状況
            </h1>
          </div>
          <AuthMenuBar current="haizoku" />
        </header>

        <div className="grid flex-1 gap-6 py-10 lg:grid-cols-[1.05fr_0.95fr] lg:py-14">
          <section className="space-y-6">
            <div className="rounded-[2rem] border border-white/80 bg-white/90 p-6 shadow-[0_18px_60px_rgba(15,23,42,0.08)] md:p-8">
              <p className="text-sm font-semibold text-sky-700">学生の提出状況</p>
              <h2 className="mt-2 text-3xl font-semibold tracking-tight text-slate-950 md:text-4xl">
                志望提出の進み具合を確認する
              </h2>
              <p className="mt-3 max-w-2xl text-sm leading-7 text-slate-600 md:text-base">
                配属先の見込みと各ゼミの応募人数を確認しながら、提出内容の最終確認に使う画面です。
              </p>

              <div className="mt-6 grid gap-4 sm:grid-cols-3">
                <div className="rounded-3xl bg-slate-950 p-5 text-white">
                  <p className="text-sm text-slate-300">提出状態</p>
                  <p className="mt-3 text-xl font-semibold">提出済み</p>
                </div>
                <div className="rounded-3xl bg-slate-100 p-5">
                  <p className="text-sm text-slate-500">提出日時</p>
                  <p className="mt-3 text-xl font-semibold text-slate-950">7月2日 18:40</p>
                </div>
                <div className="rounded-3xl bg-slate-100 p-5">
                  <p className="text-sm text-slate-500">マッチ度</p>
                  <p className="mt-3 text-xl font-semibold text-slate-950">82%</p>
                </div>
              </div>
            </div>

            <div className="rounded-[2rem] border border-white/80 bg-white/90 p-6 shadow-[0_18px_60px_rgba(15,23,42,0.08)] md:p-8">
              <div className="flex items-end justify-between gap-4">
                <div>
                  <p className="text-sm font-semibold text-indigo-700">志望の内訳</p>
                  <h3 className="mt-1 text-2xl font-semibold text-slate-950">第1〜第3志望</h3>
                </div>
                <a className="text-sm font-semibold text-sky-700 transition hover:text-sky-900" href="/mypage">
                  マイページへ戻る
                </a>
              </div>

              <div className="mt-6 space-y-3">
                {statusRows.map((row) => (
                  <div
                    key={row.label}
                    className="rounded-3xl border border-slate-200 bg-slate-50 px-4 py-4"
                  >
                    <div className="flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
                      <div>
                        <p className="text-sm font-medium text-slate-500">{row.label}</p>
                        <p className="mt-1 text-lg font-semibold text-slate-950">{row.value}</p>
                      </div>
                      <p className="text-sm font-medium text-slate-600">{row.detail}</p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </section>

          <aside className="space-y-6">
            <div className="rounded-[2rem] border border-slate-200 bg-white/90 p-6 shadow-[0_18px_60px_rgba(15,23,42,0.08)] md:p-8">
              <p className="text-sm font-semibold text-sky-700">配属見込み</p>
              <h3 className="mt-2 text-2xl font-semibold tracking-tight text-slate-950">
                データベースゼミが第一候補
              </h3>
              <p className="mt-3 text-sm leading-7 text-slate-600">
                現在の提出状況では、第一志望のゼミを中心に配属が進む見込みです。
              </p>

              <div className="mt-6 grid gap-3 sm:grid-cols-2">
                <div className="rounded-2xl bg-slate-100 p-4">
                  <p className="text-sm text-slate-500">定員差</p>
                  <p className="mt-2 text-base font-semibold text-slate-950">残り 1 名</p>
                </div>
                <div className="rounded-2xl bg-slate-100 p-4">
                  <p className="text-sm text-slate-500">応募倍率</p>
                  <p className="mt-2 text-base font-semibold text-slate-950">1.2 倍</p>
                </div>
              </div>
            </div>

            <div className="rounded-[2rem] border border-slate-950 bg-slate-950 p-6 text-white shadow-[0_18px_60px_rgba(15,23,42,0.16)] md:p-8">
              <p className="text-sm font-semibold text-slate-300">次の操作</p>
              <h3 className="mt-2 text-2xl font-semibold">提出内容を見直す</h3>
              <p className="mt-3 text-sm leading-7 text-slate-300">
                志望理由を修正したい場合はマイページへ戻って編集できます。
              </p>

              <div className="mt-6 flex flex-col gap-3 sm:flex-row">
                <a
                  className="inline-flex items-center justify-center rounded-full bg-white px-5 py-3 text-sm font-semibold text-slate-950 transition hover:bg-slate-100"
                  href="/mypage"
                >
                  マイページへ戻る
                </a>
                <a
                  className="inline-flex items-center justify-center rounded-full border border-white/15 bg-white/5 px-5 py-3 text-sm font-semibold text-white transition hover:bg-white/10"
                  href="/"
                >
                  トップへ戻る
                </a>
              </div>
            </div>
          </aside>
        </div>
      </section>
    </main>
  );
}