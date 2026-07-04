export default function Home() {
  return (
    <main className="min-h-screen bg-[radial-gradient(circle_at_top,rgba(15,23,42,0.1),transparent_35%),linear-gradient(180deg,#f8fafc_0%,#eef2ff_100%)] text-slate-900">
      <section className="mx-auto flex min-h-screen w-full max-w-7xl flex-col px-6 py-6 md:px-10 lg:px-12">
        <header className="flex flex-col gap-4 rounded-[2rem] border border-white/70 bg-white/85 px-5 py-4 shadow-[0_12px_40px_rgba(15,23,42,0.08)] backdrop-blur md:flex-row md:items-center md:justify-between md:px-6">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.28em] text-slate-500">
              Seminar Selection Platform
            </p>
            <h1 className="mt-1 text-lg font-semibold tracking-tight text-slate-950 md:text-xl">
              ゼミ選択・配属支援プラットフォーム
            </h1>
          </div>
          <nav className="flex flex-wrap gap-2 text-sm font-medium text-slate-600">
            <a className="rounded-full bg-slate-900 px-4 py-2 text-white transition hover:bg-slate-700" href="#overview">
              概要
            </a>
            <a className="rounded-full bg-slate-100 px-4 py-2 transition hover:bg-slate-200" href="#features">
              機能
            </a>
            <a className="rounded-full bg-slate-100 px-4 py-2 transition hover:bg-slate-200" href="#roles">
              対象ユーザー
            </a>
          </nav>
        </header>

        <div className="grid flex-1 items-center gap-10 py-10 lg:grid-cols-[1.15fr_0.85fr] lg:py-16">
          <div className="space-y-8">
            <div className="inline-flex items-center gap-2 rounded-full border border-sky-200 bg-sky-50 px-4 py-2 text-sm font-medium text-sky-800">
              <span className="h-2 w-2 rounded-full bg-sky-500" />
              学生・教員・運営をつなぐ最初の入口
            </div>

            <div className="space-y-5">
              <p className="text-sm font-semibold uppercase tracking-[0.3em] text-slate-500">
                First Screen
              </p>
              <h2 className="max-w-3xl text-4xl font-semibold leading-tight tracking-tight text-slate-950 md:text-6xl">
                自分に合うゼミを見つけて、
                <span className="bg-gradient-to-r from-sky-600 to-indigo-600 bg-clip-text text-transparent">
                  志望提出まで迷わず進める
                </span>
                最初の画面。
              </h2>
              <p id="overview" className="max-w-2xl text-base leading-8 text-slate-600 md:text-lg">
                ゼミ情報、FAQ、志望提出、教員向けの応募管理までを一つの画面群にまとめる前提で、まずはログイン後に迷わない起点ページを用意します。
              </p>
            </div>

            <div className="flex flex-col gap-3 sm:flex-row">
              <a
                className="inline-flex items-center justify-center rounded-full bg-slate-950 px-6 py-3 text-sm font-semibold text-white shadow-lg shadow-slate-950/15 transition hover:-translate-y-0.5 hover:bg-slate-800"
                href="/mypage"
              >
                学生マイページを見る
              </a>
              <a
                className="inline-flex items-center justify-center rounded-full border border-slate-300 bg-white px-6 py-3 text-sm font-semibold text-slate-900 transition hover:border-slate-400 hover:bg-slate-50"
                href="#features"
              >
                実装イメージを見る
              </a>
            </div>

            <div className="grid gap-4 sm:grid-cols-3">
              <article className="rounded-3xl border border-white/80 bg-white/90 p-5 shadow-[0_10px_30px_rgba(15,23,42,0.06)]">
                <p className="text-sm font-medium text-slate-500">学生</p>
                <p className="mt-3 text-2xl font-semibold text-slate-950">ゼミを探す</p>
                <p className="mt-2 text-sm leading-6 text-slate-600">一覧、詳細、FAQ、志望提出へ自然に遷移できる導線。</p>
              </article>
              <article className="rounded-3xl border border-white/80 bg-white/90 p-5 shadow-[0_10px_30px_rgba(15,23,42,0.06)]">
                <p className="text-sm font-medium text-slate-500">教員</p>
                <p className="mt-3 text-2xl font-semibold text-slate-950">応募を確認する</p>
                <p className="mt-2 text-sm leading-6 text-slate-600">応募者一覧、分析、CSV出力に進める入口。</p>
              </article>
              <article className="rounded-3xl border border-white/80 bg-white/90 p-5 shadow-[0_10px_30px_rgba(15,23,42,0.06)]">
                <p className="text-sm font-medium text-slate-500">運営</p>
                <p className="mt-3 text-2xl font-semibold text-slate-950">設定を管理する</p>
                <p className="mt-2 text-sm leading-6 text-slate-600">募集期間、ゼミ、教員、配属結果の管理導線。</p>
              </article>
            </div>
          </div>

          <aside className="relative">
            <div className="absolute inset-0 -z-10 rounded-[2rem] bg-gradient-to-br from-sky-200/60 via-white to-indigo-200/60 blur-2xl" />
            <div className="rounded-[2rem] border border-white/70 bg-slate-950 p-5 text-slate-100 shadow-[0_24px_80px_rgba(15,23,42,0.18)] md:p-6">
              <div className="flex items-center justify-between border-b border-white/10 pb-4">
                <div>
                  <p className="text-sm text-slate-400">Preview</p>
                  <p className="mt-1 text-xl font-semibold">ホームの役割</p>
                </div>
                <span className="rounded-full bg-white/10 px-3 py-1 text-xs font-medium text-slate-200">
                  MVP
                </span>
              </div>

              <div className="space-y-4 py-5">
                <div className="rounded-2xl border border-white/10 bg-white/5 p-4">
                  <p className="text-xs uppercase tracking-[0.2em] text-slate-400">What users see</p>
                  <p className="mt-2 text-base font-medium leading-7">
                    メニュー、導線、対象ユーザーを最初に見せて、迷わず次の画面へ進める。
                  </p>
                </div>
                <div id="features" className="grid gap-3 sm:grid-cols-2">
                  <div className="rounded-2xl bg-white/5 p-4">
                    <p className="text-sm font-semibold text-white">共通レイアウト</p>
                    <p className="mt-2 text-sm leading-6 text-slate-300">メニューバーとヘッダーを共通化。</p>
                  </div>
                  <div className="rounded-2xl bg-white/5 p-4">
                    <p className="text-sm font-semibold text-white">レスポンシブ</p>
                    <p className="mt-2 text-sm leading-6 text-slate-300">モバイルでも読みやすく崩れない。</p>
                  </div>
                  <div className="rounded-2xl bg-white/5 p-4">
                    <p className="text-sm font-semibold text-white">権限別導線</p>
                    <p className="mt-2 text-sm leading-6 text-slate-300">学生・教員・運営で表示を切り替える。</p>
                  </div>
                  <div className="rounded-2xl bg-white/5 p-4">
                    <p className="text-sm font-semibold text-white">拡張前提</p>
                    <p className="mt-2 text-sm leading-6 text-slate-300">後続画面を追加しやすい起点にする。</p>
                  </div>
                </div>
              </div>
            </div>
          </aside>
        </div>

        <section id="roles" className="grid gap-4 pb-6 md:grid-cols-3">
          <article className="rounded-[1.75rem] border border-white/70 bg-white/85 p-6 shadow-[0_10px_30px_rgba(15,23,42,0.06)]">
            <p className="text-sm font-semibold text-sky-700">学生向け</p>
            <h3 className="mt-3 text-xl font-semibold text-slate-950">ゼミ選択の起点</h3>
            <p className="mt-2 text-sm leading-7 text-slate-600">ゼミ一覧、詳細、FAQ、志望提出へつながる導線をまとめる。</p>
          </article>
          <article className="rounded-[1.75rem] border border-white/70 bg-white/85 p-6 shadow-[0_10px_30px_rgba(15,23,42,0.06)]">
            <p className="text-sm font-semibold text-indigo-700">教員向け</p>
            <h3 className="mt-3 text-xl font-semibold text-slate-950">応募確認の起点</h3>
            <p className="mt-2 text-sm leading-7 text-slate-600">応募者一覧、詳細、分析画面へすばやく進める。</p>
          </article>
          <article className="rounded-[1.75rem] border border-white/70 bg-white/85 p-6 shadow-[0_10px_30px_rgba(15,23,42,0.06)]">
            <p className="text-sm font-semibold text-violet-700">運営向け</p>
            <h3 className="mt-3 text-xl font-semibold text-slate-950">管理の起点</h3>
            <p className="mt-2 text-sm leading-7 text-slate-600">募集期間やゼミ設定、CSVインポートを扱う入口にする。</p>
          </article>
        </section>
      </section>
    </main>
  );
}
