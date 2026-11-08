"use strict";

const paths = {
  grid: "M3 3h7v7H3zM14 3h7v7h-7zM3 14h7v7H3zM14 14h7v7h-7z",
  chart: "M3 3v18h18M6 14l4-4 4 3 6-8",
  spark: "m12 3 2.4 6.6L21 12l-6.6 2.4L12 21l-2.4-6.6L3 12l6.6-2.4L12 3Z",
  folder: "M3 7V5a1 1 0 0 1 1-1h5l2 3h9a1 1 0 0 1 1 1v11H3V7Z",
  clock: "M12 8v4l3 2M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z",
  wind: "M3 8h12a3 3 0 1 0-3-3M3 12h16a3 3 0 1 1-3 3M3 16h5a3 3 0 1 1-3 3",
  alert: "m12 3 10 18H2L12 3ZM12 9v5M12 17h.01",
  check: "m5 12 4 4L19 6",
  x: "m6 6 12 12M6 18 18 6",
  arrow: "M5 12h14m-5-5 5 5-5 5",
  plus: "M12 5v14M5 12h14",
  info: "M12 11v6M12 7h.01M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z",
  search: "m16 16 5 5M18 10a8 8 0 1 1-16 0 8 8 0 0 1 16 0Z",
  download: "M12 3v12m-4-4 4 4 4-4M4 17v4h16v-4",
  refresh:
    "M3 10a9 9 0 0 1 15-6l3 3M21 3v4h-4M21 14A9 9 0 0 1 6 20l-3-3M3 21v-4h4",
  database:
    "M21 5c0 2-4 3-9 3S3 7 3 5s4-3 9-3 9 1 9 3ZM3 5v14c0 2 4 3 9 3s9-1 9-3V5M3 12c0 2 4 3 9 3s9-1 9-3",
  file: "M14 2H5v20h14V7l-5-5ZM14 2v6h5M8 12h8M8 16h8",
  turbine: "M12 8v14M12 8 8 2M12 8l8-1M12 8l-6 7M10 22h4",
};
const icon = (name) =>
  `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="${paths[name] || paths.info}"/></svg>`;
const esc = (value) =>
  String(value ?? "").replace(
    /[&<>"']/g,
    (c) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[
        c
      ],
  );
const dt = (value, options = {}) =>
  new Intl.DateTimeFormat("en-GB", {
    timeZone: "Europe/Copenhagen",
    day: "2-digit",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
    ...options,
  }).format(new Date(value));
const clock = (value) =>
  new Intl.DateTimeFormat("en-GB", {
    timeZone: "Europe/Copenhagen",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(value));
const badge = (label, color = "") =>
  `<span class="badge ${color}">${esc(label)}</span>`;
const button = (label, action, style = "", extra = "") =>
  `<button class="button ${style}" data-action="${action}" ${extra}>${label}</button>`;
const S = {
  user: null,
  csrf: "",
  users: [],
  accountEvents: [],
  data: null,
  detail: null,
  view: "overview",
  range: 24,
  filter: "All",
  search: "",
  decisions: {},
  editing: false,
  error: "",
  busy: false,
  newKind: "fault",
  pending: new Map(),
};
let toastTimer;

function toast(message, error = false) {
  const el = document.getElementById("toast");
  el.textContent = message;
  el.className = `visible${error ? " error" : ""}`;
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => {
    el.className = "";
  }, 5000);
}
function connection(ok) {
  const el = document.getElementById("connection");
  el.className = `connection${ok ? "" : " offline"}`;
  el.innerHTML = `<i class="status-dot"></i>${ok ? "Database connected" : "Connection unavailable"}`;
}
async function api(path, options = {}) {
  const headers = { Accept: "application/json", ...options.headers };
  if (options.method && options.method !== "GET" && S.csrf) headers["X-CSRF-Token"] = S.csrf;
  let response;
  try {
    response = await fetch(path, { ...options, credentials: "same-origin", headers, cache: "no-store" });
  } catch {
    throw new Error(
      "Cannot reach the application. Check your connection and that the demo server is running, then refresh.",
    );
  }
  let body;
  try {
    body = await response.json();
  } catch {
    throw new Error(
      "The application returned an unreadable response. Please refresh.",
    );
  }
  if (!response.ok) {
    const message =
      body.error?.message || "The request could not be completed.";
    const fields = body.error?.fields
      ?.map((f) => `${f.field.replace("body.", "")}: ${f.message}`)
      .join(" ");
    const error = new Error(fields ? `${message} ${fields}` : message);
    error.status = response.status;
    if (body.error?.code === "AUTH_REQUIRED") signedOut();
    if (body.error?.code === "PASSWORD_CHANGE_REQUIRED") { S.user.must_change_password = true; render(); }
    throw error;
  }
  return body;
}
async function mutate(path, fields = {}, method = "POST") {
  const fingerprint = method + path + JSON.stringify(fields);
  if (!S.pending.has(fingerprint))
    S.pending.set(fingerprint, crypto.randomUUID());
  const request_id = S.pending.get(fingerprint);
  try {
    const result = await api(path, {
      method,
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ request_id, ...fields }),
    });
    S.pending.delete(fingerprint);
    return result;
  } catch (error) {
    if (error.status && error.status < 500) S.pending.delete(fingerprint);
    throw error;
  }
}
async function load(scenarioId = S.detail?.scenario.id) {
  const session = await api("/api/auth/me");
  S.user = session.user;
  S.csrf = session.csrf_token;
  if (S.user.must_change_password) { render(); return; }
  if (S.view === "users" && S.user.role !== "admin") S.view = "overview";
  if (S.view === "users") await loadUsers();
  const data = await api("/api/overview");
  const selected =
    scenarioId && data.scenarios.some((s) => s.id === scenarioId)
      ? scenarioId
      : data.active_scenario_id;
  const detail = selected ? await api(`/api/scenarios/${selected}`) : null;
  S.data = data;
  S.detail = detail;
  S.error = "";
  S.editing = false;
  S.decisions = {};
  connection(true);
  render();
}
async function act(task, trigger) {
  if (S.busy) return;
  S.busy = true;
  document.body.setAttribute("aria-busy", "true");
  if (trigger) {
    trigger.disabled = true;
    trigger.dataset.oldLabel = trigger.innerHTML;
    trigger.textContent = "Working…";
  }
  try {
    await task();
  } catch (error) {
    toast(error.message, true);
    if (!error.status || error.status >= 500) {
      connection(false);
      S.error = error.message;
      let warning = document.getElementById("connection-failure");
      if (!warning) {
        warning = document.createElement("div");
        warning.id = "connection-failure";
        warning.className = "error-banner";
        warning.setAttribute("role", "alert");
        document.getElementById("main").prepend(warning);
      }
      warning.textContent =
        error.message +
        " Displayed records may be out of date. Use Refresh to reconnect.";
    }
    const holder = document.getElementById("modal-error");
    if (holder) holder.textContent = error.message;
    if (error.status === 409) {
      try {
        await load();
      } catch {
        connection(false);
      }
    }
  } finally {
    S.busy = false;
    document.body.removeAttribute("aria-busy");
    if (trigger?.isConnected) {
      trigger.disabled = false;
      trigger.innerHTML = trigger.dataset.oldLabel;
    }
  }
}
function navigate(view) {
  if (!S.user || (view === "users" && S.user.role !== "admin")) return;
  S.view = view;
  S.editing = false;
  S.decisions = {};
  document.body.classList.remove("nav-open");
  render();
  window.scrollTo({ top: 0, behavior: "instant" });
}
function navigation() {
  const items = [
    ["overview", "grid", "Overview"],
    ["history", "chart", "Sensor history"],
    ["review", "spark", "Forecast reviews"],
    ["cases", "folder", "Predictive cases"],
    ["activity", "clock", "Activity log"],
  ];
  if (S.user.role === "admin") items.push(["users", "grid", "User administration"]);
  document.getElementById("navigation").innerHTML = items
    .map(
      ([key, symbol, label]) =>
        `<button class="nav-link ${(S.view === "case" ? "cases" : S.view) === key ? "active" : ""}" data-action="nav" data-view="${key}" ${(S.view === "case" ? "cases" : S.view) === key ? 'aria-current="page"' : ""}>${icon(symbol)}<span>${label}</span>${key === "review" && S.data.metrics.pending_reviews ? `<span class="nav-count">${S.data.metrics.pending_reviews}</span>` : ""}</button>`,
    )
    .join("");
}
function heading() {
  const copy = {
    overview: [
      "Maintenance overview",
      "From sensor evidence to a reviewed maintenance decision.",
    ],
    history: [
      "Sensor history",
      "Inspect the readings and evidence behind each analysis window.",
    ],
    review: [
      "Forecast review",
      "Apply specialist judgement to an illustrated failure forecast.",
    ],
    cases: [
      "Predictive cases",
      "A traceable record of faults, reviewed risks and maintenance outcomes.",
    ],
    case: [
      "Case workspace",
      "Follow the evidence, decisions and outcome of this predictive case.",
    ],
    users: ["User administration", "Manage access to the shared maintenance workspace."],
    activity: [
      "Activity log",
      "Every recorded step, from sensor readings to case resolution.",
    ],
  };
  const [title, subtitle] = copy[S.view] || copy.overview;
  return `<div class="page-heading"><div><div class="eyebrow">WIND TURBINE OPERATIONS</div><h1>${title}</h1><p>${subtitle}</p></div><div class="heading-actions"><span class="date-label">${dt(new Date(), { hour: undefined, minute: undefined, year: "numeric" })}</span>${button(icon("plus") + "New demo scenario", "new", "primary")}</div></div><div class="notice">${icon("info")}<span><strong>A working prototype.</strong> Sensor data, forecasts and external maintenance outcomes are simulated.</span><button class="text-button" data-action="about">How it works ↗</button></div>`;
}
function render() {
  profile();
  if (!S.user) { loginView(); return; }
  if (S.user.must_change_password) {
    document.getElementById("navigation").innerHTML = "";
    document.getElementById("main").innerHTML = `<div class="auth-shell"><section class="card auth-card"><div class="eyebrow">ACCOUNT SECURITY</div><h1>Choose your own password</h1><p>Your administrator supplied a temporary password. Change it before opening the workspace.</p>${passwordForm()}</section></div>`;
    return;
  }
  if (!S.data) return;
  navigation();
  const view =
    {
      overview: overviewView,
      history: historyView,
      review: reviewView,
      cases: casesView,
      case: caseView,
      activity: activityView,
      users: usersView,
    }[S.view] || overviewView;
  document.getElementById("main").innerHTML =
    heading() +
    (S.error
      ? `<div class="error-banner">${esc(S.error)}${button("Retry", "refresh")}</div>`
      : "") +
    view();
  if (S.view === "review") updateReviewSubmit();
}
function latest() {
  return S.detail?.readings.filter((r) => r.quality === "Usable").at(-1);
}
function metrics() {
  const wind = latest();
  const m = S.data.metrics;
  return `<div class="metrics">${[
    [
      "Latest wind speed",
      wind ? wind.value.toFixed(1) : "—",
      "m/s",
      "wind",
      "",
      wind
        ? `${clock(wind.measured_at)} · Selected window`
        : "No usable readings",
    ],
    [
      "Current fault alerts",
      m.alerts,
      "",
      "alert",
      "amber",
      "Incidents awaiting a resolved case",
    ],
    [
      "Awaiting forecast review",
      m.pending_reviews,
      "",
      "spark",
      "violet",
      "Human judgement required",
    ],
    [
      "Open predictive cases",
      m.open_cases,
      "",
      "folder",
      "blue",
      "Ready for external maintenance",
    ],
  ]
    .map(
      ([label, value, unit, symbol, color, caption]) =>
        `<article class="metric ${color}"><div class="metric-top"><span>${label}</span><span class="metric-icon">${icon(symbol)}</span></div><div class="metric-value">${value}<small>${unit}</small></div><div class="metric-caption">${color ? "" : '<i class="status-dot"></i>'}${caption}</div></article>`,
    )
    .join("")}</div>`;
}
function chart() {
  const all = S.detail?.readings || [];
  const end = all.length
    ? new Date(all.at(-1).measured_at).getTime()
    : Date.now();
  const readings = all.filter(
    (r) => new Date(r.measured_at).getTime() >= end - S.range * 3600000,
  );
  const usable = readings.filter(
    (r) => r.quality === "Usable" && r.value !== null,
  );
  let graphic;
  if (!usable.length)
    graphic = `<div class="empty"><div>${icon("chart")}</div><h3>No usable readings in this window</h3><p>${all.length ? "Invalid readings are retained in Sensor history but excluded from analysis." : "Add a reading to your custom window to begin."}</p></div>`;
  else {
    const width = 760,
      height = 205,
      left = 36,
      right = 24,
      top = 18,
      bottom = 29;
    const graphW = width - left - right,
      graphH = height - top - bottom;
    const start = Math.min(
      new Date(readings[0].measured_at).getTime(),
      end - 3600000,
    );
    const span = end - start;
    const ymax = Math.max(
      40,
      Math.ceil(Math.max(...usable.map((r) => r.value)) / 10) * 10,
    );
    const x = (r) =>
      left + ((new Date(r.measured_at).getTime() - start) / span) * graphW;
    const y = (v) => top + graphH * (1 - v / ymax);
    let connected = false;
    const line = readings
      .map((r) => {
        if (r.quality !== "Usable" || r.value === null) {
          connected = false;
          return "";
        }
        const part = `${connected ? "L" : "M"}${x(r).toFixed(1)},${y(r.value).toFixed(1)}`;
        connected = true;
        return part;
      })
      .join(" ");
    const peak = usable.reduce((a, b) => (a.value > b.value ? a : b));
    const ticks = [0, 1, 2, 3, 4]
      .map((j) => {
        const v = (ymax * j) / 4;
        return `<line x1="${left}" y1="${y(v)}" x2="${width - right}" y2="${y(v)}" stroke="#edf1f2" stroke-dasharray="3 4"/><text x="${left - 11}" y="${y(v) + 3}" text-anchor="end">${v}</text>`;
      })
      .join("");
    const times = [0, 1, 2, 3, 4, 5]
      .map(
        (j) =>
          `<text x="${left + (graphW * j) / 5}" y="${height - 5}" text-anchor="${j === 0 ? "start" : j === 5 ? "end" : "middle"}">${clock(start + (span * j) / 5)}</text>`,
      )
      .join("");
    const area = `M${x(usable[0])},${y(0)} ${usable.map((r) => `L${x(r).toFixed(1)},${y(r.value).toFixed(1)}`).join(" ")} L${x(usable.at(-1))},${y(0)}Z`;
    graphic = `<div class="chart"><svg viewBox="0 0 ${width} ${height}" role="img" aria-label="Synthetic wind speed history; illustrative fault threshold strictly above 28 metres per second"><defs><linearGradient id="chart-fill" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stop-color="#438b76" stop-opacity=".15"/><stop offset="100%" stop-color="#438b76" stop-opacity=".015"/></linearGradient></defs>${ticks}<path d="${area}" fill="url(#chart-fill)"/><line x1="${left}" x2="${width - right}" y1="${y(28)}" y2="${y(28)}" stroke="#d4ad71" stroke-width="1" stroke-dasharray="5 5"/><rect x="${width - 111}" y="${y(28) - 16}" width="91" height="15" rx="3" fill="white"/><text x="${width - 25}" y="${y(28) - 6}" class="threshold-label" text-anchor="end">Demo rule · 28 m/s</text><path d="${line}" stroke="#438b76" stroke-width="2" stroke-linejoin="round" stroke-linecap="round" fill="none"/>${peak.value > 28 ? `<circle cx="${x(peak)}" cy="${y(peak.value)}" r="4" fill="#c5914b" stroke="white" stroke-width="2"/><text x="${x(peak)}" y="${y(peak.value) - 11}" text-anchor="middle" class="peak-label">${peak.value.toFixed(1)}</text>` : ""}${times}${usable.map((r) => `<circle cx="${x(r)}" cy="${y(r.value)}" r="6" fill="transparent"><title>${clock(r.measured_at)} · ${r.value} m/s · Synthetic</title></circle>`).join("")}</svg></div>`;
  }
  return `<section class="card chart-card"><div class="card-header"><div><h2>Wind speed history</h2><p class="card-subtitle">WT-017 <span aria-hidden="true">·</span> ${esc(S.detail?.scenario.title || "No analysis window")}</p></div><div class="segmented" aria-label="Chart time range"><button data-action="range" data-range="6" class="${S.range === 6 ? "active" : ""}" aria-pressed="${S.range === 6}">6 hours</button><button data-action="range" data-range="24" class="${S.range === 24 ? "active" : ""}" aria-pressed="${S.range === 24}">24 hours</button></div></div><div class="chart-topline"><span>WIND SPEED (m/s)</span><div class="chart-legend"><span class="legend-item"><i class="legend-mark"></i>Wind speed</span><span class="legend-item"><i class="legend-mark threshold"></i>Demo threshold</span></div></div>${graphic}<div class="chart-footer"><span>${readings.length} ${readings.length === 1 ? "reading" : "readings"} in this range · Synthetic source</span><strong>${usable.length} usable ${usable.length === 1 ? "reading" : "readings"}</strong></div></section>`;
}
function asset() {
  const d = S.detail;
  const count = d?.readings.length || 0;
  const usable = d?.readings.filter((r) => r.quality === "Usable").length || 0;
  const latestAt = d?.readings.at(-1)?.measured_at;
  const stale = latestAt && Date.now() - new Date(latestAt).getTime() > 3600000;
  const dataLabel = !count
    ? "No data"
    : stale
      ? "Historical data"
      : "Demo replay";
  return `<section class="card asset-card"><div class="card-header"><h2>Asset snapshot</h2>${badge("1 asset")}</div><div class="asset-visual"><span class="asset-identifier">DEMO WIND TURBINE</span><span class="asset-marker"></span><svg viewBox="0 0 210 125" aria-hidden="true"><ellipse cx="108" cy="118" rx="47" ry="4" fill="#e2ece5"/><path d="M20 50h29m-14 12h25m98-16h30m-22 14h24M38 91h17m110-8h17" stroke="#d8e6df" stroke-width="1.2" stroke-linecap="round"/><circle cx="107" cy="54" r="42" stroke="#e3ece6" stroke-dasharray="2 5" fill="none"/><path d="m105 56-3 60h12l-5-60" fill="#c8d9ce" stroke="#a5c0b0"/><path d="m107 52-9-41 3-7 5 8 5 39M109 54l37 20 2 7-9-3-32-20M105 56 72 80h-8l6-7 32-22" fill="#e8f0e9" stroke="#a2c0af" stroke-width="1.2" stroke-linejoin="round"/><circle cx="107" cy="54" r="5" fill="#93b69f" stroke="#fff" stroke-width="2"/><path d="M105 116v-10h5v10" fill="#b0c7b8"/></svg></div><div class="asset-meta"><div class="asset-name">WT-017 ${badge(dataLabel, count && !stale ? "green" : "")}</div><p class="asset-location">North Sea · Demonstration site</p><div class="definition-row"><span>Data quality</span><strong>${count ? Math.round((usable / count) * 100) + "% usable" : "No readings"}</strong></div><div class="definition-row"><span>Assessment</span><strong>${d?.incident ? "Fault recorded" : usable === 0 ? "No usable data" : d?.scenario.fault_assessed_at ? "No fault detected" : "Not assessed"}</strong></div><div class="definition-row"><span>Data source</span><strong>PostgreSQL · Synthetic</strong></div></div></section>`;
}
function workflow() {
  const d = S.detail;
  const stages = [
    ["Readings", !!d?.readings.length],
    ["Fault check", !!d?.scenario.fault_assessed_at],
    ["Review", d?.forecast?.review_status === "Reviewed"],
    ["Case", !!d?.case],
  ];
  const current = stages.findIndex((s) => !s[1]);
  return `<section class="card"><div class="card-header"><h2>Workflow progress</h2>${badge(d?.case?.status === "Resolved" ? "Resolved" : `${stages.filter((s) => s[1]).length} of 4`, d?.case?.status === "Resolved" ? "green" : "")}</div><div class="steps">${stages.map(([label, done], n) => `<div class="step ${done ? "done" : n === current ? "current" : ""}"><div class="step-indicator">${done ? "✓" : n + 1}</div>${label}</div>`).join("")}</div><p class="workflow-note">${d?.case ? "Case evidence is preserved. Maintenance outcomes are simulated." : !d?.incident && d?.scenario.fault_assessed_at ? "No current fault: a predictive case cannot be created." : "A case needs both a fault incident and a reviewed forecast."}</p></section>`;
}
function reviewQueue() {
  const pending = S.data.scenarios.filter((s) => s.review_status === "Pending");
  return `<section class="card"><div class="card-header"><h2>Forecast review queue <span class="subtitle-id">${pending.length}</span></h2><button class="text-button" data-action="nav" data-view="review">View reviews ↗</button></div>${
    pending.length
      ? pending
          .slice(0, 3)
          .map(
            (s) =>
              `<div class="review-item"><div class="review-symbol">${icon("spark")}</div><div><h3>${esc(s.title)} ${badge("Review needed", "amber")}</h3><p>WT-017 · 2 illustrative risks · ${dt(s.created_at)}</p></div>${button("Review forecast " + icon("arrow"), "open-review", "", `data-id="${s.id}"`)}</div>`,
          )
          .join("")
      : `<div class="empty inline"><h3>All forecasts have been reviewed</h3><p>Start a new demo scenario to explore the full workflow.</p></div>`
  }<div class="queue-note">${icon("info")}Simulated forecast · No real AI analysis · Human review required</div></section>`;
}
function filteredCases() {
  return S.data.cases.filter(
    (c) =>
      (S.filter === "All" || c.status === S.filter) &&
      `${c.id} ${c.title} ${c.turbine_id}`
        .toLowerCase()
        .includes(S.search.toLowerCase()),
  );
}
function caseRows() {
  const cases = filteredCases();
  return cases.length
    ? cases
        .map(
          (c) =>
            `<tr><td><button class="case-link mono" data-action="open-case" data-id="${c.id}">${esc(c.id)}</button><div class="cell-note">${esc(c.title)}</div></td><td>WT-017</td><td><span class="case-summary">${c.accepted_risks.length ? esc(c.accepted_risks[0].label) : "Current fault only"}</span><div class="cell-note">${c.accepted_risks.length} accepted predicted ${c.accepted_risks.length === 1 ? "risk" : "risks"}</div></td><td>${badge(c.status, c.status === "Open" ? "amber" : "green")}</td><td class="table-date">${dt(c.created_at)}</td><td><button class="row-button" data-action="open-case" data-id="${c.id}" aria-label="Open ${esc(c.id)}">↗</button></td></tr>`,
        )
        .join("")
    : `<tr><td colspan="6"><div class="empty inline"><h3>${S.search ? "No matching cases" : "No cases in this view"}</h3><p>${S.search ? "Try another case ID or scenario title." : "Review a forecast with a current fault to create a predictive case."}</p></div></td></tr>`;
}
function casesTable() {
  return `<section class="card"><div class="card-header"><h2>Predictive maintenance cases</h2>${button(icon("download") + "Export CSV", "export")}</div><div class="table-toolbar"><div class="tabs" aria-label="Case status">${["All", "Open", "Resolved"].map((t) => `<button data-action="case-filter" data-filter="${t}" class="${S.filter === t ? "active" : ""}" aria-pressed="${S.filter === t}">${t}<span>${S.data.cases.filter((c) => t === "All" || c.status === t).length}</span></button>`).join("")}</div><div class="table-actions"><label class="search-box">${icon("search")}<span class="sr-only">Search cases</span><input id="case-search" placeholder="Search cases…" value="${esc(S.search)}" type="search"></label></div></div><div class="table-wrap"><table><thead><tr><th>CASE</th><th>TURBINE</th><th>REVIEWED RISK</th><th>STATUS</th><th>CREATED</th><th><span class="sr-only">Open case</span></th></tr></thead><tbody id="case-rows">${caseRows()}</tbody></table></div><div class="table-footer"><span id="case-result-count">${filteredCases().length} ${filteredCases().length === 1 ? "case" : "cases"} shown</span><span>Seeded history and interactive demo records</span></div></section>`;
}
function overviewView() {
  return (
    metrics() +
    `<div class="main-grid">${chart()}${asset()}</div><div class="queue-grid">${reviewQueue()}${workflow()}</div>` +
    casesTable()
  );
}
function casesView() {
  return metrics() + casesTable();
}
function picker() {
  return `<div class="analysis-picker"><div><label for="scenario-picker">ANALYSIS WINDOW</label><select id="scenario-picker">${S.data.scenarios.map((s) => `<option value="${s.id}" ${s.id === S.detail?.scenario.id ? "selected" : ""}>${esc(s.title)} · ${dt(s.created_at)}</option>`).join("")}</select></div><div class="analysis-meta"><span class="source-label">${esc(S.detail?.scenario.source || "No data")}</span>${button(icon("refresh") + "Refresh", "refresh")}</div></div>`;
}
function gateCard() {
  const d = S.detail;
  const hasIncident = !!d?.incident;
  const reviewed = d?.forecast?.review_status === "Reviewed";
  return `<section class="card gate-card"><div class="aside-note"><h3>Case creation requirements</h3><div class="gate ${hasIncident ? "met" : ""}">${icon(hasIncident ? "check" : "clock")}<span>Current fault incident recorded</span></div><div class="gate ${reviewed ? "met" : ""}">${icon(reviewed ? "check" : "clock")}<span>Failure forecast reviewed</span></div>${d?.case ? button("Open predictive case " + icon("arrow"), "open-case", "light-green", `data-id="${d.case.id}"`) : button(icon("folder") + "Create predictive case", "create-case", "primary", hasIncident && reviewed ? "" : "disabled")}<p class="gate-caption">${d?.case ? "The case keeps the incident and reviewed forecast together." : "Both requirements apply to this analysis window. A forecast can be reviewed even when every risk is rejected."}</p><div class="callout">Better Maintenance is outside this prototype. Case handoff and maintenance outcomes are demonstrated without building work orders or assignments.</div></div></section>`;
}
function riskCard(r, editable) {
  const reviewDecision = S.detail.forecast?.review?.decisions.find(
    (d) => d.risk_id === r.id,
  )?.decision;
  const selected = S.decisions[r.id] || reviewDecision;
  return `<article class="risk-card"><div class="risk-card-header"><div><h3>${esc(r.label)}</h3><p class="risk-component">${esc(r.component)}</p></div>${badge(editable ? "Illustrative risk" : selected || "Not reviewed", editable ? "violet" : selected === "Accepted" ? "green" : "")}</div><div class="risk-numbers"><div class="risk-number"><strong>${Math.round(r.likelihood * 100)}<span>%</span></strong><small>Illustrative likelihood</small></div><div class="risk-number"><strong>${r.horizon_days}<span>days</span></strong><small>Illustrative horizon</small></div></div><p>${esc(r.explanation)}</p>${editable ? `<div class="decision-buttons" aria-label="Decision for ${esc(r.label)}"><button type="button" class="accept ${selected === "Accepted" ? "selected" : ""}" data-action="decision" data-risk="${r.id}" data-decision="Accepted" aria-pressed="${selected === "Accepted"}">${icon("check")}Accept risk</button><button type="button" class="reject ${selected === "Rejected" ? "selected" : ""}" data-action="decision" data-risk="${r.id}" data-decision="Rejected" aria-pressed="${selected === "Rejected"}">${icon("x")}Reject risk</button></div>` : ""}</article>`;
}
function noForecast() {
  const d = S.detail;
  const usable = d?.readings.some((r) => r.quality === "Usable");
  return `<section class="card"><div class="empty">${icon("spark")}<h3>No forecast in this window</h3><p>${usable ? "Generate an illustrated forecast from the usable evidence, then review its risks." : "A forecast needs usable readings. Start a new scenario or add data to an unassessed custom window."}</p>${button(icon("spark") + "Generate simulated forecast", "forecast", "violet", usable ? "" : "disabled")}${!usable ? `<div class="action-strip">${button("Inspect sensor history", "nav", "", `data-view="history"`)}</div>` : ""}</div></section>`;
}
function reviewView() {
  if (!S.detail)
    return `<div class="empty">No analysis window. Start a demo scenario.</div>`;
  const f = S.detail.forecast;
  let content = noForecast();
  if (f) {
    const editable =
      !S.detail.case && (f.review_status === "Pending" || S.editing);
    const record = f.review;
    content = `<section class="card"><div class="review-intro"><div class="review-symbol">${icon("spark")}</div><div><h2>Failure forecast <span class="subtitle-id mono">${esc(f.id)}</span></h2><p>Two independent risk illustrations for specialist review.</p><span class="simulation-label">Simulated forecast · No real AI analysis</span></div></div>${editable ? '<form id="review-form">' : ""}${f.risks.map((r) => riskCard(r, editable)).join("")}${editable ? `<div class="review-form-fields"><div class="field"><span>Reviewed by</span><input id="reviewer" name="reviewer" aria-label="Reviewed by" required minlength="2" maxlength="80" value="${esc(S.user.display_name)}" readonly><small>Saved as your signed-in account. Existing reviews retain their original identity.</small></div><label class="field"><span>Review note</span><textarea id="review-note" name="note" placeholder="Explain which evidence informed your decisions…" required minlength="3" maxlength="1000">${esc(record?.note || "")}</textarea></label><div class="form-actions"><span class="form-hint">Choose a decision for both risks.<br>Your decisions and note will be saved.</span><button type="submit" id="save-review" class="button primary" disabled>${icon("check")}Save forecast review</button></div></div></form>` : `<div class="review-record"><strong class="small">Forecast reviewed ${badge("Saved", "green")}</strong><p>${esc(record?.note)}</p><div class="meta">${esc(record?.reviewer)} · ${record ? dt(record.reviewed_at) : ""}</div>${!S.detail.case ? button("Edit review", "edit-review", "wide-button") : ""}</div>`}</section>`;
  }
  return (
    picker() +
    `<div class="section-columns"><div class="section-stack">${content}</div><div class="section-stack">${gateCard()}${evidenceCard()}</div></div>`
  );
}
function updateReviewSubmit() {
  const el = document.getElementById("save-review");
  if (!el) return;
  const f = S.detail?.forecast;
  const choices = f?.risks.every(
    (r) =>
      S.decisions[r.id] || f.review?.decisions.find((d) => d.risk_id === r.id),
  );
  el.disabled = !(
    choices &&
    document.getElementById("reviewer")?.value.trim().length >= 2 &&
    document.getElementById("review-note")?.value.trim().length >= 3
  );
}
function evidenceCard() {
  const d = S.detail;
  return `<section class="card"><div class="card-header"><h2>Evidence bundle</h2></div><div class="evidence-list"><div class="evidence-row">${icon("chart")}<div><strong>${d?.readings.length || 0} retained sensor ${d?.readings.length === 1 ? "reading" : "readings"}</strong><span>${d?.readings.filter((r) => r.quality === "Usable").length || 0} usable · Units: m/s</span></div></div><div class="evidence-row">${icon("alert")}<div><strong>${d?.incident ? "Current fault incident" : "No current fault incident"}</strong><span>${d?.incident ? esc(d.incident.id) : d?.scenario.fault_assessed_at ? "Assessment complete; rule did not trigger" : "Awaiting assessment"}</span></div></div><div class="evidence-row">${icon("spark")}<div><strong>${d?.forecast ? "Simulated failure forecast" : "No forecast generated"}</strong><span>${d?.forecast ? esc(d.forecast.model_version) : "Usable source data required"}</span></div></div><button class="text-button link-line" data-action="nav" data-view="history">Inspect source readings ↗</button></div></section>`;
}
function historyView() {
  if (!S.detail)
    return '<div class="empty">Start a demo scenario to inspect its readings.</div>';
  const d = S.detail;
  const frozen = d.scenario.fault_assessed_at || d.forecast;
  return (
    picker() +
    `<div class="main-grid">${chart()}${asset()}</div><div class="analysis-picker"><div><h3>Evidence actions</h3><p class="card-subtitle">${frozen ? "This evidence window is frozen. New measurements belong in a new window." : "Add readings, then run the two independent assessments."}</p></div><div class="action-strip">${button(icon("plus") + "Add reading", "reading", "", frozen ? "disabled" : "")}${button("Assess current faults", "assess", "", d.scenario.fault_assessed_at || !d.readings.some((r) => r.quality === "Usable") ? "disabled" : "")}${button(icon("spark") + "Generate forecast", "forecast", "violet", d.forecast || !d.readings.some((r) => r.quality === "Usable") ? "disabled" : "")}</div></div><section class="card"><div class="card-header"><h2>Retained sensor readings</h2>${badge(`${d.readings.length} ${d.readings.length === 1 ? "record" : "records"}`)}</div><div class="table-toolbar"><span class="muted small">Invalid readings are visible here and excluded from analysis.</span>${d.forecast ? button("Review forecast " + icon("arrow"), "nav", "", `data-view="review"`) : ""}</div><div class="table-wrap"><table><thead><tr><th>MEASURED AT · COPENHAGEN</th><th>SIGNAL</th><th>VALUE</th><th>QUALITY</th><th>REASON</th></tr></thead><tbody>${
      d.readings.length
        ? [...d.readings]
            .reverse()
            .map(
              (r) =>
                `<tr class="${r.quality === "Invalid" ? "reading-invalid" : ""}"><td>${dt(r.measured_at)}</td><td>Wind speed</td><td>${r.value === null ? "—" : r.value.toFixed(1)} m/s</td><td><i class="quality-dot ${r.quality === "Invalid" ? "invalid" : ""}"></i>${r.quality}</td><td class="small">${esc(r.reason || "Within synthetic input range")}</td></tr>`,
            )
            .join("")
        : '<tr><td colspan="5"><div class="empty">No readings yet. Add a synthetic reading to begin.</div></td></tr>'
    }</tbody></table></div></section>`
  );
}
function timeline(events) {
  const symbols = {
    "Sensor Readings Recorded": "chart",
    "Fault Incident Opened": "alert",
    "Current Faults Assessed": "check",
    "Failure Forecast Generated": "spark",
    "Failure Forecast Reviewed": "check",
    "Predictive Maintenance Case Created": "folder",
    "Maintenance Outcome Recorded": "file",
    "Predictive Case Resolved": "check",
  };
  return `<section class="card"><div class="card-header"><h2>Event timeline</h2>${badge(`${events.length} events`)}</div><div class="timeline">${events.map((e) => `<article class="timeline-item"><div class="timeline-symbol">${icon(symbols[e.name] || "clock")}</div><div class="timeline-content"><strong>${esc(e.name)}</strong><p>${esc(e.payload.reviewer || e.payload.external_reference || e.payload.source || e.payload.case_id || e.payload.forecast_id || e.payload.incident_id || (e.payload.count !== undefined ? `${e.payload.count} synthetic readings` : "Persisted domain event"))}${e.payload.simulated || e.payload.simulated_outcome ? " · Simulated" : ""}</p></div><time class="timeline-time" datetime="${e.occurred_at}">${dt(e.occurred_at)}</time></article>`).join("") || '<div class="empty inline">No events recorded.</div>'}</div></section>`;
}
function caseView() {
  const d = S.detail,
    c = d?.case;
  if (!c)
    return `<section class="card"><div class="empty">${icon("folder")}<h3>No case has been created in this window</h3><p>Review a forecast with a current fault before creating a predictive case.</p>${button("Review forecast", "nav", "primary", `data-view="review"`)}</div></section>`;
  const review = d.forecast.review;
  return `<div class="section-stack"><section class="card"><div class="case-banner"><div class="case-icon">${icon("folder")}</div><div><h2>${esc(d.scenario.title)}</h2><p class="mono">${esc(c.id)} · WT-017 · ${esc(d.scenario.source)}</p></div>${badge(c.status, c.status === "Open" ? "amber" : "green")}</div><div class="case-facts"><div><label>CREATED</label><strong>${dt(c.created_at)}</strong></div><div><label>FORECAST REVIEWER</label><strong>${esc(review.reviewer)}</strong></div><div><label>HANDOFF</label><strong>${c.status === "Resolved" ? "Simulated outcome received" : "Ready · No service connected"}</strong></div></div></section><div class="section-columns"><div class="section-stack"><section class="card"><div class="card-header"><h2>Current fault & reviewed risks</h2>${badge("Evidence preserved", "green")}</div><div class="card-body"><div class="risk-card-header"><div><h3>High-wind incident</h3><p class="card-subtitle">${esc(d.incident.id)} · ${d.incident.evidence.length} supporting readings</p></div>${badge(`Peak ${d.incident.peak.toFixed(1)} m/s`, "amber")}</div><p class="help-inline">${esc(d.incident.summary)} This rule and its threshold are illustrative.</p></div>${d.forecast.risks.map((r) => riskCard(r, false)).join("")}<div class="review-record"><strong class="small">Specialist review note</strong><p>${esc(review.note)}</p><div class="meta">${esc(review.reviewer)} · ${dt(review.reviewed_at)}</div></div></section>${timeline(d.events)}</div><div class="section-stack">${outcomeCard()}${evidenceCard()}</div></div></div>`;
}
function outcomeCard() {
  const d = S.detail;
  return `<section class="card"><div class="aside-note"><h3>External maintenance outcome</h3>${badge("Simulation only", "violet")}<p class="gate-caption">${d.case.status === "Resolved" ? "The case was resolved using a clearly simulated external outcome. No real repair or verification is claimed." : "Demonstrate a result arriving from outside Predictive Maintenance. Better Maintenance is not implemented."}</p>${d.case.status === "Open" ? button(icon("plus") + "Simulate maintenance outcome", "outcome", "primary wide-button") : badge("Case resolved", "green")}<p class="help-inline">Resolution requires all required work complete and verification passed.</p></div>${d.outcomes.map((o) => `<div class="outcome-record"><span class="mono">${esc(o.external_reference)}</span> ${badge(o.all_work_complete && o.verification === "Passed" ? "Successful" : "Further work needed", o.all_work_complete && o.verification === "Passed" ? "green" : "amber")}<p>${esc(o.note)}</p><p>Required work: ${o.all_work_complete ? "Complete" : "Incomplete"} · Verification: ${esc(o.verification)}</p><p>${esc(o.evidence_reference)} · ${dt(o.created_at)} · Simulated</p></div>`).join("")}</section>`;
}
function activityView() {
  return `<div class="section-stack">${timeline(S.data.events)}<p class="small muted">The latest 30 persisted events across this prototype. Case pages preserve their complete timeline.</p></div>`;
}
function modal(content) {
  document.getElementById("modal-content").innerHTML = content;
  const el = document.getElementById("modal");
  if (!el.open) el.showModal();
}
function modalHeader(title, description) {
  return `<div class="modal-heading"><h2>${title}</h2><button class="icon-button" data-action="close" aria-label="Close dialog">${icon("x")}</button></div><p class="modal-description">${description}</p>`;
}
function closeModal() {
  document.getElementById("modal").close();
  document.getElementById("modal-content").innerHTML = "";
}
function newModal() {
  S.newKind = "fault";
  modal(
    `<div class="modal-body">${modalHeader("Start a demo scenario", "Create a separate synthetic evidence window for WT-017. Existing cases and history are preserved.")}<form id="scenario-form"><div class="scenario-cards">${[
      [
        "fault",
        "wind",
        "High-wind event",
        "Fault incident + forecast awaiting your review.",
      ],
      [
        "normal",
        "check",
        "Normal operation",
        "Usable readings with no current fault.",
      ],
      [
        "invalid",
        "alert",
        "Unusable telemetry",
        "Retained invalid readings; excluded from analysis.",
      ],
      [
        "empty",
        "plus",
        "Custom window",
        "Add your own synthetic sensor readings.",
      ],
    ]
      .map(
        ([key, symbol, label, description]) =>
          `<button type="button" class="scenario-choice ${key === "fault" ? "active" : ""}" data-action="scenario-choice" data-kind="${key}" aria-pressed="${key === "fault"}">${icon(symbol)}<strong>${label}</strong><small>${description}</small></button>`,
      )
      .join(
        "",
      )}</div><label class="field"><span>Scenario title <span class="muted">(optional)</span></span><input name="title" maxlength="100" placeholder="e.g. Group walkthrough · Wind gust"></label><p class="help-inline">Demo fault rule: wind speed strictly above 28.0 m/s. Forecasts are fixed illustrations, not real AI analysis.</p><div id="modal-error" role="alert" class="small"></div><div class="modal-footer">${button("Cancel", "close")}<button type="submit" class="button primary">${icon("plus")}Create scenario</button></div></form></div>`,
  );
}
function outcomeModal() {
  modal(
    `<div class="modal-body">${modalHeader("Simulate a maintenance outcome", "This records a demo result from an external system. It does not perform actual maintenance or verification.")}<span class="simulation-label">SIMULATED EXTERNAL OUTCOME</span><form id="outcome-form"><label class="field"><span>Demonstration result</span><select name="result"><option value="success">Successful · All work complete, verification passed</option><option value="failed">Failed verification · Case stays open</option><option value="incomplete">Incomplete work · Case stays open</option></select></label><div class="form-grid"><label class="field"><span>External outcome reference</span><input name="external_reference" required minlength="3" maxlength="100" value="DEMO-${Date.now()}"></label><label class="field"><span>Evidence reference</span><input name="evidence_reference" required minlength="3" maxlength="200" value="DEMO-EVIDENCE-${Date.now()}"></label></div><label class="field"><span>Outcome note</span><textarea name="note" required minlength="3" maxlength="1000">Simulated external maintenance result for the prototype walkthrough. No real turbine was repaired or verified.</textarea></label><div id="modal-error" role="alert" class="small"></div><div class="modal-footer">${button("Cancel", "close")}<button type="submit" class="button primary">Record simulated outcome</button></div></form></div>`,
  );
}
function readingModal() {
  modal(
    `<div class="modal-body">${modalHeader("Add a synthetic reading", "The reading is persisted in this custom evidence window. Missing or out-of-range values are retained as Invalid.")}<form id="reading-form"><div class="form-grid"><label class="field"><span>Wind speed (m/s)</span><input type="number" name="value" step="any" placeholder="e.g. 28.1"><small>Leave blank to demonstrate a missing value.</small></label><label class="field"><span>Measured at (UTC)</span><input type="datetime-local" name="measured_at" required value="${new Date().toISOString().slice(0, 16)}"></label></div><label class="field"><span>Source quality</span><select name="quality"><option>Usable</option><option>Invalid</option></select></label><label class="field"><span>Quality note (optional)</span><input name="reason" maxlength="200" placeholder="e.g. Synthetic sensor calibration error"></label><div id="modal-error" role="alert" class="small"></div><div class="modal-footer">${button("Cancel", "close")}<button type="submit" class="button primary">Save synthetic reading</button></div></form></div>`,
  );
}
function aboutModal() {
  modal(
    `<div class="modal-body">${modalHeader("A clear path from data to decision", "Aeris demonstrates only the Predictive Maintenance bounded context from your group’s model.")}<ol class="about-list"><li>Record synthetic sensor readings and assess a small current-fault rule.</li><li>Review a clearly simulated forecast. Accept or reject each risk.</li><li>Create a predictive case when both a fault and a reviewed forecast exist.</li><li>Inspect the case and record a simulated external maintenance outcome.</li></ol><p class="modal-description">The API, decisions, persistence and event history really work. The forecasts are fixed illustrations. Seeded example history is labelled; no real turbine, AI inference, work order or repair is represented.</p><div class="callout">Data stays in this prototype’s PostgreSQL database and is accessed through the application API. The dashboard uses no external fonts, trackers or chart services.</div><div class="modal-footer">${button("Back to workspace", "close", "primary")}</div></div>`,
  );
}
function exportCases() {
  const rows = [
    [
      "Case ID",
      "Turbine",
      "Scenario",
      "Status",
      "Created",
      "Accepted predicted risks",
    ],
    ...filteredCases().map((c) => [
      c.id,
      c.turbine_id,
      c.title,
      c.status,
      c.created_at,
      c.accepted_risks.length,
    ]),
  ];
  const csv = rows
    .map((row) =>
      row
        .map(
          (v) =>
            '"' +
            String(v)
              .replace(/^[=+\-@\t\r]/, "'$&")
              .replace(/"/g, '""') +
            '"',
        )
        .join(","),
    )
    .join("\r\n");
  const url = URL.createObjectURL(
    new Blob(["\ufeff" + csv], { type: "text/csv;charset=utf-8" }),
  );
  const a = document.createElement("a");
  a.href = url;
  a.download = "aeris-predictive-cases.csv";
  a.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
  toast("Case list exported.");
}

document.addEventListener("click", (event) => {
  const el = event.target.closest("[data-action]");
  if (!el || el.disabled) return;
  const action = el.dataset.action;
  if (["logout", "account", "user-new", "user-edit", "user-password"].includes(action)) {
    if (action === "account") { if (S.user.must_change_password) { render(); return; } modal(`<div class="modal-body">${modalHeader("Change password", "Sign in again after changing your password. All your other sessions will end.")}${passwordForm()}</div>`); return; }
    if (action === "user-new") { userModal(); return; }
    if (action === "user-edit") { userModal(S.users.find(u => u.id === el.dataset.userId)); return; }
    if (action === "user-password") { resetPasswordModal(S.users.find(u => u.id === el.dataset.userId)); return; }
    act(async () => { await accountWrite("/api/auth/logout", {}); signedOut(); }, el);
    return;
  }
  if (action === "nav") {
    if (el.dataset.view === "users") {
      act(async () => { await loadUsers(); navigate("users"); }, el); return;
    }
    navigate(el.dataset.view);
    return;
  }
  if (action === "menu") {
    document.body.classList.toggle("nav-open");
    return;
  }
  if (action === "about") {
    aboutModal();
    return;
  }
  if (action === "new") {
    newModal();
    return;
  }
  if (action === "close") {
    closeModal();
    return;
  }
  if (action === "outcome") {
    outcomeModal();
    return;
  }
  if (action === "reading") {
    readingModal();
    return;
  }
  if (action === "range") {
    S.range = Number(el.dataset.range);
    render();
    return;
  }
  if (action === "case-filter") {
    S.filter = el.dataset.filter;
    render();
    return;
  }
  if (action === "export") {
    exportCases();
    return;
  }
  if (action === "edit-review") {
    S.editing = true;
    S.decisions = Object.fromEntries(
      S.detail.forecast.review.decisions.map((d) => [d.risk_id, d.decision]),
    );
    render();
    return;
  }
  if (action === "decision") {
    S.decisions[el.dataset.risk] = el.dataset.decision;
    document
      .querySelectorAll(`[data-risk="${el.dataset.risk}"]`)
      .forEach((b) => {
        const selected = b.dataset.decision === el.dataset.decision;
        b.classList.toggle("selected", selected);
        b.setAttribute("aria-pressed", selected);
      });
    updateReviewSubmit();
    return;
  }
  if (action === "scenario-choice") {
    S.newKind = el.dataset.kind;
    document.querySelectorAll(".scenario-choice").forEach((b) => {
      const selected = b.dataset.kind === S.newKind;
      b.classList.toggle("active", selected);
      b.setAttribute("aria-pressed", selected);
    });
    return;
  }
  act(async () => {
    if (action === "refresh") {
      await load();
      toast("Workspace refreshed from the database.");
    }
    if (action === "open-review") {
      S.detail = await api(`/api/scenarios/${el.dataset.id}`);
      navigate("review");
    }
    if (action === "open-case") {
      S.detail = await api(`/api/cases/${el.dataset.id}`);
      navigate("case");
    }
    if (["assess", "forecast", "create-case"].includes(action)) {
      const suffix = action === "create-case" ? "case" : action;
      await mutate(`/api/scenarios/${S.detail.scenario.id}/${suffix}`, {
        expected_version: S.detail.scenario.version,
      });
      await load();
      if (action === "create-case") navigate("case");
      if (action === "forecast") navigate("review");
      toast(
        action === "assess"
          ? "Current-fault assessment saved."
          : action === "forecast"
            ? "Simulated forecast generated."
            : "Predictive case created.",
      );
    }
  }, el);
});
document.addEventListener("input", (event) => {
  if (event.target.id === "case-search") {
    S.search = event.target.value;
    document.getElementById("case-rows").innerHTML = caseRows();
    document.getElementById("case-result-count").textContent =
      `${filteredCases().length} cases shown`;
  }
  if (["reviewer", "review-note"].includes(event.target.id))
    updateReviewSubmit();
});
document.addEventListener("change", (event) => {
  if (event.target.id === "scenario-picker")
    act(async () => {
      S.detail = await api(`/api/scenarios/${event.target.value}`);
      S.editing = false;
      S.decisions = {};
      render();
    });
});
document.addEventListener("submit", (event) => {
  const form = event.target;
  if (
    ![
      "scenario-form",
      "review-form",
      "outcome-form",
      "reading-form",
      "login-form",
      "password-form",
      "user-create-form",
      "user-edit-form",
      "user-password-form",
    ].includes(form.id)
  )
    return;
  event.preventDefault();
  const f = Object.fromEntries(new FormData(form));
  const submit = form.querySelector('[type="submit"]');
  act(async () => {
    if (form.id === "scenario-form") {
      const payload = { kind: S.newKind, prepare: true };
      if (f.title.trim()) payload.title = f.title.trim();
      const result = await mutate("/api/scenarios", payload);
      closeModal();
      await load(result.scenario_id);
      navigate(
        S.newKind === "empty" || S.newKind === "invalid" ? "history" : "review",
      );
      toast("New synthetic scenario saved. Existing history preserved.");
    }
    if (form.id === "review-form") {
      const decisions = S.detail.forecast.risks.map((r) => ({
        risk_id: r.id,
        decision:
          S.decisions[r.id] ||
          S.detail.forecast.review?.decisions.find((d) => d.risk_id === r.id)
            ?.decision,
      }));
      await mutate(
        `/api/scenarios/${S.detail.scenario.id}/review`,
        {
          expected_version: S.detail.scenario.version,
          note: f.note,
          decisions,
        },
        "PUT",
      );
      await load();
      toast("Forecast review saved.");
    }
    if (form.id === "outcome-form") {
      const fields = {
        expected_version: S.detail.scenario.version,
        simulated: true,
        external_reference: f.external_reference,
        evidence_reference: f.evidence_reference,
        note: f.note,
        all_work_complete: f.result !== "incomplete",
        verification: f.result === "failed" ? "Failed" : "Passed",
      };
      const result = await mutate(
        `/api/cases/${S.detail.case.id}/outcomes`,
        fields,
      );
      closeModal();
      await load();
      toast(
        result.status === "Resolved"
          ? "Case resolved with a simulated external outcome."
          : "Simulated outcome recorded. The case remains open.",
      );
    }
    if (form.id === "reading-form") {
      await mutate(`/api/scenarios/${S.detail.scenario.id}/readings`, {
        expected_version: S.detail.scenario.version,
        value: f.value === "" ? null : Number(f.value),
        measured_at: new Date(f.measured_at + "Z").toISOString(),
        quality: f.quality,
        reason: f.reason,
      });
      closeModal();
      await load();
      toast("Synthetic reading recorded.");
    }
    if (form.id === "login-form") {
      const session = await accountWrite("/api/auth/login", { username: f.username, password: f.password });
      form.reset();
      S.user = session.user; S.csrf = session.csrf_token;
      await load();
    }
    if (form.id === "password-form") {
      if (f.new_password !== f.confirm_password) throw new Error("The new passwords do not match.");
      await accountWrite("/api/auth/password", { current_password: f.current_password, new_password: f.new_password });
      form.reset(); closeModal(); signedOut("Password changed. Sign in with your new password.");
    }
    if (form.id === "user-create-form") {
      await accountWrite("/api/admin/users", { username: f.username, display_name: f.display_name, role: f.role, password: f.password });
      form.reset(); closeModal(); await loadUsers(); render(); toast("User created. Supply their temporary password privately.");
    }
    if (form.id === "user-edit-form") {
      await accountWrite(`/api/admin/users/${form.dataset.userId}`, { display_name: f.display_name, role: f.role, active: f.active === "on", expected_version: Number(form.dataset.version) }, "PATCH");
      closeModal(); await load(); toast("User updated. Their existing sessions have ended.");
    }
    if (form.id === "user-password-form") {
      await accountWrite(`/api/admin/users/${form.dataset.userId}/password`, { password: f.password, expected_version: Number(form.dataset.version) });
      form.reset(); closeModal(); await loadUsers(); render(); toast("Temporary password set. Existing sessions have ended.");
    }
  }, submit);
});
document.getElementById("modal").addEventListener("click", (event) => {
  if (event.target === event.currentTarget) {
    const rect = event.currentTarget.getBoundingClientRect();
    if (
      event.clientX < rect.left ||
      event.clientX > rect.right ||
      event.clientY < rect.top ||
      event.clientY > rect.bottom
    )
      closeModal();
  }
});
window.addEventListener("hashchange", () => {
  const next = location.hash.slice(1);
  if (["overview", "history", "review", "cases", "activity"].includes(next))
    navigate(next);
});
// Remove the former shared-token value; individual sessions use HttpOnly cookies.
sessionStorage.removeItem("aeris-token");
(async () => {
  try {
    await load();
    const next = location.hash.slice(1);
    if (["history", "review", "cases", "activity"].includes(next) && !S.user.must_change_password) navigate(next);
  } catch (error) {
    if (error.status === 401) signedOut();
    else { signedOut(error.message); connection(false); }
  }
})();
document.addEventListener("click", (event) => {
  if (event.target.closest('[data-action="retry-start"]')) location.reload();
});

function profile() {
  const u = S.user;
  document.getElementById("profile").innerHTML = u
    ? `<span class="avatar">${esc(u.display_name.slice(0, 2).toUpperCase())}</span><div class="profile-identity"><button class="text-button" data-action="account">${esc(u.display_name)}</button><small>${u.role === "admin" ? "Administrator" : "Technician · Maintenance specialist"}</small></div><button class="icon-button" data-action="logout" aria-label="Sign out" title="Sign out">${icon("arrow")}</button>`
    : `<span class="avatar">A</span><div><strong>Aeris workspace</strong><small>Sign in to continue</small></div>`;
}
function signedOut(message = "") {
  S.user = null; S.csrf = ""; S.data = null; S.detail = null;
  S.users = []; S.accountEvents = []; S.pending.clear(); S.view = "overview";
  closeModal(); profile(); loginView(message);
}
function loginView(message = "") {
  document.getElementById("navigation").innerHTML = "";
  document.getElementById("connection").textContent = "Sign-in required";
  document.getElementById("main").innerHTML = `<div class="auth-shell"><section class="card auth-card"><div class="eyebrow">AERIS WORKSPACE</div><h1>Welcome back</h1><p>Sign in to review turbine evidence and predictive maintenance cases.</p><form id="login-form"><label class="field"><span>Username</span><input name="username" autocomplete="username" required minlength="3" maxlength="64" autofocus></label><label class="field"><span>Password</span><input type="password" name="password" autocomplete="current-password" required maxlength="128"></label><div id="modal-error" class="auth-error" role="alert">${esc(message)}</div><button type="submit" class="button primary wide-button">Sign in</button></form><p class="help-inline">Need access? Ask your administrator for an individual account.</p><div class="callout">Predictive Maintenance prototype · Synthetic data and simulated forecasts.</div></section></div>`;
}
function passwordForm() {
  return `<form id="password-form"><label class="field"><span>Current password</span><input type="password" name="current_password" autocomplete="current-password" required maxlength="128"></label><label class="field"><span>New password</span><input type="password" name="new_password" autocomplete="new-password" required minlength="15" maxlength="128"><small>Use 15–128 characters. A long, unique passphrase works well.</small></label><label class="field"><span>Confirm new password</span><input type="password" name="confirm_password" autocomplete="new-password" required minlength="15" maxlength="128"></label><div id="modal-error" class="auth-error" role="alert"></div><button class="button primary" type="submit">Change password</button></form>`;
}
async function accountWrite(path, fields, method = "POST") {
  return api(path, { method, headers: { "Content-Type": "application/json" }, body: JSON.stringify(fields) });
}
async function loadUsers() {
  const [users, audit] = await Promise.all([api("/api/admin/users"), api("/api/admin/audit")]);
  S.users = users.users; S.accountEvents = audit.events;
}
function usersView() {
  if (S.user.role !== "admin") return "";
  return `<div class="section-stack"><section class="card"><div class="card-header"><div><h2>People & access</h2><p class="card-subtitle">${S.users.filter(u => u.active).length} active accounts · Two application roles</p></div>${button(icon("plus") + "Add user", "user-new", "primary")}</div><div class="table-scroll"><table><thead><tr><th>USER</th><th>ROLE</th><th>STATUS</th><th>PASSWORD</th><th>ACTIONS</th></tr></thead><tbody>${S.users.map(u => `<tr><td><strong>${esc(u.display_name)}</strong><div class="muted small">${esc(u.username)}${u.id === S.user.id ? " · You" : ""}</div></td><td>${badge(u.role === "admin" ? "Admin" : "Technician", u.role === "admin" ? "violet" : "green")}</td><td>${badge(u.active ? "Active" : "Inactive", u.active ? "green" : "")}</td><td>${u.must_change_password ? "Change required" : "Ready"}</td><td><div class="action-strip">${button("Edit", "user-edit", "", `data-user-id="${esc(u.id)}"`)}${u.id !== S.user.id ? button("Reset password", "user-password", "", `data-user-id="${esc(u.id)}"`) : ""}</div></td></tr>`).join("")}</tbody></table></div><div class="card-body"><p class="help-inline">Technicians can use the maintenance workspace. Admins can also manage accounts. Changes end that user's current sessions; deactivation preserves their recorded evidence.</p></div></section><section class="card"><div class="card-header"><h2>Account administration history</h2>${badge("Latest 100")}</div><div class="card-body account-audit">${S.accountEvents.map(e => `<div class="definition-row"><div><strong>${esc(e.action)}</strong><p class="small muted">${esc(e.actor_name || "Initial host setup")} → ${esc(e.target_username)}</p></div><time datetime="${esc(e.occurred_at)}">${dt(e.occurred_at)}</time></div>`).join("") || '<p class="muted">No account changes yet.</p>'}</div></section></div>`;
}
function userModal(user = null) {
  const editing = Boolean(user);
  modal(`<div class="modal-body">${modalHeader(editing ? "Edit user" : "Add user", editing ? "Changes end this user's existing sessions. Accounts are deactivated rather than deleted." : "Create an individual account. Share the temporary password privately; they must change it on first sign-in.")}<form id="${editing ? "user-edit-form" : "user-create-form"}" ${editing ? `data-user-id="${esc(user.id)}" data-version="${user.version}"` : ""}><label class="field"><span>Display name</span><input name="display_name" required minlength="2" maxlength="80" value="${esc(user?.display_name || "")}"></label>${editing ? `<p class="help-inline">Username: ${esc(user.username)}</p>` : '<label class="field"><span>Username</span><input name="username" autocomplete="off" required minlength="3" maxlength="64" pattern="[a-z0-9][a-z0-9._-]{2,63}"><small>Lowercase letters, numbers, dots, hyphens and underscores.</small></label>'}<label class="field"><span>Role</span><select name="role"><option value="technician" ${user?.role !== "admin" ? "selected" : ""}>Technician · Maintenance specialist</option><option value="admin" ${user?.role === "admin" ? "selected" : ""}>Admin · Full workspace and user management</option></select></label>${editing ? `<label class="account-toggle"><input type="checkbox" name="active" ${user.active ? "checked" : ""}>Account active</label>` : '<label class="field"><span>Temporary password</span><input type="password" name="password" autocomplete="new-password" required minlength="15" maxlength="128"><small>15–128 characters. This value is not saved in the browser.</small></label>'}<div id="modal-error" class="auth-error" role="alert"></div><div class="modal-footer">${button("Cancel", "close")}<button type="submit" class="button primary">${editing ? "Save user" : "Create user"}</button></div></form></div>`);
}
function resetPasswordModal(user) {
  modal(`<div class="modal-body">${modalHeader("Reset password", `Set a new temporary password for ${user.display_name}. Their existing sessions will end and they must choose a new password on sign-in.`)}<form id="user-password-form" data-user-id="${esc(user.id)}" data-version="${user.version}"><label class="field"><span>New temporary password</span><input type="password" name="password" autocomplete="new-password" required minlength="15" maxlength="128"></label><div id="modal-error" class="auth-error" role="alert"></div><div class="modal-footer">${button("Cancel", "close")}<button type="submit" class="button primary">Reset password</button></div></form></div>`);
}
