"use strict";
// 案件管理 フロントエンド(ビルド不要の素の JavaScript)

const $ = (sel, root = document) => root.querySelector(sel);
const view = $("#view");
let META = null;

// ------------------------------------------------------------ 汎用

function h(v) {
  return String(v ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}
const WD = "日月火水木金土";
function jdate(iso) {
  if (!iso) return "";
  const d = new Date(iso.slice(0, 10) + "T00:00:00");
  return `${d.getFullYear()}/${d.getMonth() + 1}/${d.getDate()}(${WD[d.getDay()]})`;
}
function today() {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
}
function daysLeft(iso) {
  return Math.round((new Date(iso + "T00:00:00") - new Date(today() + "T00:00:00")) / 86400000);
}
function dueTag(iso) {
  const n = daysLeft(iso);
  if (n < 0) return `<span class="tag danger">${-n}日超過</span>`;
  if (n === 0) return `<span class="tag danger">本日</span>`;
  if (n <= 3) return `<span class="tag danger">あと${n}日</span>`;
  if (n <= 7) return `<span class="tag warning">あと${n}日</span>`;
  return `<span class="tag">あと${n}日</span>`;
}
function statusTag(s) {
  const cls = { 相談: "gray", 受任: "", 係属: "warning", 終結: "ok" }[s] ?? "";
  return `<span class="tag ${cls}">${h(s)}</span>`;
}
function toast(msg, error = false) {
  const t = $("#toast");
  t.textContent = msg;
  t.className = "toast" + (error ? " error" : "");
  clearTimeout(toast.timer);
  toast.timer = setTimeout(() => t.classList.add("hidden"), error ? 5000 : 2200);
}

// ------------------------------------------------------------ API

class ApiError extends Error {
  constructor(status, detail) {
    super(typeof detail === "string" ? detail : detail?.message || JSON.stringify(detail));
    this.status = status;
    this.detail = detail;
  }
}

async function api(method, path, body, retried = false) {
  const opt = { method, headers: { "x-cm": "1" }, credentials: "same-origin" };
  if (body !== undefined) {
    opt.headers["content-type"] = "application/json";
    opt.body = JSON.stringify(body);
  }
  const res = await fetch("/api" + path, opt);
  if (res.status === 401 && path !== "/auth/login" && path !== "/auth/reauth") {
    showLogin();
    throw new ApiError(401, "ログインが必要です");
  }
  let data = null;
  try { data = await res.json(); } catch { /* 空 */ }
  if (res.status === 403 && data?.detail?.code === "reauth_required" && !retried) {
    const ok = await reauthDialog();
    if (ok) return api(method, path, body, true);
    throw new ApiError(403, "再認証がキャンセルされました");
  }
  if (!res.ok) {
    let d = data?.detail ?? res.statusText;
    if (Array.isArray(d)) d = d.map((e) => `${(e.loc || []).slice(-1)[0]}: ${e.msg}`).join(" / ");
    throw new ApiError(res.status, d);
  }
  return data;
}

async function guard(fn) {
  try { return await fn(); } catch (e) {
    if (e.status !== 401) toast(e.message || String(e), true);
    return undefined;
  }
}

// ------------------------------------------------------------ モーダル・フォーム

function openModal(html) {
  $("#modal-body").innerHTML = html;
  $("#modal").classList.remove("hidden");
  const first = $("#modal-body input:not([type=hidden]), #modal-body textarea, #modal-body select");
  if (first && window.matchMedia("(min-width: 700px)").matches) first.focus();
}
function closeModal() {
  $("#modal").classList.add("hidden");
  $("#modal-body").innerHTML = "";
}
$("#modal").addEventListener("click", (e) => { if (e.target.id === "modal") closeModal(); });

function fieldHtml(f) {
  const v = f.value ?? "";
  const req = f.required ? "required" : "";
  const name = `name="${h(f.name)}"`;
  if (f.type === "checkbox") {
    return `<label class="check"><input type="checkbox" ${name} ${v ? "checked" : ""}> ${h(f.label)}</label>`;
  }
  let input;
  if (f.type === "select") {
    const opts = (f.options || []).map((o) => {
      const [val, lab] = Array.isArray(o) ? o : [o, o];
      return `<option value="${h(val)}" ${String(val) === String(v) ? "selected" : ""}>${h(lab)}</option>`;
    }).join("");
    input = `<select ${name} ${req}>${opts}</select>`;
  } else if (f.type === "textarea") {
    input = `<textarea ${name} ${req} placeholder="${h(f.placeholder || "")}">${h(v)}</textarea>`;
  } else {
    const extra = f.type === "number" ? `inputmode="numeric" min="${f.min ?? 0}"` : "";
    input = `<input type="${f.type || "text"}" ${name} value="${h(v)}" ${req} ${extra} placeholder="${h(f.placeholder || "")}" autocomplete="off">`;
  }
  const hint = f.hint ? `<div class="muted small">${h(f.hint)}</div>` : "";
  return `<label class="field"><span>${h(f.label)}${f.required ? " *" : ""}</span>${input}${hint}</label>`;
}

// fields の値をまとめて onSubmit(values) に渡す。成功時に閉じる
function formDialog({ title, fields, submitLabel = "保存", onSubmit, extraHtml = "", danger }) {
  openModal(`<h1>${h(title)}</h1><form id="dlg-form">${fields.map(fieldHtml).join("")}${extraHtml}
    <div class="actions">${danger ? `<button type="button" class="danger" id="dlg-danger">${h(danger.label)}</button><span class="grow"></span>` : ""}
    <button type="button" id="dlg-cancel">キャンセル</button><button class="primary" type="submit">${h(submitLabel)}</button></div></form>`);
  $("#dlg-cancel").onclick = closeModal;
  if (danger) $("#dlg-danger").onclick = async () => {
    if (!confirm(danger.confirm || "削除しますか?")) return;
    const r = await guard(danger.onClick);
    if (r !== undefined) { closeModal(); route(); }
  };
  $("#dlg-form").onsubmit = async (e) => {
    e.preventDefault();
    const fd = new FormData(e.target);
    const vals = {};
    for (const f of fields) {
      if (f.type === "checkbox") vals[f.name] = fd.get(f.name) === "on";
      else if (f.type === "number") vals[f.name] = fd.get(f.name) === "" ? null : Number(fd.get(f.name));
      else if (f.type === "date") vals[f.name] = fd.get(f.name) || null;
      else vals[f.name] = (fd.get(f.name) ?? "").toString();
    }
    const btn = e.target.querySelector("button[type=submit]");
    btn.disabled = true;
    const r = await guard(() => onSubmit(vals));
    btn.disabled = false;
    if (r !== undefined && r !== false) { closeModal(); route(); }
  };
}

function showLogin() {
  document.body.classList.add("logged-out");
  $("#tabbar").classList.add("hidden");
  view.innerHTML = `<div class="login card"><h1>案件管理</h1>
    <form id="login-form"><label class="field"><span>アクセストークン</span>
    <input type="password" name="token" autocomplete="current-password" required></label>
    <button class="primary" type="submit">ログイン</button></form>
    <p class="muted small">トークンは PC の .env に設定した値です。</p></div>`;
  $("#login-form").onsubmit = async (e) => {
    e.preventDefault();
    const token = new FormData(e.target).get("token");
    const r = await guard(() => api("POST", "/auth/login", { token }));
    if (r) { $("#tabbar").classList.remove("hidden"); await loadMeta(); route(); }
  };
}

function reauthDialog() {
  return new Promise((resolve) => {
    openModal(`<h1>再認証</h1><p>機微案件・重要操作のため、トークンを再入力してください。</p>
      <form id="re-form"><label class="field"><span>アクセストークン</span>
      <input type="password" name="token" required autocomplete="current-password"></label>
      <div class="actions"><button type="button" id="re-cancel">キャンセル</button><button class="primary">認証</button></div></form>`);
    $("#re-cancel").onclick = () => { closeModal(); resolve(false); };
    $("#re-form").onsubmit = async (e) => {
      e.preventDefault();
      const token = new FormData(e.target).get("token");
      try {
        await api("POST", "/auth/reauth", { token });
        closeModal();
        resolve(true);
      } catch (err) { toast(err.message, true); }
    };
  });
}

// ------------------------------------------------------------ ルーティング

const routes = [
  [/^#?\/?$/, viewDashboard, "home"],
  [/^#\/cases$/, viewCases, "cases"],
  [/^#\/cases\/new$/, viewCaseNew, "cases"],
  [/^#\/cases\/(\d+)(?:\/(\w+))?$/, viewCase, "cases"],
  [/^#\/deadlines$/, viewDeadlines, "deadlines"],
  [/^#\/calc$/, viewCalc, "deadlines"],
  [/^#\/todos$/, viewTodos, "more"],
  [/^#\/stale$/, viewStale, "more"],
  [/^#\/conflicts$/, viewConflicts, "more"],
  [/^#\/search$/, viewSearch, "search"],
  [/^#\/more$/, viewMore, "more"],
  [/^#\/settings$/, viewSettings, "more"],
  [/^#\/audit$/, viewAudit, "more"],
  [/^#\/profit$/, viewProfit, "more"],
  [/^#\/ailog$/, viewAILog, "more"],
];

let routeSeq = 0;

async function route() {
  const seq = ++routeSeq;   // 画面の描画が重なったときは古い方のエラーを無視する
  const hash = location.hash || "#/";
  const [path, qs] = hash.split("?");
  for (const [re, fn, nav] of routes) {
    const m = path.match(re);
    if (m) {
      document.querySelectorAll("[data-nav]").forEach((a) => a.classList.toggle("active", a.dataset.nav === nav));
      try {
        await fn(...m.slice(1), new URLSearchParams(qs || ""));
      } catch (e) {
        if (e.status === 401 || seq !== routeSeq) return;
        view.innerHTML = `<div class="alert danger">${h(e.message)}</div><p><a href="#/">ホームへ</a></p>`;
      }
      return;
    }
  }
  view.innerHTML = `<p>ページが見つかりません。<a href="#/">ホームへ</a></p>`;
}
window.addEventListener("hashchange", () => { closeModal(); route(); window.scrollTo(0, 0); });

async function loadMeta() {
  META = await api("GET", "/meta");
}

// ------------------------------------------------------------ ダッシュボード

async function viewDashboard() {
  const d = await api("GET", "/dashboard");
  updateBell(d.notifications);
  const backup = d.last_backup_at
    ? `最終バックアップ: ${h(d.last_backup_at.replace("T", " "))}`
    : `<span class="tag danger">バックアップ未実施</span>`;
  const alerts = d.notifications.filter((n) => n.level === "danger" || n.type === "unconfirmed")
    .map((n) => `<div class="alert ${n.level}">${n.case_id ? `<a href="#/cases/${n.case_id}/deadlines">${h(n.text)}</a>` : h(n.text)}</div>`).join("");
  view.innerHTML = `
    ${alerts}
    <div class="stats">
      <a class="stat" href="#/cases?status=係属"><b>${d.counts["係属"] || 0}</b><span>係属</span></a>
      <a class="stat" href="#/cases?status=受任"><b>${d.counts["受任"] || 0}</b><span>受任</span></a>
      <a class="stat" href="#/cases?status=相談"><b>${d.counts["相談"] || 0}</b><span>相談</span></a>
      <a class="stat" href="#/stale"><b>${d.stale.length}</b><span>放置</span></a>
    </div>
    <h2>直近の期限・期日(14日以内)<a class="btn small" href="#/deadlines">すべて</a></h2>
    ${deadlineList(d.upcoming, true) || `<p class="muted">直近の期限はありません。</p>`}
    <h2>未対応事項<a class="btn small" href="#/todos">すべて</a></h2>
    ${todoList(d.todos.slice(0, 10), true) || `<p class="muted">未対応の TODO はありません。</p>`}
    ${d.stale.length ? `<h2>放置アラート<a class="btn small" href="#/stale">すべて</a></h2>${staleList(d.stale.slice(0, 5))}` : ""}
    <h2>係属中・受任中の案件</h2>
    ${caseList(d.active_cases) || `<p class="muted">ありません。</p>`}
    <p class="muted small">${backup}${d.backup_configured ? "" : "(BACKUP_DIR 未設定)"}</p>
    <button class="fab" data-href="#/cases/new" aria-label="新規案件">+</button>`;
}

function deadlineList(items, showCase) {
  if (!items.length) return "";
  return `<ul class="list">${items.map((d) => `
    <li class="link" data-href="#/cases/${d.case_id}/deadlines">
      <div class="row between"><span class="title">${d.kind === "期日" ? "📅" : "⏰"} ${h(d.title)}</span>${d.done ? `<span class="tag ok">完了</span>` : dueTag(d.due_date)}</div>
      <div class="muted small">${jdate(d.due_date)} ${h(d.due_time || "")} ${h(d.place || "")}
        ${d.confirmed ? "" : `<span class="tag warning">未確定(計算値)</span>`}</div>
      ${showCase ? `<div class="small">${h(d.case_title)}</div>` : ""}
    </li>`).join("")}</ul>`;
}

function todoList(items, showCase) {
  if (!items.length) return "";
  return `<ul class="list">${items.map((t) => `
    <li class="link" data-href="#/cases/${t.case_id}/todos">
      <div class="row between"><span class="title">${h(t.title)}</span>
        ${t.status === "待ち" ? `<span class="tag warning">待ち ${t.waiting_days}日</span>` : `<span class="tag gray">${h(t.status)}</span>`}</div>
      ${t.waiting_for ? `<div class="small">⏳ ${h(t.waiting_for)}</div>` : ""}
      ${t.due_date ? `<div class="small">期限 ${jdate(t.due_date)} ${dueTag(t.due_date)}</div>` : ""}
      ${showCase ? `<div class="muted small">${h(t.case_title)}</div>` : ""}
    </li>`).join("")}</ul>`;
}

function staleList(items) {
  return `<ul class="list">${items.map((s) => `
    <li class="link" data-href="#/cases/${s.id}">
      <div class="row between"><span class="title">${h(s.title)}</span><span class="tag danger">${s.idle_days}日動きなし</span></div>
      <div class="muted small">${statusTag(s.status)} 最終: ${jdate(s.last_activity)}(基準 ${s.limit_days}日)</div>
      ${s.waiting ? `<div class="small">⏳ ${h(s.waiting)}</div>` : ""}
    </li>`).join("")}</ul>`;
}

function caseList(items) {
  if (!items.length) return "";
  return `<ul class="list">${items.map((c) => `
    <li class="link" data-href="#/cases/${c.id}">
      <div class="row between"><span class="title">${c.sensitive ? "🔒 " : ""}${h(c.title)}</span>${statusTag(c.status)}</div>
      <div class="muted small">${h(c.field || "")} ${h(c.court || "")} ${h(c.case_number || "")}
        ${c.clients ? ` / 依頼者: ${h(c.clients)}` : ""}</div>
      <div class="small">${c.next_due ? `次の期限 ${jdate(c.next_due)} ${dueTag(c.next_due)}` : ""}
        <span class="muted">最終動き ${jdate(c.last_activity)}</span></div>
    </li>`).join("")}</ul>`;
}

// ------------------------------------------------------------ 案件一覧・作成

async function viewCases(params) {
  const status = params.get("status") || "相談,受任,係属";
  const list = await api("GET", `/cases?status=${encodeURIComponent(status)}`);
  const chips = [["相談,受任,係属", "進行中"], ["相談", "相談"], ["受任", "受任"], ["係属", "係属"], ["終結", "終結"]];
  view.innerHTML = `<h1>案件</h1>
    <div class="chips">${chips.map(([v, l]) => `<button data-href="#/cases?status=${encodeURIComponent(v)}" class="${v === status ? "on" : ""}">${l}</button>`).join("")}</div>
    ${caseList(list) || `<p class="muted">該当する案件はありません。</p>`}
    <button class="fab" data-href="#/cases/new" aria-label="新規案件">+</button>`;
}

function caseFields(c = {}) {
  return [
    { name: "title", label: "事件名", required: true, value: c.title, placeholder: "例: 山田 対 株式会社〇〇 貸金返還請求" },
    { name: "field", label: "分野", type: "select", options: META.fields, value: c.field || "民事" },
    { name: "status", label: "状態", type: "select", options: META.statuses, value: c.status || "相談" },
    { name: "accepted_on", label: "受任日", type: "date", value: c.accepted_on },
    { name: "closed_on", label: "終結日", type: "date", value: c.closed_on },
    { name: "court", label: "裁判所・係属部", value: c.court },
    { name: "case_number", label: "事件番号", value: c.case_number, placeholder: "例: 令和8年(ワ)第123号" },
    { name: "fee_terms", label: "報酬条件", type: "textarea", value: c.fee_terms },
    { name: "memo", label: "メモ", type: "textarea", value: c.memo },
    { name: "folder_path", label: "案件フォルダ(PC上の絶対パス)", value: c.folder_path, placeholder: "C:\\Users\\...\\事件\\山田" },
    { name: "stale_days", label: "放置アラートまでの日数(空欄=既定値)", type: "number", value: c.stale_days, min: 1 },
    { name: "sensitive", label: "機微案件(閲覧時に再認証を求める)", type: "checkbox", value: c.sensitive },
  ];
}

async function viewCaseNew() {
  view.innerHTML = `<h1>新規案件</h1><div class="card"><p class="muted small">
    先に<a href="#/conflicts">利益相反チェック</a>を行ってください。作成後、当事者を登録すると自動で照合結果を確認できます。</p></div>
    <form id="new-case">${caseFields().map(fieldHtml).join("")}
    <label class="check"><input type="checkbox" name="with_checklist" checked> 分野別の受任時チェックリストを作成する</label>
    <div class="actions"><button class="primary" type="submit">作成</button></div></form>`;
  $("#new-case").onsubmit = async (e) => {
    e.preventDefault();
    const fd = new FormData(e.target);
    const body = Object.fromEntries(caseFields().map((f) => [f.name, fd.get(f.name)]));
    body.sensitive = fd.get("sensitive") === "on";
    body.with_checklist = fd.get("with_checklist") === "on";
    for (const k of ["accepted_on", "closed_on"]) body[k] = body[k] || null;
    body.stale_days = body.stale_days ? Number(body.stale_days) : null;
    const r = await guard(() => api("POST", "/cases", body));
    if (r) { toast("作成しました"); location.hash = `#/cases/${r.id}/parties`; }
  };
}

// ------------------------------------------------------------ 案件詳細

const CASE_TABS = [["", "概要"], ["parties", "当事者"], ["deadlines", "期限"], ["checklist", "チェック"],
  ["activities", "活動"], ["comms", "連絡"], ["todos", "TODO"], ["files", "資料"], ["recordings", "録音"],
  ["ai", "AI"], ["money", "会計"]];

async function viewCase(id, tab = "") {
  const c = await api("GET", `/cases/${id}`);
  const tabs = CASE_TABS.map(([k, l]) => {
    let n = "";
    if (k === "checklist") n = ` ${c.checklist.filter((x) => x.done).length}/${c.checklist.length}`;
    if (k === "todos") { const open = c.todos.filter((x) => x.status !== "完了").length; n = open ? ` ${open}` : ""; }
    if (k === "deadlines") { const open = c.deadlines.filter((x) => !x.done).length; n = open ? ` ${open}` : ""; }
    return `<a href="#/cases/${id}${k ? "/" + k : ""}" class="${k === (tab || "") ? "on" : ""}">${l}${n}</a>`;
  }).join("");
  const body = { "": caseOverview, parties: caseParties, deadlines: caseDeadlines, checklist: caseChecklist,
    activities: caseActivities, comms: caseComms, todos: caseTodos, files: caseFiles, recordings: caseRecordings,
    ai: caseAI, money: caseMoney }[tab || ""];
  view.innerHTML = `<div class="row between"><h1 class="grow">${c.sensitive ? "🔒 " : ""}${h(c.title)}</h1>${statusTag(c.status)}</div>
    <div class="muted small">${h(c.field)} ${h(c.court || "")} ${h(c.case_number || "")}</div>
    <nav class="tabs">${tabs}</nav><div id="case-body"></div>`;
  await body(c);
}

function caseOverview(c) {
  const openTodos = c.todos.filter((t) => t.status !== "完了");
  const nextDl = c.deadlines.filter((d) => !d.done).slice(0, 3);
  $("#case-body").innerHTML = `
    <div class="card"><dl class="kv">
      <dt>状態</dt><dd>${statusTag(c.status)}</dd>
      <dt>分野</dt><dd>${h(c.field)}</dd>
      <dt>受任日</dt><dd>${jdate(c.accepted_on) || "—"}</dd>
      <dt>終結日</dt><dd>${jdate(c.closed_on) || "—"}</dd>
      <dt>裁判所</dt><dd>${h(c.court) || "—"}</dd>
      <dt>事件番号</dt><dd>${h(c.case_number) || "—"}</dd>
      <dt>報酬条件</dt><dd class="pre">${h(c.fee_terms) || "—"}</dd>
      <dt>依頼者</dt><dd>${h(c.parties.filter((p) => p.role === "依頼者").map((p) => p.name).join("、")) || "—"}</dd>
      <dt>相手方</dt><dd>${h(c.parties.filter((p) => p.role === "相手方").map((p) => p.name).join("、")) || "—"}</dd>
      <dt>フォルダ</dt><dd class="small">${h(c.folder_path) || "—"}</dd>
      <dt>最終動き</dt><dd>${jdate(c.last_activity)}</dd>
    </dl></div>
    ${c.memo ? `<div class="card pre">${h(c.memo)}</div>` : ""}
    <div class="row"><button class="primary" id="edit-case">編集</button>
      <button id="quick-act">活動を記録</button><button id="del-case" class="danger">削除</button></div>
    ${nextDl.length ? `<h2>次の期限・期日</h2>${deadlineList(nextDl, false)}` : ""}
    ${openTodos.length ? `<h2>未完了の TODO</h2>${todoList(openTodos, false)}` : ""}
    ${c.activities.length ? `<h2>最近の活動</h2>${activityList(c.activities.slice(0, 5))}` : ""}`;
  $("#edit-case").onclick = () => formDialog({
    title: "案件の編集", fields: caseFields(c),
    onSubmit: (v) => {
      v.stale_days = v.stale_days || null;
      return api("PUT", `/cases/${c.id}`, v);
    },
  });
  $("#quick-act").onclick = () => activityDialog(c);
  $("#del-case").onclick = async () => {
    if (!confirm(`「${c.title}」を削除します。当事者・記録もすべて削除されます。よろしいですか?`)) return;
    if (!confirm("本当に削除しますか?(元に戻せません。通常は状態を「終結」にしてください)")) return;
    const r = await guard(() => api("DELETE", `/cases/${c.id}`));
    if (r) { toast("削除しました"); location.hash = "#/cases"; }
  };
}

// 当事者
function partyFields(p = {}) {
  return [
    { name: "role", label: "役割", type: "select", options: META.roles, value: p.role || "依頼者" },
    { name: "name", label: "氏名・名称", required: true, value: p.name },
    { name: "kana", label: "フリガナ", value: p.kana, hint: "利益相反チェックの精度が上がります" },
    { name: "phone", label: "電話", type: "tel", value: p.phone },
    { name: "email", label: "メール", type: "email", value: p.email },
    { name: "address", label: "住所", value: p.address },
    { name: "note", label: "備考", type: "textarea", value: p.note },
  ];
}

function caseParties(c) {
  $("#case-body").innerHTML = `
    <div class="row"><button class="primary" id="add-party">当事者を追加</button>
      <button id="cc-case">この案件の当事者で利益相反チェック</button></div>
    <ul class="list">${c.parties.map((p) => `
      <li class="link" data-party="${p.id}">
        <div class="row between"><span class="title">${h(p.name)} <span class="muted small">${h(p.kana || "")}</span></span><span class="tag">${h(p.role)}</span></div>
        <div class="small">${p.phone ? `📞 <a href="tel:${h(p.phone)}">${h(p.phone)}</a> ` : ""}${p.email ? `✉️ <a href="mailto:${h(p.email)}">${h(p.email)}</a>` : ""}</div>
        ${p.address ? `<div class="muted small">${h(p.address)}</div>` : ""}
        ${p.note ? `<div class="small pre">${h(p.note)}</div>` : ""}
        <div class="muted small">連絡履歴 ${c.communications.filter((m) => m.party_id === p.id).length}件</div>
      </li>`).join("")}</ul>
    <div id="cc-result"></div>`;
  $("#add-party").onclick = () => formDialog({
    title: "当事者の追加", fields: partyFields(),
    onSubmit: async (v) => {
      await api("POST", `/cases/${c.id}/parties`, v);
      const r = await api("POST", "/conflicts/check", { names: [{ name: v.name, kana: v.kana }], exclude_case_id: c.id });
      if (r.hit_count) setTimeout(() => toast(`⚠ 他案件に類似の当事者が ${r.hit_count} 件あります(当事者タブで確認)`, true), 300);
      return true;
    },
  });
  $("#cc-case").onclick = async () => {
    if (!c.parties.length) return toast("当事者が登録されていません", true);
    const r = await guard(() => api("POST", "/conflicts/check", {
      names: c.parties.map((p) => ({ name: p.name, kana: p.kana || "" })), exclude_case_id: c.id }));
    if (r) $("#cc-result").innerHTML = `<h2>照合結果</h2>${conflictResultHtml(r)}`;
  };
  $("#case-body").querySelectorAll("[data-party]").forEach((li) => li.addEventListener("click", (e) => {
    if (e.target.closest("a")) return;
    const p = c.parties.find((x) => x.id === Number(li.dataset.party));
    partyDialog(c, p);
  }));
}

function partyDialog(c, p) {
  const hist = c.communications.filter((m) => m.party_id === p.id);
  formDialog({
    title: "当事者の編集", fields: partyFields(p),
    extraHtml: `<h3>連絡履歴</h3>${hist.length ? commList(hist) : `<p class="muted small">ありません</p>`}`,
    onSubmit: (v) => api("PUT", `/parties/${p.id}`, v),
    danger: { label: "削除", onClick: () => api("DELETE", `/parties/${p.id}`) },
  });
}

// 期限
function caseDeadlines(c) {
  $("#case-body").innerHTML = `
    <div class="row"><button class="primary" id="add-dl">期限・期日を追加</button>
      <a class="btn" href="#/calc?case=${c.id}">自動計算して追加</a></div>
    <ul class="list">${c.deadlines.map((d) => `
      <li class="link" data-dl="${d.id}">
        <div class="row between"><span class="title ${d.done ? "done" : ""}">${d.kind === "期日" ? "📅" : "⏰"} ${h(d.title)}</span>
          ${d.done ? `<span class="tag ok">完了</span>` : dueTag(d.due_date)}</div>
        <div class="small">${jdate(d.due_date)} ${h(d.due_time || "")} ${h(d.place || "")}</div>
        ${d.confirmed ? (d.calc ? `<div class="muted small">計算値を ${h((d.confirmed_at || "").replace("T", " "))} に確定</div>` : "")
          : `<div><span class="tag warning">未確定(計算値)</span> <button class="small primary" data-confirm="${d.id}">根拠を確認して確定</button></div>`}
        ${d.note ? `<div class="muted small pre">${h(d.note)}</div>` : ""}
      </li>`).join("")}</ul>`;
  $("#add-dl").onclick = () => deadlineDialog(c);
  $("#case-body").querySelectorAll("[data-dl]").forEach((li) => li.addEventListener("click", (e) => {
    const d = c.deadlines.find((x) => x.id === Number(li.dataset.dl));
    if (e.target.dataset.confirm) return confirmDialog(d);
    deadlineDialog(c, d);
  }));
}

function calcHtml(calc) {
  if (!calc) return "";
  return `<div class="card"><div class="due">${h(calc.due_label)}</div>
    <h3>計算過程</h3><ol class="steps">${calc.steps.map((s) => `<li>${h(s)}</li>`).join("")}</ol>
    <h3>根拠</h3><ul class="steps">${calc.basis.map((s) => `<li>${h(s)}</li>`).join("")}</ul>
    ${calc.warnings.length ? `<h3>注意</h3>${calc.warnings.map((w) => `<div class="alert warning small">${h(w)}</div>`).join("")}` : ""}
    </div>`;
}

function confirmDialog(d) {
  openModal(`<h1>期限の確定</h1><p class="title">${h(d.title)}</p>${calcHtml(d.calc)}
    <div class="alert info small">起算点となる事実(送達日・告知日等)と計算過程を記録・原本で確認したうえで確定してください。</div>
    <div class="actions"><button id="cf-cancel">キャンセル</button><button class="primary" id="cf-ok">確認した・確定する</button></div>`);
  $("#cf-cancel").onclick = closeModal;
  $("#cf-ok").onclick = async () => {
    const r = await guard(() => api("POST", `/deadlines/${d.id}/confirm`));
    if (r) { closeModal(); toast("確定しました"); route(); }
  };
}

function deadlineDialog(c, d) {
  const fields = [
    { name: "kind", label: "種別", type: "select", options: ["期限", "期日"], value: d?.kind || "期限" },
    { name: "title", label: "内容", required: true, value: d?.title, placeholder: "例: 第1回口頭弁論期日 / 準備書面提出" },
    { name: "due_date", label: "日付", type: "date", required: true, value: d?.due_date },
    { name: "due_time", label: "時刻", type: "time", value: d?.due_time },
    { name: "place", label: "場所(法廷・Web等)", value: d?.place },
    { name: "note", label: "備考", type: "textarea", value: d?.note },
  ];
  if (d) fields.push({ name: "done", label: "完了", type: "checkbox", value: d.done });
  formDialog({
    title: d ? "期限・期日の編集" : "期限・期日の追加", fields,
    extraHtml: d?.calc ? `<h3>自動計算の記録</h3>${calcHtml(d.calc)}` : "",
    onSubmit: (v) => d ? api("PUT", `/deadlines/${d.id}`, v) : api("POST", `/cases/${c.id}/deadlines`, v),
    danger: d ? { label: "削除", onClick: () => api("DELETE", `/deadlines/${d.id}`) } : null,
  });
}

// チェックリスト
function caseChecklist(c) {
  $("#case-body").innerHTML = `
    <ul class="list">${c.checklist.map((i) => `
      <li><label class="check"><input type="checkbox" data-check="${i.id}" ${i.done ? "checked" : ""}>
        <span class="grow ${i.done ? "done" : ""}">${h(i.label)}</span>
        ${i.done_at ? `<span class="muted small">${jdate(i.done_at)}</span>` : ""}
        <button class="small" data-del-check="${i.id}" aria-label="削除">×</button></label></li>`).join("")}</ul>
    <div class="row"><input id="new-check" class="grow" placeholder="項目を追加"><button id="add-check">追加</button>
      <button id="apply-tpl">ひな形を再適用</button></div>`;
  $("#case-body").querySelectorAll("[data-check]").forEach((cb) => cb.addEventListener("change", async () => {
    await guard(() => api("PUT", `/checklist/${cb.dataset.check}`, { done: cb.checked }));
    route();
  }));
  $("#case-body").querySelectorAll("[data-del-check]").forEach((b) => b.addEventListener("click", async (e) => {
    e.preventDefault();
    if (!confirm("この項目を削除しますか?")) return;
    await guard(() => api("DELETE", `/checklist/${b.dataset.delCheck}`));
    route();
  }));
  $("#add-check").onclick = async () => {
    const label = $("#new-check").value.trim();
    if (!label) return;
    await guard(() => api("POST", `/cases/${c.id}/checklist`, { label }));
    route();
  };
  $("#apply-tpl").onclick = async () => {
    const r = await guard(() => api("POST", `/cases/${c.id}/checklist/apply-template`));
    if (r) { toast(`${r.added}件追加しました`); route(); }
  };
}

// 活動記録
function activityList(items) {
  return `<ul class="list timeline">${items.map((a) => `
    <li class="link" data-act="${a.id}"><div class="row between"><span><b>${jdate(a.date)}</b> <span class="tag">${h(a.kind)}</span></span>
      ${a.minutes ? `<span class="muted small">${a.minutes}分</span>` : ""}</div>
      <div class="pre">${h(a.content)}</div></li>`).join("")}</ul>`;
}

function activityDialog(c, a) {
  formDialog({
    title: a ? "活動記録の編集" : "活動の記録",
    fields: [
      { name: "date", label: "日付", type: "date", required: true, value: a?.date || today() },
      { name: "kind", label: "種類", type: "select", options: META.activity_kinds, value: a?.kind || "面談" },
      { name: "content", label: "内容", type: "textarea", required: true, value: a?.content },
      { name: "minutes", label: "所要時間(分)", type: "number", value: a?.minutes },
    ],
    onSubmit: (v) => a ? api("PUT", `/activities/${a.id}`, v) : api("POST", `/cases/${c.id}/activities`, v),
    danger: a ? { label: "削除", onClick: () => api("DELETE", `/activities/${a.id}`) } : null,
  });
}

function caseActivities(c) {
  $("#case-body").innerHTML = `<div class="row"><button class="primary" id="add-act">活動を記録</button></div>
    ${activityList(c.activities) || ""}${c.activities.length ? "" : `<p class="muted">記録はありません。</p>`}`;
  $("#add-act").onclick = () => activityDialog(c);
  $("#case-body").querySelectorAll("[data-act]").forEach((li) => li.addEventListener("click", () =>
    activityDialog(c, c.activities.find((x) => x.id === Number(li.dataset.act)))));
}

// 連絡履歴
function commList(items) {
  return `<ul class="list">${items.map((m) => `
    <li class="link" data-comm="${m.id}"><div class="row between"><span><b>${jdate(m.date)}</b> <span class="tag">${h(m.channel)}</span>
      <span class="tag gray">${h(m.direction)}</span></span><span class="small">${h(m.party_name || "")}</span></div>
      <div class="pre">${h(m.summary)}</div></li>`).join("")}</ul>`;
}

function commDialog(c, m) {
  formDialog({
    title: m ? "連絡履歴の編集" : "連絡の記録",
    fields: [
      { name: "party_id", label: "相手", type: "select",
        options: [["", "(未指定)"], ...c.parties.map((p) => [p.id, `${p.name}(${p.role})`])], value: m?.party_id ?? "" },
      { name: "date", label: "日付", type: "date", required: true, value: m?.date || today() },
      { name: "channel", label: "手段", type: "select", options: META.channels, value: m?.channel || "電話" },
      { name: "direction", label: "発信/受信", type: "select", options: ["発信", "受信"], value: m?.direction || "発信" },
      { name: "summary", label: "要旨", type: "textarea", required: true, value: m?.summary },
    ],
    onSubmit: (v) => {
      v.party_id = v.party_id ? Number(v.party_id) : null;
      return m ? api("PUT", `/communications/${m.id}`, v) : api("POST", `/cases/${c.id}/communications`, v);
    },
    danger: m ? { label: "削除", onClick: () => api("DELETE", `/communications/${m.id}`) } : null,
  });
}

function caseComms(c) {
  const pid = new URLSearchParams(location.hash.split("?")[1] || "").get("party");
  const items = pid ? c.communications.filter((m) => String(m.party_id) === pid) : c.communications;
  $("#case-body").innerHTML = `<div class="row"><button class="primary" id="add-comm">連絡を記録</button></div>
    <div class="chips"><button data-href="#/cases/${c.id}/comms" class="${pid ? "" : "on"}">すべて</button>
      ${c.parties.map((p) => `<button data-href="#/cases/${c.id}/comms?party=${p.id}" class="${String(p.id) === pid ? "on" : ""}">${h(p.name)}</button>`).join("")}</div>
    ${items.length ? commList(items) : `<p class="muted">記録はありません。</p>`}`;
  $("#add-comm").onclick = () => commDialog(c);
  $("#case-body").querySelectorAll("[data-comm]").forEach((li) => li.addEventListener("click", () =>
    commDialog(c, c.communications.find((x) => x.id === Number(li.dataset.comm)))));
}

// TODO
function todoDialog(c, t) {
  formDialog({
    title: t ? "TODO の編集" : "TODO の追加",
    fields: [
      { name: "title", label: "内容", required: true, value: t?.title },
      { name: "status", label: "状態", type: "select", options: ["未着手", "待ち", "完了"], value: t?.status || "未着手" },
      { name: "waiting_for", label: "待ちの内容", value: t?.waiting_for, placeholder: "例: 相手方回答待ち / 依頼者からの資料待ち" },
      { name: "due_date", label: "期限", type: "date", value: t?.due_date },
    ],
    onSubmit: (v) => t ? api("PUT", `/todos/${t.id}`, v) : api("POST", `/cases/${c.id}/todos`, v),
    danger: t ? { label: "削除", onClick: () => api("DELETE", `/todos/${t.id}`) } : null,
  });
}

function caseTodos(c) {
  $("#case-body").innerHTML = `<div class="row"><button class="primary" id="add-todo">TODO を追加</button></div>
    <ul class="list">${c.todos.map((t) => `
      <li class="link" data-todo="${t.id}"><div class="row between"><span class="title ${t.status === "完了" ? "done" : ""}">${h(t.title)}</span>
        <span class="tag ${t.status === "待ち" ? "warning" : t.status === "完了" ? "ok" : "gray"}">${h(t.status)}</span></div>
        ${t.waiting_for ? `<div class="small">⏳ ${h(t.waiting_for)}</div>` : ""}
        ${t.due_date ? `<div class="small">期限 ${jdate(t.due_date)} ${t.status !== "完了" ? dueTag(t.due_date) : ""}</div>` : ""}
      </li>`).join("")}</ul>`;
  $("#add-todo").onclick = () => todoDialog(c);
  $("#case-body").querySelectorAll("[data-todo]").forEach((li) => li.addEventListener("click", () =>
    todoDialog(c, c.todos.find((x) => x.id === Number(li.dataset.todo)))));
}

// 資料
function fmtSize(n) {
  if (n < 1024) return `${n}B`;
  if (n < 1048576) return `${(n / 1024).toFixed(0)}KB`;
  return `${(n / 1048576).toFixed(1)}MB`;
}

async function caseFiles(c) {
  const box = $("#case-body");
  if (!c.folder_path) {
    box.innerHTML = `<p class="muted">案件フォルダが紐付けられていません。「概要 → 編集」でフォルダのパスを設定してください。</p>`;
    return;
  }
  box.innerHTML = `<p class="muted">読み込み中…</p>`;
  let r;
  try { r = await api("GET", `/cases/${c.id}/files`); } catch (e) {
    box.innerHTML = `<div class="alert warning">${h(e.message)}</div>`;
    return;
  }
  const idx = await api("GET", `/cases/${c.id}/index`);
  const nOk = idx.files.filter((f) => f.status === "ok").length;
  const problems = idx.files.filter((f) => f.status !== "ok");
  box.innerHTML = `<div class="card"><div class="row between"><b>本文検索(この案件のみ)</b>
      <button class="small" id="run-index">${idx.files.length ? "索引を更新" : "本文を索引化"}</button></div>
    <div class="muted small">索引済み ${nOk}件${idx.last_job ? ` ・ 最終 ${h((idx.last_job.updated_at || "").replace("T", " "))} ${h(idx.last_job.status)} ${h(idx.last_job.progress || "")}` : ""}</div>
    ${problems.length ? `<details class="small"><summary>本文を取り出せなかったファイル ${problems.length}件</summary>
      ${problems.map((f) => `<div>${h(f.rel_path)}: ${h(f.message || f.status)}</div>`).join("")}</details>` : ""}
    <form id="doc-q" class="row"><input name="q" class="grow" placeholder="PDF・Word・メール・録音の本文を検索" enterkeyhint="search"><button>検索</button></form>
    <div id="doc-hits"></div></div>
    <div class="muted small">${h(r.folder)}(${r.files.length}件${r.truncated ? "・上限で打切り" : ""})</div>
    <input id="file-filter" placeholder="ファイル名・メモで絞り込み">
    <ul class="list" id="file-list">${r.files.map((f, i) => `
      <li data-i="${i}" data-text="${h((f.path + " " + f.note).toLowerCase())}">
        <div class="row between"><a class="grow" target="_blank" rel="noopener"
          href="/api/cases/${c.id}/files/open?path=${encodeURIComponent(f.path)}">📄 ${h(f.path)}</a>
          <button class="small" data-note="${i}">メモ</button></div>
        <div class="muted small">${fmtSize(f.size)} ・ ${h(f.mtime.replace("T", " "))}</div>
        ${f.note ? `<div class="small pre">📝 ${h(f.note)}</div>` : ""}
      </li>`).join("")}</ul>`;
  $("#run-index").onclick = async () => {
    const r2 = await guard(() => api("POST", `/cases/${c.id}/index`));
    if (!r2) return;
    toast("索引化を開始しました");
    const j = await waitJob(r2.job_id, (p) => { $("#run-index").textContent = p || "処理中…"; });
    if (j) toast(j.status === "完了" ? j.progress : `失敗: ${j.error}`, j.status !== "完了");
    route();
  };
  $("#doc-q").onsubmit = async (e) => {
    e.preventDefault();
    const q = e.target.q.value.trim();
    if (!q) return;
    const hits = await guard(() => api("GET", `/cases/${c.id}/docsearch?q=${encodeURIComponent(q)}`));
    if (!hits) return;
    $("#doc-hits").innerHTML = hits.length ? `<ul class="list">${hits.map((x) => `<li>
      <a ${sourceLink(c.id, x.source_type === "audio" ? { type: "audio", transcript_id: x.transcript_id, t_start: x.t_start }
        : { type: "file", rel_path: x.rel_path, page: x.page })}>${x.source_type === "audio" ? "🎙" : "📄"} ${h(x.rel_path)} ${h(x.loc)}</a>
      <div class="small">${h(x.snippet)}</div></li>`).join("")}</ul>` : `<p class="muted small">該当なし</p>`;
  };
  $("#file-filter").oninput = (e) => {
    const q = e.target.value.toLowerCase();
    box.querySelectorAll("#file-list > li").forEach((li) => li.classList.toggle("hidden", q && !li.dataset.text.includes(q)));
  };
  box.querySelectorAll("[data-note]").forEach((b) => b.addEventListener("click", () => {
    const f = r.files[Number(b.dataset.note)];
    formDialog({
      title: "資料メモ", fields: [{ name: "note", label: f.path, type: "textarea", value: f.note }],
      onSubmit: (v) => api("PUT", `/cases/${c.id}/files/note`, { path: f.path, note: v.note }),
    });
  }));
}

// ------------------------------------------------------------ 期限一覧・計算

async function viewDeadlines(params) {
  const days = Number(params.get("days") || 60);
  const items = await api("GET", `/deadlines?days=${days}`);
  const unconfirmed = items.filter((d) => !d.confirmed);
  view.innerHTML = `<h1>期限・期日</h1>
    <div class="row"><a class="btn primary" href="#/calc">期限を自動計算</a></div>
    <div class="chips">${[[30, "30日"], [60, "60日"], [180, "180日"], [3650, "すべて"]].map(([v, l]) =>
      `<button data-href="#/deadlines?days=${v}" class="${v === days ? "on" : ""}">${l}</button>`).join("")}</div>
    ${unconfirmed.length ? `<div class="alert warning">未確定の計算期限が ${unconfirmed.length} 件あります。各案件で根拠を確認して確定してください。</div>` : ""}
    ${deadlineList(items, true) || `<p class="muted">期限はありません。</p>`}`;
}

async function viewCalc(params) {
  const caseId = params.get("case");
  const byField = {};
  for (const p of META.presets) (byField[p.field] ||= []).push(p);
  const presetOpts = Object.entries(byField).map(([f, ps]) =>
    `<optgroup label="${h(f)}">${ps.map((p) => `<option value="${h(p.code)}">${h(p.name)}(${p.amount}${META.units[p.unit]})</option>`).join("")}</optgroup>`).join("");
  const cases = await api("GET", "/cases?status=相談,受任,係属");
  view.innerHTML = `<h1>期限の自動計算</h1>
    <div class="alert info small">計算結果は初稿です。起算日・休日の扱いを確認のうえ、登録後に「確定」してください。</div>
    <form id="calc-form">
      <label class="field"><span>期間の種類</span><select name="preset"><option value="">任意の期間を指定</option>${presetOpts}</select></label>
      <div id="preset-info" class="muted small"></div>
      <label class="field"><span id="event-label">起算点となる事実の日(送達日・告知日など)</span><input type="date" name="event_date" required value="${today()}"></label>
      <div id="custom-box">
        <div class="row"><input type="number" name="amount" min="1" value="14" class="grow">
          <select name="unit" class="grow">${Object.entries(META.units).map(([k, v]) => `<option value="${k}">${v}</option>`).join("")}</select></div>
        <label class="field"><span>計算ルール</span><select name="ruleset">${Object.entries(META.rulesets).map(([k, v]) => `<option value="${k}">${h(v.name)}</option>`).join("")}</select></label>
        <label class="check"><input type="checkbox" name="include_first_day"> 初日を算入する(午前零時開始・時効期間の初日等)</label>
        <label class="check"><input type="checkbox" name="extend_on_holiday" checked> 末日が休日なら延長する</label>
      </div>
      <button class="primary" type="submit">計算</button>
    </form>
    <div id="calc-result"></div>`;
  const form = $("#calc-form");
  const sync = () => {
    const p = META.presets.find((x) => x.code === form.preset.value);
    $("#custom-box").classList.toggle("hidden", !!p);
    $("#preset-info").innerHTML = p ? `根拠: ${h(p.basis)} / 起算点: ${h(p.start_event)}${p.note ? `<br>${h(p.note)}` : ""}` : "";
    $("#event-label").textContent = p ? `起算点: ${p.start_event}` : "起算点となる事実の日(送達日・告知日など)";
  };
  form.preset.onchange = sync;
  form.onsubmit = async (e) => {
    e.preventDefault();
    const body = { event_date: form.event_date.value };
    if (form.preset.value) body.preset = form.preset.value;
    else Object.assign(body, { amount: Number(form.amount.value), unit: form.unit.value, ruleset: form.ruleset.value,
      include_first_day: form.include_first_day.checked, extend_on_holiday: form.extend_on_holiday.checked });
    const r = await guard(() => api("POST", "/deadline-calc", body));
    if (!r) return;
    $("#calc-result").innerHTML = `<h2>計算結果(未確定)</h2>${calcHtml(r)}
      <h3>案件に登録</h3>
      <div class="row"><select id="reg-case" class="grow">${cases.map((c) =>
        `<option value="${c.id}" ${String(c.id) === caseId ? "selected" : ""}>${h(c.title)}</option>`).join("")}</select></div>
      <label class="field"><span>表示名</span><input id="reg-title" value="${h(r.title)}"></label>
      <button class="primary" id="reg-btn">未確定として登録</button>`;
    $("#reg-btn").onclick = async () => {
      const cid = $("#reg-case").value;
      if (!cid) return toast("案件を選択してください", true);
      const calc = { ...r, input: body };
      const ok = await guard(() => api("POST", `/cases/${cid}/deadlines`, {
        kind: "期限", title: $("#reg-title").value || r.title, due_date: r.due, calc,
        note: `起算点の日: ${r.start_event_date}` }));
      if (ok) { toast("登録しました(未確定)"); location.hash = `#/cases/${cid}/deadlines`; }
    };
  };
}

// ------------------------------------------------------------ TODO・放置

async function viewTodos(params) {
  const st = params.get("status") || "未着手,待ち";
  const items = await api("GET", `/todos?status=${encodeURIComponent(st)}`);
  view.innerHTML = `<h1>TODO・待ち状態</h1>
    <div class="chips">${[["未着手,待ち", "未完了"], ["待ち", "待ちのみ"], ["未着手", "未着手"], ["完了", "完了"]].map(([v, l]) =>
      `<button data-href="#/todos?status=${encodeURIComponent(v)}" class="${v === st ? "on" : ""}">${l}</button>`).join("")}</div>
    ${todoList(items, true) || `<p class="muted">ありません。</p>`}`;
}

async function viewStale() {
  const items = await api("GET", "/stale");
  view.innerHTML = `<h1>放置案件</h1><p class="muted small">終結以外で、活動・連絡・更新が一定期間ない案件です(基準日数は設定・案件ごとに変更可)。</p>
    ${items.length ? staleList(items) : `<p class="muted">放置案件はありません。</p>`}`;
}

// ------------------------------------------------------------ 利益相反

function conflictResultHtml(r) {
  return r.results.map((x) => `<div class="card"><div class="title">${h(x.name)} <span class="muted small">${h(x.kana || "")}</span></div>
    ${x.hits.length ? `<ul class="list">${x.hits.map((hh) => `<li class="link" data-href="#/cases/${hh.case_id}/parties">
      <div class="row between"><span>${h(hh.party_name)} <span class="muted small">${h(hh.party_kana || "")}</span></span>
        <span class="tag ${hh.level === "一致" ? "danger" : "warning"}">${hh.level} ${Math.round(hh.score * 100)}%</span></div>
      <div class="small">${hh.adverse ? `<span class="tag danger">${h(hh.role)}</span>` : `<span class="tag">${h(hh.role)}</span>`}
        ${h(hh.case_title)} ${statusTag(hh.case_status)}</div>
      <div class="muted small">${h(hh.reason)}</div></li>`).join("")}</ul>`
      : `<div class="tag ok">該当なし</div>`}</div>`).join("") + `<p class="muted small">${h(r.note)}</p>`;
}

async function viewConflicts() {
  const hist = await api("GET", "/conflicts/history?limit=20");
  view.innerHTML = `<h1>利益相反チェック</h1>
    <p class="muted small">新規相談の相談者・相手方・関係者の氏名を入力してください。1行に1名。「氏名,フリガナ」の形式でも可。旧姓・旧商号は括弧書きで(例: 山田花子(旧姓佐藤))。</p>
    <form id="cc-form"><textarea name="names" required placeholder="山田 太郎,ヤマダタロウ&#10;株式会社〇〇商事"></textarea>
    <button class="primary" type="submit">照合する</button></form>
    <div id="cc-out"></div>
    <h2>実施履歴</h2>
    <ul class="list">${hist.map((x) => `<li><div class="row between"><span class="small">${h(x.checked_at.replace("T", " "))}</span>
      <span class="tag ${x.hit_count ? "warning" : "ok"}">該当 ${x.hit_count}件</span></div>
      <div>${h(x.names)}</div>${x.conclusion ? `<div class="small">判断: ${h(x.conclusion)}</div>` : ""}</li>`).join("")}</ul>`;
  $("#cc-form").onsubmit = async (e) => {
    e.preventDefault();
    const names = e.target.names.value.split(/\n/).map((l) => l.trim()).filter(Boolean).map((l) => {
      const [name, kana = ""] = l.split(/[,,\t]/);
      return { name: name.trim(), kana: kana.trim() };
    });
    const r = await guard(() => api("POST", "/conflicts/check", { names }));
    if (!r) return;
    $("#cc-out").innerHTML = `<h2>結果(該当 ${r.hit_count}件)</h2>${conflictResultHtml(r)}
      <label class="field"><span>判断の記録</span><input id="cc-concl" placeholder="例: 該当なし・受任可 / 別人と確認済み"></label>
      <button id="cc-save">判断を記録</button>`;
    $("#cc-save").onclick = async () => {
      const ok = await guard(() => api("PUT", `/conflicts/${r.id}`, { conclusion: $("#cc-concl").value }));
      if (ok) { toast("記録しました"); route(); }
    };
  };
}

// ------------------------------------------------------------ 検索

async function viewSearch(params) {
  const q = params.get("q") || "";
  view.innerHTML = `<h1>横断検索</h1>
    <form id="s-form" class="row"><input name="q" class="grow" value="${h(q)}" placeholder="氏名・事件名・記録の語句" enterkeyhint="search">
    <button class="primary">検索</button></form><div id="s-out"></div>`;
  $("#s-form").onsubmit = (e) => {
    e.preventDefault();
    location.hash = `#/search?q=${encodeURIComponent(e.target.q.value.trim())}`;
  };
  if (!q) return;
  const r = await api("GET", `/search?q=${encodeURIComponent(q)}`);
  const tabFor = { 案件: "", 当事者: "/parties", 活動記録: "/activities", 連絡履歴: "/comms", TODO: "/todos", 期限: "/deadlines", 資料メモ: "/files" };
  $("#s-out").innerHTML = r.results.length ? `<ul class="list">${r.results.map((x) => `
    <li class="link" data-href="#/cases/${x.case_id}${tabFor[x.kind] || ""}">
      <div class="row between"><span class="tag">${h(x.kind)}</span><span class="muted small">${jdate(x.date)}</span></div>
      <div class="title">${h(x.case_title)}</div>
      ${x.masked ? `<div class="muted small">(機微案件のため内容は再認証後に表示)</div>` : `<div class="small">${h(x.snippet)}</div>`}
    </li>`).join("")}</ul>` : `<p class="muted">該当はありません。</p>`;
}

// ------------------------------------------------------------ その他・設定

function viewMore() {
  view.innerHTML = `<h1>その他</h1><ul class="list">
    <li class="link" data-href="#/conflicts">⚖️ 利益相反チェック</li>
    <li class="link" data-href="#/todos">✅ TODO・待ち状態</li>
    <li class="link" data-href="#/stale">💤 放置案件</li>
    <li class="link" data-href="#/calc">🧮 期限の自動計算</li>
    <li class="link" data-href="#/cases?status=終結">📦 終結案件</li>
    <li class="link" data-href="#/settings">⚙️ 設定・休日・バックアップ</li>
    <li class="link" data-href="#/profit">💴 稼働・採算</li>
    <li class="link" data-href="#/ailog">🤖 AI送信ログ</li>
    <li class="link" data-href="#/audit">📜 操作ログ・監査ログ</li>
    <li class="link" id="logout">🚪 ログアウト</li></ul>`;
  $("#logout").onclick = async () => {
    await guard(() => api("POST", "/auth/logout"));
    showLogin();
  };
}

async function viewSettings() {
  const s = await api("GET", "/settings");
  const year = new Date().getFullYear();
  const hol = await api("GET", `/holidays?year=${year}`);
  const [ais, mt] = await Promise.all([api("GET", "/ai/status"), api("GET", "/settings/memo-template")]);
  view.innerHTML = `<h1>設定</h1>
    <form id="set-form" class="card">
      <label class="field"><span>放置アラートの既定日数</span><input type="number" name="stale_days" min="1" value="${s.stale_days}"></label>
      <label class="field"><span>期限通知の日数(何日前から通知するか)</span><input type="number" name="notify_days" min="0" value="${s.notify_days}"></label>
      <button class="primary">保存</button></form>
    <h2>バックアップ</h2>
    <div class="card"><dl class="kv"><dt>保存先</dt><dd>${h(s.backup_dir) || `<span class="tag danger">未設定</span>`}</dd>
      <dt>世代数</dt><dd>${s.backup_keep}</dd><dt>最終実行</dt><dd>${h((s.last_backup_at || "—").replace("T", " "))}</dd>
      <dt>ファイル</dt><dd class="small">${h(s.last_backup_file || "—")}</dd></dl>
      ${s.last_backup_error ? `<div class="alert danger small">${h(s.last_backup_error)}</div>` : ""}
      <button id="run-backup">今すぐバックアップ</button></div>
    <h2>セキュリティ</h2>
    <div class="card small"><dl class="kv"><dt>再認証の有効時間</dt><dd>${s.reauth_minutes}分</dd>
      <dt>フォルダ制限</dt><dd>${s.allowed_folder_roots.map(h).join("<br>") || "なし"}</dd></dl>
      <p class="muted">トークン・APIキーは PC の .env で管理します(画面には表示しません)。</p></div>
    <h2>AI・文字起こし</h2>
    <div class="card small"><dl class="kv">
      <dt>AI</dt><dd>${ais.ai_configured ? `<span class="tag ok">利用可</span> ${h(ais.model)}(${h(ais.effort)})` : `<span class="tag danger">未設定</span> .env の ANTHROPIC_API_KEY`}</dd>
      <dt>文字起こし</dt><dd>${ais.transcriber_installed ? `<span class="tag ok">利用可</span> faster-whisper ${h(ais.whisper_model)}` : `<span class="tag danger">未インストール</span>`}</dd>
      <dt>話者分離</dt><dd>${h(ais.diarization)}</dd>
      <dt>OCR</dt><dd>${ais.ocr_available ? `<span class="tag ok">利用可</span>` : `<span class="tag gray">未設定</span>(Tesseract)`}</dd></dl></div>
    <h3>相談メモの見出し(事務所様式)</h3>
    <form id="memo-form" class="card"><textarea name="sections">${h(mt.sections.join("\n"))}</textarea>
      <div class="muted small">1行に1見出し。既定: ${h(mt.default.join(" / "))}</div><button>保存</button></form>
    <h2>休日(${year}年)</h2>
    <div class="card small">${hol.national.map((x) => `${jdate(x.date)} ${h(x.name)}`).join("<br>")}</div>
    <h3>追加の休日(庁舎閉庁日等)</h3>
    <ul class="list">${hol.custom.map((x) => `<li class="row between"><span>${jdate(x.date)} ${h(x.name)}</span>
      <button class="small" data-del-hol="${x.date}">削除</button></li>`).join("")}</ul>
    <form id="hol-form" class="row"><input type="date" name="date" required class="grow"><input name="name" placeholder="名称" required class="grow">
      <button>追加</button></form>`;
  $("#set-form").onsubmit = async (e) => {
    e.preventDefault();
    const ok = await guard(() => api("PUT", "/settings", {
      stale_days: Number(e.target.stale_days.value), notify_days: Number(e.target.notify_days.value) }));
    if (ok) toast("保存しました");
  };
  $("#memo-form").onsubmit = async (e) => {
    e.preventDefault();
    const sections = e.target.sections.value.split("\n").map((x) => x.trim()).filter(Boolean);
    const ok = await guard(() => api("PUT", "/settings/memo-template", { sections }));
    if (ok) toast("保存しました");
  };
  $("#run-backup").onclick = async () => {
    const r = await guard(() => api("POST", "/backup/run"));
    if (r) { toast(`バックアップしました: ${r.file}`); route(); }
  };
  $("#hol-form").onsubmit = async (e) => {
    e.preventDefault();
    const ok = await guard(() => api("POST", "/holidays", { date: e.target.date.value, name: e.target.name.value }));
    if (ok) route();
  };
  view.querySelectorAll("[data-del-hol]").forEach((b) => b.addEventListener("click", async () => {
    await guard(() => api("DELETE", `/holidays/${b.dataset.delHol}`));
    route();
  }));
}

async function viewAudit() {
  const items = await api("GET", "/audit?limit=300");
  view.innerHTML = `<h1>操作ログ・監査ログ</h1><p class="muted small">直近300件。変更操作、ログイン、機微案件の閲覧、資料の閲覧、利益相反チェック等を記録しています。</p>
    <div class="card"><table class="tbl"><thead><tr><th>日時</th><th>操作</th><th>詳細</th></tr></thead><tbody>
    ${items.map((a) => `<tr><td>${h(a.ts.replace("T", " "))}</td><td>${h(a.action)}${a.case_id ? ` <a href="#/cases/${a.case_id}">#${a.case_id}</a>` : ""}</td>
      <td class="muted">${h(a.detail)} ${h(a.ip)}</td></tr>`).join("")}</tbody></table></div>`;
}

// ------------------------------------------------------------ v2 共通

async function waitJob(jobId, onProgress) {
  for (;;) {
    let j;
    try { j = await api("GET", `/jobs/${jobId}`); } catch (e) { toast(e.message, true); return null; }
    if (j.status === "完了" || j.status === "失敗") return j;
    if (onProgress) onProgress(j.progress || j.status);
    await new Promise((r) => setTimeout(r, 1500));
  }
}

function fmtSec(sec) {
  sec = Math.floor(sec || 0);
  const hh = Math.floor(sec / 3600), mm = Math.floor((sec % 3600) / 60), ss = sec % 60;
  return `${String(hh).padStart(2, "0")}:${String(mm).padStart(2, "0")}:${String(ss).padStart(2, "0")}`;
}
function yen(n) { return (n ?? 0).toLocaleString("ja-JP") + "円"; }
function hours(min) { return `${(min / 60).toFixed(1)}時間`; }

// 出典から原典を開くリンク属性
function sourceLink(caseId, c) {
  if (c.type === "file") {
    const page = c.page ? `#page=${c.page}` : "";
    return `href="/api/cases/${caseId}/files/open?path=${encodeURIComponent(c.rel_path)}${page}" target="_blank" rel="noopener"`;
  }
  if (c.type === "audio") return `href="#/cases/${caseId}/recordings?t=${c.transcript_id}&at=${Math.floor(c.t_start || 0)}"`;
  if (c.type === "activity") return `href="#/cases/${caseId}/activities"`;
  if (c.type === "communication") return `href="#/cases/${caseId}/comms"`;
  return `href="#/cases/${caseId}"`;
}

const MATCH_CLS = { 一致: "ok", 部分一致: "warning", 不一致: "danger", 出典なし: "danger", 引用なし: "warning" };

function citeChips(caseId, cits) {
  if (!cits || !cits.length) return `<span class="tag danger">出典なし</span>`;
  return cits.map((c) => `<span class="cite"><a ${sourceLink(caseId, c)}>${c.type === "audio" ? "🎙" : c.type === "file" ? "📄" : "📝"}
    ${h(c.label || c.source_id)}</a> <span class="tag ${MATCH_CLS[c.match] || ""}" title="引用: ${h(c.quote)}">${h(c.match)}</span>
    ${c.quote ? `<span class="quote">「${h(c.quote)}」</span>` : ""}</span>`).join("");
}

function itemHtml(caseId, it, body) {
  const bad = !it.citations?.length || it.citations.some((c) => c.match === "不一致" || c.match === "出典なし");
  return `<li class="${bad ? "flag" : ""}">${body ?? `<div class="pre">${h(it.text)}</div>`}
    <div class="cites">${citeChips(caseId, it.citations)}</div></li>`;
}

// ------------------------------------------------------------ AI タブ

const KIND_LABEL = { ask: "質問", memo: "相談メモ", timeline: "時系列・争点整理表" };

async function caseAI(c, params) {
  const box = $("#case-body");
  const [st, runs, terms] = await Promise.all([api("GET", "/ai/status"), api("GET", `/cases/${c.id}/ai/runs`),
    api("GET", `/cases/${c.id}/anon-terms`)]);
  const runId = new URLSearchParams(location.hash.split("?")[1] || "").get("run");
  box.innerHTML = `
    ${st.ai_configured ? "" : `<div class="alert warning">AI が未設定です。PC の .env に ANTHROPIC_API_KEY を設定してください。</div>`}
    <div class="alert info small">送信前に氏名・会社名・住所・連絡先を記号に置き換え、置換漏れがあれば送信しません。送信内容は確認でき、AI送信ログに記録されます。出力は初稿です。</div>
    <div class="card">
      <form id="ask-form"><label class="field"><span>この事件について質問(出典つきで回答)</span>
        <textarea name="q" placeholder="例: この事件の経緯は? / 納品日について資料間に食い違いはあるか"></textarea></label>
        <button class="primary" ${st.ai_configured ? "" : "disabled"}>確認して送信</button></form>
      <div class="row"><button id="mk-memo" ${st.ai_configured ? "" : "disabled"}>相談メモを作成</button>
        <button id="mk-tl" ${st.ai_configured ? "" : "disabled"}>時系列・争点整理表を作成</button></div>
      <p class="muted small">対象: 録音の文字起こし・索引化した資料・活動記録・連絡履歴・案件メモ</p>
    </div>
    <div id="ai-result"></div>
    <h2>実行履歴</h2>
    <ul class="list">${runs.map((r) => `<li class="link" data-run="${r.id}"><div class="row between">
      <span><span class="tag">${h(KIND_LABEL[r.kind] || r.kind)}</span> ${h(r.question || "")}</span>
      <span class="tag ${r.status === "完了" ? "ok" : "danger"}">${h(r.status)}</span></div>
      <div class="muted small">${h(r.created_at.replace("T", " "))} ${h(r.model || "")} ${h(r.error || "")}</div></li>`).join("")
      || `<li class="muted">まだありません</li>`}</ul>
    <h2>追加の匿名化語</h2>
    <p class="muted small">当事者として登録していない人名・地名・建物名・あだ名・言い間違いなどを登録すると、送信時に置換されます。</p>
    <ul class="list">${terms.map((t) => `<li class="row between"><span>${h(t.term)} <span class="tag gray">${h(t.category)}</span></span>
      <button class="small" data-del-term="${t.id}">削除</button></li>`).join("")}</ul>
    <form id="term-form" class="row"><input name="term" class="grow" placeholder="語句" required>
      <select name="category" class="grow"><option>人物</option><option>会社</option><option>地名</option><option>固有名</option></select>
      <button>追加</button></form>`;
  $("#ask-form").onsubmit = (e) => {
    e.preventDefault();
    const q = e.target.q.value.trim();
    if (!q) return toast("質問を入力してください", true);
    previewAndRun(c, "ask", q);
  };
  $("#mk-memo").onclick = () => previewAndRun(c, "memo", "");
  $("#mk-tl").onclick = () => previewAndRun(c, "timeline", "");
  box.querySelectorAll("[data-run]").forEach((li) => li.addEventListener("click", () => showRun(c, Number(li.dataset.run))));
  box.querySelectorAll("[data-del-term]").forEach((b) => b.addEventListener("click", async () => {
    await guard(() => api("DELETE", `/anon-terms/${b.dataset.delTerm}`));
    route();
  }));
  $("#term-form").onsubmit = async (e) => {
    e.preventDefault();
    const ok = await guard(() => api("POST", `/cases/${c.id}/anon-terms`, { term: e.target.term.value, category: e.target.category.value }));
    if (ok) route();
  };
  if (runId) showRun(c, Number(runId));
}

async function previewAndRun(c, kind, question) {
  const pv = await guard(() => api("POST", `/cases/${c.id}/ai/preview`, { kind, question }));
  if (!pv) return;
  const blocked = pv.leaks.length > 0;
  openModal(`<h1>送信内容の確認(${h(KIND_LABEL[kind])})</h1>
    ${blocked ? `<div class="alert danger">置換漏れの可能性がある語があるため送信できません: ${pv.leaks.map(h).join("、")}<br>
      「追加の匿名化語」に登録するか、当事者の表記を確認してください。</div>` : `<div class="alert ok">置換漏れは検出されませんでした。</div>`}
    ${pv.omitted_sources ? `<div class="alert warning">資料が多いため ${pv.omitted_sources} 件を送信対象から外しています。</div>` : ""}
    <p class="small">資料 ${pv.sources}件 ・ ${pv.chars.toLocaleString()}文字 ・ プロンプト版 ${h(pv.prompt_version)}</p>
    <details><summary>置換一覧(${pv.replacements.length}件・この PC 内でのみ表示)</summary>
      <table class="tbl"><tbody>${pv.replacements.map((r) => `<tr><td>${h(r.label)}</td><td>${h(r.original)}</td><td class="muted">${h(r.category)}</td></tr>`).join("")}</tbody></table></details>
    <details><summary>実際に送信する本文</summary><pre class="pre sent">${h(pv.sent_text)}</pre></details>
    <div class="actions"><button id="pv-cancel">キャンセル</button>
      <button class="primary" id="pv-send" ${blocked ? "disabled" : ""}>送信する</button></div>`);
  $("#pv-cancel").onclick = closeModal;
  $("#pv-send").onclick = async () => {
    $("#pv-send").disabled = true;
    const r = await guard(() => api("POST", `/cases/${c.id}/ai/run`, { kind, question }));
    if (!r) { $("#pv-send").disabled = false; return; }
    closeModal();
    $("#ai-result").innerHTML = `<div class="card"><p>AI が作成中です… <span id="ai-prog"></span></p><p class="muted small">1〜3分かかることがあります。画面を離れても処理は続きます。</p></div>`;
    const j = await waitJob(r.job_id, (p) => { const el = $("#ai-prog"); if (el) el.textContent = p; });
    if (!j) return;
    if (j.status !== "完了") { $("#ai-result").innerHTML = `<div class="alert danger">${h(j.error)}</div>`; return; }
    location.hash = `#/cases/${c.id}/ai?run=${j.result_id}`;
  };
}

async function showRun(c, runId) {
  const r = await guard(() => api("GET", `/ai/runs/${runId}`));
  if (!r) return;
  const box = $("#ai-result");
  if (!r.result) { box.innerHTML = `<div class="alert danger">${h(r.status)}: ${h(r.error)}</div>`; return; }
  const res = r.result, st = res.citation_stats || {};
  let body = "";
  if (r.kind === "ask") {
    body = `<h3>Q. ${h(r.question)}</h3><ul class="list ai">${res.answer.map((it) => itemHtml(c.id, it)).join("")}</ul>
      ${res.not_found.length ? `<h3>資料から分からない点</h3><ul>${res.not_found.map((x) => `<li>${h(x)}</li>`).join("")}</ul>` : ""}`;
  } else if (r.kind === "memo") {
    body = res.sections.map((s) => `<h3>■ ${h(s.heading)}</h3>
      <ul class="list ai">${s.items.map((it) => itemHtml(c.id, it)).join("") || `<li class="muted">なし</li>`}</ul>`).join("")
      + (res.caveats.length ? `<h3>注意</h3><ul>${res.caveats.map((x) => `<li>${h(x)}</li>`).join("")}</ul>` : "");
  } else {
    body = `<h3>時系列</h3><ul class="list ai">${res.timeline.map((t) => itemHtml(c.id, t,
      `<div><b>${h(t.date || "日付不明")}</b> <span class="tag ${t.certainty === "確実" ? "ok" : "warning"}">${h(t.certainty)}</span></div>
       <div class="pre">${h(t.event)}</div>${t.note ? `<div class="muted small">${h(t.note)}</div>` : ""}`)).join("")}</ul>
      <h3>争点整理表</h3><ul class="list ai">${res.issues.map((i) => itemHtml(c.id, i,
      `<div class="title">${h(i.issue)} <span class="tag ${i.status === "争いあり" ? "danger" : "gray"}">${h(i.status)}</span></div>
       <dl class="kv small"><dt>当方</dt><dd>${h(i.our_position)}</dd><dt>相手方</dt><dd>${h(i.their_position)}</dd>
       ${i.open_questions.length ? `<dt>未確認</dt><dd>${i.open_questions.map(h).join("<br>")}</dd>` : ""}</dl>`)).join("")}</ul>
      ${res.contradictions.length ? `<h3>資料間・発言の食い違い</h3><ul class="list ai">${res.contradictions.map((it) => itemHtml(c.id, it)).join("")}</ul>` : ""}
      <p><a class="btn small" href="/api/ai/runs/${r.id}/csv">CSV(Excel)で出力</a></p>`;
  }
  box.innerHTML = `<div class="card">
    <div class="row between"><b>${h(KIND_LABEL[r.kind])}(AI初稿・要確認)</b><span class="muted small">${h(r.created_at.replace("T", " "))}</span></div>
    <div class="small">出典照合: <span class="tag ok">一致 ${st.verified || 0}</span> <span class="tag warning">部分一致 ${st.partial || 0}</span>
      <span class="tag danger">不一致 ${st.unverified || 0}</span> <span class="tag danger">出典なし ${(st.missing_source || 0) + (st.uncited_items || 0)}</span></div>
    ${res.omitted_sources ? `<div class="alert warning small">資料 ${res.omitted_sources} 件は送信対象外でした。</div>` : ""}
    ${body}
    <div class="row"><button id="save-act">活動記録に保存</button><button id="show-sent">送信した内容</button></div></div>`;
  $("#save-act").onclick = async () => {
    const ok = await guard(() => api("POST", `/ai/runs/${r.id}/save-activity`));
    if (ok) toast("活動記録に保存しました");
  };
  $("#show-sent").onclick = () => {
    openModal(`<h1>送信した内容(匿名化済み)</h1><p class="small">モデル ${h(r.model)} ・ 入力 ${r.input_tokens ?? "-"} / 出力 ${r.output_tokens ?? "-"} トークン ・ プロンプト版 ${h(r.prompt_version)}</p>
      <pre class="pre sent">${h(r.sent_text)}</pre><div class="actions"><button id="sent-close">閉じる</button></div>`);
    $("#sent-close").onclick = closeModal;
  };
  box.scrollIntoView({ behavior: "smooth" });
}

// ------------------------------------------------------------ 録音タブ

async function caseRecordings(c) {
  const box = $("#case-body");
  const params = new URLSearchParams(location.hash.split("?")[1] || "");
  const [st, recs] = await Promise.all([api("GET", "/ai/status"), api("GET", `/cases/${c.id}/recordings`)]);
  box.innerHTML = `
    <div class="card"><form id="rec-form">
      <label class="field"><span>録音ファイル(iPhone のボイスメモ → 共有 →「ファイルに保存」したもの等)</span>
        <input type="file" name="file" accept="audio/*,.m4a,.mp3,.wav" required></label>
      <label class="field"><span>録音日</span><input type="date" name="recorded_on" value="${today()}"></label>
      <button class="primary">取り込んで文字起こし</button></form>
      <p class="muted small">文字起こしはこの PC 内で行います(音声は外部に送信しません)。${st.transcriber_installed ? `エンジン: faster-whisper(${h(st.whisper_model)})、話者分離: ${h(st.diarization)}` : `<span class="tag danger">faster-whisper が未インストール</span>`}</p>
      <div id="rec-prog"></div></div>
    <ul class="list">${recs.map((r) => `<li class="link" data-rec="${r.id}"><div class="row between">
      <span>🎙 ${h(r.filename)}</span><span class="tag ${r.status === "完了" ? "ok" : r.status === "失敗" ? "danger" : "warning"}">${h(r.status)}</span></div>
      <div class="muted small">${jdate(r.recorded_on)} ${r.duration ? fmtSec(r.duration) : ""} ${h(r.message || "")}</div></li>`).join("")
      || `<li class="muted">録音はありません</li>`}</ul>
    <div id="transcript"></div>`;
  $("#rec-form").onsubmit = async (e) => {
    e.preventDefault();
    const fd = new FormData(e.target);
    const btn = e.target.querySelector("button");
    btn.disabled = true;
    $("#rec-prog").textContent = "アップロード中…";
    let res;
    try {
      const r = await fetch(`/api/cases/${c.id}/recordings`, { method: "POST", body: fd, headers: { "x-cm": "1" }, credentials: "same-origin" });
      res = await r.json();
      if (!r.ok) throw new Error(res.detail?.message || res.detail || r.statusText);
    } catch (err) { toast(err.message, true); btn.disabled = false; $("#rec-prog").textContent = ""; return; }
    const j = await waitJob(res.job_id, (p) => { $("#rec-prog").textContent = `文字起こし中… ${p}`; });
    btn.disabled = false;
    if (j?.status === "完了") { toast("文字起こしが完了し、活動記録に保存しました"); location.hash = `#/cases/${c.id}/recordings?t=${res.transcript_id}`; }
    else if (j) toast(`失敗: ${j.error}`, true);
  };
  box.querySelectorAll("[data-rec]").forEach((li) => li.addEventListener("click", () => {
    location.hash = `#/cases/${c.id}/recordings?t=${li.dataset.rec}`;
  }));
  if (params.get("t")) showTranscript(c, Number(params.get("t")), Number(params.get("at") || 0));
}

async function showTranscript(c, tid, at) {
  const t = await guard(() => api("GET", `/transcripts/${tid}`));
  if (!t) return;
  const box = $("#transcript");
  if (t.status !== "完了") { box.innerHTML = `<div class="alert warning">${h(t.status)} ${h(t.message || "")}</div>`; return; }
  const spk = [...new Set(t.segments.map((s) => s.speaker || ""))];
  const name = (s) => t.speakers[s || ""] || s || "話者不明";
  box.innerHTML = `<div class="card"><div class="row between"><b>🎙 ${h(t.filename)}</b><span class="muted small">${fmtSec(t.duration)} ${h(t.engine)}</span></div>
    <audio id="player" controls preload="metadata" src="/api/transcripts/${t.id}/audio"></audio>
    <h3>話者名</h3><div id="spk">${spk.map((s) => `<label class="field"><span>${h(s || "話者不明")}</span>
      <input data-spk="${h(s)}" value="${h(t.speakers[s] || "")}" placeholder="例: 依頼者 / 弁護士"></label>`).join("")}</div>
    <h3>本文(時刻をタップで再生・本文をタップで修正)</h3>
    <ul class="list segs">${t.segments.map((s, i) => `<li data-seg="${i}" class="${at && s.start <= at && at < s.end + 1 ? "flag" : ""}">
      <button class="small" data-play="${s.start}">${fmtSec(s.start)}</button> <b>${h(name(s.speaker))}</b>
      <div class="pre seg-text">${h(s.text)}</div></li>`).join("")}</ul>
    <div class="row"><button class="primary" id="save-tr">修正を保存</button><button class="danger" id="del-tr">録音を削除</button></div></div>`;
  const player = $("#player");
  if (at) player.addEventListener("loadedmetadata", () => { player.currentTime = at; }, { once: true });
  box.querySelectorAll("[data-play]").forEach((b) => b.addEventListener("click", () => {
    player.currentTime = Number(b.dataset.play);
    player.play().catch(() => {});
  }));
  box.querySelectorAll(".seg-text").forEach((el) => el.addEventListener("click", () => {
    const i = Number(el.closest("[data-seg]").dataset.seg);
    const v = prompt("文字起こしの修正", t.segments[i].text);
    if (v !== null) { t.segments[i].text = v; el.textContent = v; }
  }));
  $("#save-tr").onclick = async () => {
    const speakers = {};
    box.querySelectorAll("[data-spk]").forEach((i) => { if (i.value.trim()) speakers[i.dataset.spk] = i.value.trim(); });
    const ok = await guard(() => api("PUT", `/transcripts/${t.id}`, { speakers, segments: t.segments }));
    if (ok) { toast("保存しました(活動記録にも反映)"); showTranscript(c, tid, 0); }
  };
  $("#del-tr").onclick = async () => {
    if (!confirm("録音と文字起こし(活動記録を含む)を削除します。よろしいですか?")) return;
    const ok = await guard(() => api("DELETE", `/transcripts/${t.id}`));
    if (ok) { toast("削除しました"); location.hash = `#/cases/${c.id}/recordings`; }
  };
  if (at) box.querySelector(".flag")?.scrollIntoView({ block: "center" });
}

// ------------------------------------------------------------ 会計タブ(報酬・入金・預り金・稼働)

const FIN_KINDS = ["請求", "入金", "実費支出", "預り金受入", "預り金支出", "預り金返還"];

async function caseMoney(c) {
  const f = await api("GET", `/cases/${c.id}/finance`);
  const s = f.summary, w = f.worktime;
  const hourly = w.minutes ? Math.round(s.fees.received / (w.minutes / 60)) : null;
  $("#case-body").innerHTML = `
    ${s.warnings.map((x) => `<div class="alert danger">${h(x)}</div>`).join("")}
    <h2>報酬</h2><div class="stats three">
      <div class="stat"><b>${yen(s.fees.billed)}</b><span>請求</span></div>
      <div class="stat"><b>${yen(s.fees.received)}</b><span>入金</span></div>
      <div class="stat"><b>${yen(s.fees.receivable)}</b><span>未収</span></div></div>
    ${s.fees.advance ? `<div class="small">請求前の入金(前受): ${yen(s.fees.advance)}</div>` : ""}
    <div class="small muted">${Object.entries(s.fees.by_category).map(([k, v]) => `${h(k)}: 請求 ${yen(v.billed)} / 入金 ${yen(v.received)}`).join("<br>")}</div>
    <h2>実費(立替)</h2><div class="stats three">
      <div class="stat"><b>${yen(s.expenses.spent)}</b><span>支出</span></div>
      <div class="stat"><b>${yen(s.expenses.recovered)}</b><span>回収</span></div>
      <div class="stat"><b>${yen(s.expenses.outstanding)}</b><span>立替残</span></div></div>
    <h2>預り金(報酬と分けて管理)</h2><div class="card deposit"><div class="stats three">
      <div class="stat"><b>${yen(s.deposit.received)}</b><span>受入</span></div>
      <div class="stat"><b>${yen(s.deposit.paid + s.deposit.returned)}</b><span>支出・返還</span></div>
      <div class="stat"><b>${yen(s.deposit.balance)}</b><span>残高</span></div></div></div>
    <h2>稼働</h2><div class="card"><dl class="kv">
      <dt>稼働時間</dt><dd>${hours(w.minutes)}(${w.records}件)</dd>
      <dt>時給換算</dt><dd>${hourly !== null ? yen(hourly) + "(入金ベース)" : "—"}</dd>
      <dt>種類別</dt><dd class="small">${Object.entries(w.by_kind).map(([k, v]) => `${h(k)} ${hours(v)}`).join(" / ") || "—"}</dd>
      <dt>月別</dt><dd class="small">${Object.entries(w.by_month).map(([k, v]) => `${h(k)} ${hours(v)}`).join(" / ") || "—"}</dd></dl>
      ${w.records_without_minutes ? `<div class="muted small">所要時間が未入力の活動記録が ${w.records_without_minutes} 件あります(集計対象外)。</div>` : ""}</div>
    <h2>入出金の記録<button class="small primary" id="add-fin">追加</button></h2>
    <table class="tbl"><thead><tr><th>日付</th><th>種別</th><th>区分</th><th>金額</th><th>備考</th></tr></thead><tbody>
    ${f.entries.map((e) => `<tr class="link" data-fin="${e.id}"><td>${h(e.date)}</td><td>${h(e.kind)}</td><td>${h(e.category)}</td>
      <td>${yen(e.amount)}</td><td>${h(e.note)}</td></tr>`).join("")}</tbody></table>`;
  const dialog = (e) => formDialog({
    title: e ? "入出金の編集" : "入出金の追加",
    fields: [
      { name: "date", label: "日付", type: "date", required: true, value: e?.date || today() },
      { name: "kind", label: "種別", type: "select", options: FIN_KINDS, value: e?.kind || "入金" },
      { name: "category", label: "区分(請求・入金は報酬の種類か「実費」)", type: "select",
        options: [...f.fee_categories, "実費", ...f.expense_categories, "預り金"], value: e?.category || "着手金" },
      { name: "amount", label: "金額(円・税込)", type: "number", required: true, value: e?.amount },
      { name: "note", label: "備考", value: e?.note },
    ],
    onSubmit: (v) => e ? api("PUT", `/finance/${e.id}`, v) : api("POST", `/cases/${c.id}/finance`, v),
    danger: e ? { label: "削除", onClick: () => api("DELETE", `/finance/${e.id}`) } : null,
  });
  $("#add-fin").onclick = () => dialog();
  $("#case-body").querySelectorAll("[data-fin]").forEach((tr) => tr.addEventListener("click", () =>
    dialog(f.entries.find((x) => x.id === Number(tr.dataset.fin)))));
}

async function viewProfit() {
  const p = await api("GET", "/reports/profitability");
  view.innerHTML = `<h1>稼働・採算</h1>
    <p class="muted small">報酬は入金ベース(実費・預り金を除く)。稼働時間は活動記録の所要時間の合計です。</p>
    <div class="stats three"><div class="stat"><b>${hours(p.total.minutes)}</b><span>稼働</span></div>
      <div class="stat"><b>${yen(p.total.fees_received)}</b><span>報酬入金</span></div>
      <div class="stat"><b>${p.total.hourly_received ? yen(p.total.hourly_received) : "—"}</b><span>平均時給</span></div></div>
    <div class="card"><table class="tbl"><thead><tr><th>案件</th><th>稼働</th><th>入金</th><th>時給</th></tr></thead><tbody>
    ${p.cases.map((r) => `<tr class="link" data-href="#/cases/${r.case_id}/money"><td>${h(r.title)} <span class="muted">${h(r.status)}</span>
      ${r.records_without_minutes ? `<div class="muted">時間未入力 ${r.records_without_minutes}件</div>` : ""}</td>
      <td>${hours(r.minutes)}</td><td>${yen(r.fees_received)}</td><td>${r.hourly_received ? yen(r.hourly_received) : "—"}</td></tr>`).join("")}
    </tbody></table></div>`;
}

async function viewAILog() {
  const items = await api("GET", "/ai/log");
  view.innerHTML = `<h1>AI送信ログ</h1><p class="muted small">外部 AI に送信した記録です。送信本文は匿名化済みのもので、各実行の「送信した内容」から確認できます。</p>
    <div class="card"><table class="tbl"><thead><tr><th>日時</th><th>案件・種類</th><th>状態</th><th>文字数</th></tr></thead><tbody>
    ${items.map((r) => `<tr class="link" data-href="#/cases/${r.case_id}/ai?run=${r.id}"><td>${h(r.created_at.replace("T", " "))}</td>
      <td>#${r.case_id} ${h(KIND_LABEL[r.kind] || r.kind)}<div class="muted">${h(r.model)} 版${h(r.prompt_version)}</div></td>
      <td>${h(r.status)} ${h(r.error || "")}</td><td>${(r.sent_chars || 0).toLocaleString()}</td></tr>`).join("")}</tbody></table></div>`;
}

// ------------------------------------------------------------ 通知

function updateBell(list) {
  const n = list.filter((x) => x.level !== "info").length;
  const b = $("#bell-count");
  b.textContent = n;
  b.classList.toggle("hidden", !n);
  updateBell.last = list;
}

async function pollNotifications() {
  if ($("#tabbar").classList.contains("hidden")) return;
  try { updateBell(await api("GET", "/notifications")); } catch { /* 無視 */ }
}

document.addEventListener("click", (e) => {
  const el = e.target.closest("[data-href]");
  if (el && !e.target.closest("a, button:not([data-href]), input, label")) {
    location.hash = el.dataset.href;
    return;
  }
  if (e.target.closest("[data-action=show-notifications]")) {
    const list = updateBell.last || [];
    openModal(`<h1>通知</h1>${list.length ? list.map((n) => `<div class="alert ${n.level}">
      ${n.case_id ? `<a href="#/cases/${n.case_id}${n.type === "stale" ? "" : "/deadlines"}">${h(n.text)}</a>` : h(n.text)}</div>`).join("")
      : `<p class="muted">通知はありません。</p>`}<div class="actions"><button id="nt-close">閉じる</button></div>`);
    $("#nt-close").onclick = closeModal;
  }
});

// ------------------------------------------------------------ 起動

(async function init() {
  if ("serviceWorker" in navigator) navigator.serviceWorker.register("/sw.js").catch(() => {});
  try {
    await api("GET", "/auth/status");
    await loadMeta();
    await route();
    pollNotifications();
    setInterval(pollNotifications, 5 * 60 * 1000);
  } catch (e) {
    if (e.status !== 401) view.innerHTML = `<div class="alert danger">サーバーに接続できません: ${h(e.message)}</div>`;
  }
})();
