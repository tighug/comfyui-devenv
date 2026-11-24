// workflows/ のワークフロー（UI 形式）を API 形式に変換して、ComfyUI の
// user/default/claude_export/ に書き出す。ComfyUI の画面を開いたブラウザの
// 開発者ツールのコンソールで実行する。そのあと scripts/pull_api_exports.py で取ってくる。
//
// 変換には画面が「実行」のときに使う app.graphToPrompt() を使うので、サブグラフや
// Anything Everywhere のような画面側の接続も、実行時と同じに展開される。
// 書き出すたびに画面のワークフローが切り替わる（保存はしないので、元のファイルは変わらない）。

const app = window.app
const api = window.comfyAPI.api.api
const names = await (await fetch("/api/userdata?dir=workflows&recurse=true", { cache: "no-store" })).json()
const report = []
for (const name of names.filter((n) => n.endsWith(".json") && !n.startsWith("."))) {
  try {
    const wf = await (await fetch("/api/userdata/" + encodeURIComponent("workflows/" + name), { cache: "no-store" })).json()
    await app.loadGraphData(wf, true, false, name)
    const { output } = await app.graphToPrompt()
    const res = await api.fetchApi(
      "/userdata/" + encodeURIComponent("claude_export/" + name) + "?overwrite=true",
      { method: "POST", body: JSON.stringify(output, null, 2) },
    )
    report.push({ name, nodes: Object.keys(output).length, status: res.status })
  } catch (e) {
    report.push({ name, error: String(e) })
  }
}
console.table(report)
