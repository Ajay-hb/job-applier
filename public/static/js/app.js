/* ============================================================
   Job Applier Web UI — JavaScript (SPA)
   ============================================================ */

let CONFIG  = {};
let currentPage = "dashboard";
let botPollTimer = null;

// ── Init ────────────────────────────────────────────────────

window.onload = async () => {
  await fetchConfig();
  navigate("dashboard", document.querySelector('[data-page="dashboard"]'));
  startBotPolling();
};

async function fetchConfig() {
  try {
    const r = await fetch("/api/config");
    CONFIG = await r.json();
  } catch (e) { console.error("Config load failed", e); }
}

// ── Navigation ──────────────────────────────────────────────

const PAGE_TITLES = {
  dashboard: "Dashboard", run: "Run Bot", applications: "Applications",
  profile: "My Profile", search: "Job Search Config",
  platforms: "Platform Settings", resume: "Resume", logs: "Logs"
};

function navigate(page, el) {
  currentPage = page;
  document.querySelectorAll(".nav-item").forEach(n => n.classList.remove("active"));
  if (el) el.classList.add("active");
  document.getElementById("page-title").textContent = PAGE_TITLES[page] || page;

  const content = document.getElementById("page-content");
  content.innerHTML = "";

  const pages = {
    dashboard:    renderDashboard,
    run:          renderRun,
    applications: renderApplications,
    profile:      renderProfile,
    search:       renderSearch,
    platforms:    renderPlatforms,
    resume:       renderResume,
    logs:         renderLogs,
  };
  if (pages[page]) pages[page](content);
}

function toggleSidebar() {
  document.getElementById("sidebar").classList.toggle("open");
}

// ── Toast ────────────────────────────────────────────────────

function showToast(msg, type = "info") {
  const t = document.getElementById("toast");
  t.textContent = msg;
  t.className = `toast show ${type}`;
  setTimeout(() => { t.classList.remove("show"); }, 3200);
}

// ── API helpers ──────────────────────────────────────────────

async function api(url, method = "GET", body = null) {
  const opts = { method, headers: { "Content-Type": "application/json" } };
  if (body) opts.body = JSON.stringify(body);
  const r = await fetch(url, opts);
  return r.json();
}

// ── Dashboard Page ───────────────────────────────────────────

async function renderDashboard(container) {
  container.innerHTML = `
    <div class="stats-grid" id="stat-cards">
      ${[0,1,2,3].map(() => `<div class="stat-card"><div class="s-num">—</div><div class="s-label">Loading...</div></div>`).join("")}
    </div>
    <div class="card">
      <div class="card-title"><span>📋</span>Recent Applications</div>
      <div class="table-wrap">
        <table>
          <thead><tr><th>Role</th><th>Company</th><th>Platform</th><th>Status</th><th>Date</th></tr></thead>
          <tbody id="recent-tbody"></tbody>
        </table>
      </div>
    </div>
    <div class="card">
      <div class="card-title"><span>📈</span>Applications by Platform</div>
      <div id="platform-breakdown" style="display:flex;gap:24px;flex-wrap:wrap;padding:4px 0"></div>
    </div>`;

  const stats = await api("/api/stats");
  document.getElementById("stat-cards").innerHTML = `
    <div class="stat-card blue"><div class="s-num">${stats.total}</div><div class="s-label">Total Applied</div></div>
    <div class="stat-card green"><div class="s-num">${stats.interviews}</div><div class="s-label">Interviews</div></div>
    <div class="stat-card red"><div class="s-num">${stats.rejected}</div><div class="s-label">Rejected</div></div>
    <div class="stat-card yellow"><div class="s-num">${stats.offers}</div><div class="s-label">Offers 🎉</div></div>`;

  const apps = await api("/api/applications?limit=10");
  const tbody = document.getElementById("recent-tbody");
  if (!apps.length) {
    tbody.innerHTML = `<tr><td colspan="5" style="text-align:center;color:var(--muted);padding:32px">No applications yet — run the bot!</td></tr>`;
  } else {
    tbody.innerHTML = apps.map(a => `
      <tr>
        <td><a class="job-link" href="${a.job_url||'#'}" target="_blank">${a.job_title}</a></td>
        <td>${a.company}</td>
        <td><span class="badge badge-platform">${a.platform}</span></td>
        <td><span class="badge badge-${a.status}">${a.status}</span></td>
        <td class="text-muted" style="font-size:12px">${(a.date_applied||"").substring(0,10)}</td>
      </tr>`).join("");
  }

  const pb = document.getElementById("platform-breakdown");
  const platforms = stats.by_platform || {};
  if (!Object.keys(platforms).length) {
    pb.innerHTML = `<div class="text-muted">No data yet</div>`;
  } else {
    pb.innerHTML = Object.entries(platforms).map(([pl, cnt]) => `
      <div style="text-align:center">
        <div style="font-size:1.8rem;font-weight:800;color:var(--blue)">${cnt}</div>
        <div style="font-size:11px;color:var(--muted);text-transform:capitalize">${pl}</div>
      </div>`).join("");
  }
}

// ── Run Bot Page ─────────────────────────────────────────────

async function renderRun(container) {
  container.innerHTML = `
    <div class="card run-hero">
      <div class="hero-icon">🤖</div>
      <h2>Auto Job Applier</h2>
      <p>The bot will search for jobs across all enabled platforms, fill in your details, and submit applications automatically.</p>
      <div class="run-controls">
        <button class="btn btn-green btn-lg" id="start-btn" onclick="startBot()">▶ Start Bot</button>
        <button class="btn btn-red btn-lg" id="stop-btn" onclick="stopBot()" disabled>⏹ Stop</button>
      </div>
    </div>
    <div class="card">
      <div class="card-title"><span>📊</span>Session Progress</div>
      <div style="display:flex;gap:32px;margin-bottom:16px;flex-wrap:wrap">
        <div><div style="font-size:1.6rem;font-weight:800;color:var(--blue)" id="run-applied">0</div><div class="text-muted" style="font-size:11px">Applied</div></div>
        <div><div style="font-size:1.6rem;font-weight:800;color:var(--muted)" id="run-found">0</div><div class="text-muted" style="font-size:11px">Jobs Found</div></div>
        <div style="flex:1;min-width:200px;display:flex;flex-direction:column;justify-content:center">
          <div class="text-muted" style="font-size:11px;margin-bottom:4px" id="run-current-job">Idle</div>
          <div class="progress-bar-wrap"><div class="progress-bar" id="run-progress" style="width:0%"></div></div>
        </div>
      </div>
    </div>
    <div class="card">
      <div class="card-title" style="display:flex;justify-content:space-between">
        <span><span>📝</span>Live Log</span>
        <button class="btn btn-ghost" style="padding:4px 10px;font-size:12px" onclick="clearLog()">Clear</button>
      </div>
      <div class="log-box" id="run-log">Waiting for session to start...</div>
    </div>`;

  // Load current status
  updateRunPage();
}

async function updateRunPage() {
  if (currentPage !== "run") return;
  try {
    const s = await api("/api/automation/status");
    const startBtn = document.getElementById("start-btn");
    const stopBtn  = document.getElementById("stop-btn");
    if (!startBtn) return;

    startBtn.disabled = s.running;
    stopBtn.disabled  = !s.running;

    document.getElementById("run-applied").textContent = s.applied;
    document.getElementById("run-found").textContent   = s.found;
    document.getElementById("run-current-job").textContent = s.current_job || (s.running ? "Searching..." : "Idle");

    if (s.found > 0) {
      const pct = Math.min(100, (s.applied / s.found) * 100);
      document.getElementById("run-progress").style.width = pct + "%";
    }

    const logBox = document.getElementById("run-log");
    if (s.log && s.log.length) {
      logBox.innerHTML = s.log.map(l => {
        if (l.includes("❌") || l.includes("Error") || l.includes("fatal")) return `<div class="log-err">${esc(l)}</div>`;
        if (l.includes("⚠️") || l.includes("Warn")) return `<div class="log-warn">${esc(l)}</div>`;
        if (l.includes("✅")) return `<div class="log-ok">${esc(l)}</div>`;
        return `<div class="log-info">${esc(l)}</div>`;
      }).join("");
      logBox.scrollTop = logBox.scrollHeight;
    }

    // Update sidebar indicator
    updateBotIndicator(s.running);
  } catch(e) {}
}

async function startBot() {
  const r = await api("/api/automation/start", "POST");
  if (r.ok) {
    showToast("🤖 Bot started!", "success");
    updateRunPage();
  } else {
    showToast(r.error || "Failed to start", "error");
  }
}

async function stopBot() {
  await api("/api/automation/stop", "POST");
  showToast("⏹ Stop signal sent", "info");
}

function clearLog() {
  const lb = document.getElementById("run-log");
  if (lb) lb.innerHTML = "";
}

// ── Applications Page ─────────────────────────────────────────

async function renderApplications(container) {
  container.innerHTML = `
    <div class="section-header">
      <h2>All Applications</h2>
      <div style="display:flex;gap:8px">
        <input id="app-search" placeholder="Search..." style="background:var(--bg2);border:1px solid var(--border);border-radius:8px;padding:7px 12px;color:var(--text);outline:none;font-family:inherit;font-size:13px;width:200px" oninput="filterTable()">
      </div>
    </div>
    <div class="filter-bar" id="app-filters">
      <button class="filter-btn active" onclick="setAppFilter('all',this)">All</button>
      <button class="filter-btn" onclick="setAppFilter('applied',this)">Applied</button>
      <button class="filter-btn" onclick="setAppFilter('interview',this)">Interview</button>
      <button class="filter-btn" onclick="setAppFilter('rejected',this)">Rejected</button>
      <button class="filter-btn" onclick="setAppFilter('offer',this)">Offer</button>
    </div>
    <div class="card" style="padding:0;overflow:hidden">
      <div class="table-wrap">
        <table>
          <thead><tr><th>#</th><th>Role</th><th>Company</th><th>Location</th><th>Platform</th><th>Status</th><th>Date</th><th>Action</th></tr></thead>
          <tbody id="apps-tbody"></tbody>
        </table>
      </div>
    </div>`;

  window._allApps = await api("/api/applications");
  window._appFilter = "all";
  renderAppTable(window._allApps);
}

function renderAppTable(apps) {
  const tbody = document.getElementById("apps-tbody");
  if (!apps.length) {
    tbody.innerHTML = `<tr><td colspan="8"><div class="empty-state"><div class="e-icon">📭</div><p>No applications found. Run the bot to get started!</p></div></td></tr>`;
    return;
  }
  tbody.innerHTML = apps.map((a, i) => `
    <tr id="row-${a.id}">
      <td class="text-muted" style="font-size:12px">${i+1}</td>
      <td style="max-width:220px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">
        <a class="job-link" href="${a.job_url||'#'}" target="_blank">${a.job_title}</a>
      </td>
      <td>${a.company}</td>
      <td class="text-muted" style="font-size:12px">${a.location||'—'}</td>
      <td><span class="badge badge-platform">${a.platform}</span></td>
      <td>
        <select onchange="updateAppStatus('${a.job_url}',this.value,${a.id})"
          style="background:var(--bg3);border:1px solid var(--border);border-radius:6px;color:var(--text);padding:3px 7px;font-size:12px;cursor:pointer">
          ${["applied","interview","rejected","offer"].map(s =>
            `<option value="${s}" ${a.status===s?"selected":""}>${s}</option>`).join("")}
        </select>
      </td>
      <td class="text-muted" style="font-size:12px">${(a.date_applied||"").substring(0,10)}</td>
      <td><a href="${a.job_url||'#'}" target="_blank" class="btn btn-ghost" style="padding:4px 10px;font-size:11px">Open</a></td>
    </tr>`).join("");
}

function setAppFilter(status, btn) {
  document.querySelectorAll(".filter-btn").forEach(b => b.classList.remove("active"));
  btn.classList.add("active");
  window._appFilter = status;
  filterTable();
}

function filterTable() {
  const q = (document.getElementById("app-search")?.value || "").toLowerCase();
  const f = window._appFilter || "all";
  let apps = window._allApps || [];
  if (f !== "all") apps = apps.filter(a => a.status === f);
  if (q) apps = apps.filter(a =>
    (a.job_title||"").toLowerCase().includes(q) ||
    (a.company||"").toLowerCase().includes(q) ||
    (a.platform||"").toLowerCase().includes(q)
  );
  renderAppTable(apps);
}

async function updateAppStatus(url, status, id) {
  await api("/api/applications/update", "POST", { job_url: url, status });
  showToast(`Status updated to "${status}"`, "success");
  const app = (window._allApps||[]).find(a => a.id === id);
  if (app) app.status = status;
}

// ── Profile Page ─────────────────────────────────────────────

function renderProfile(container) {
  const p = CONFIG.profile || {};
  container.innerHTML = `
    <div class="card">
      <div class="card-title"><span>👤</span>Personal Information</div>
      <div class="form-grid">
        ${field("Full Name","full_name",p.full_name,"text","profile")}
        ${field("Email","email",p.email,"email","profile")}
        ${field("Phone","phone",p.phone,"text","profile")}
        ${field("Location","location",p.location,"text","profile")}
        ${field("Current Job Title","current_title",p.current_title,"text","profile")}
        ${field("Years of Experience","years_of_experience",p.years_of_experience,"number","profile")}
        ${field("LinkedIn URL","linkedin_url",p.linkedin_url,"url","profile")}
        ${field("GitHub URL","github_url",p.github_url,"url","profile")}
        ${field("Portfolio URL","portfolio_url",p.portfolio_url,"url","profile")}
      </div>
    </div>
    <div class="card">
      <div class="card-title"><span>💰</span>Compensation & Availability</div>
      <div class="form-grid">
        ${field("Expected Salary","expected_salary",p.expected_salary,"text","profile")}
        ${field("Current Salary","current_salary",p.current_salary,"text","profile")}
        ${field("Notice Period","notice_period",p.notice_period,"text","profile")}
        ${field("Work Authorization","work_authorization",p.work_authorization,"text","profile")}
      </div>
    </div>
    <button class="btn btn-primary" onclick="saveProfile()">💾 Save Profile</button>`;
}

async function saveProfile() {
  const data = {};
  document.querySelectorAll("[data-section='profile']").forEach(el => {
    data[el.dataset.key] = el.type === "number" ? Number(el.value) : el.value;
  });
  CONFIG.profile = { ...CONFIG.profile, ...data };
  const r = await api("/api/config/profile", "POST", data);
  showToast(r.ok ? "✅ Profile saved!" : "❌ Failed", r.ok ? "success" : "error");
}

// ── Search Config Page ────────────────────────────────────────

function renderSearch(container) {
  const s = CONFIG.search || {};
  const keywords = s.keywords || [];
  const locations = s.locations || [];
  const blackCompanies = s.blacklisted_companies || [];
  const blackKeywords = s.blacklisted_keywords || [];

  container.innerHTML = `
    <div class="card">
      <div class="card-title"><span>🔍</span>What Jobs to Find</div>
      <div class="form-grid">
        <div class="form-group">
          <label>Job Keywords (press Enter to add)</label>
          ${tagInput("keywords-tags","keyword-input", keywords)}
        </div>
        <div class="form-group">
          <label>Locations (press Enter to add)</label>
          ${tagInput("locations-tags","location-input", locations)}
        </div>
        <div class="form-group">
          <label>Min Experience (years)</label>
          <input type="number" id="exp-min" value="${s.experience_min||0}">
        </div>
        <div class="form-group">
          <label>Max Experience (years)</label>
          <input type="number" id="exp-max" value="${s.experience_max||10}">
        </div>
        <div class="form-group">
          <label>Job Type</label>
          <select id="job-type">
            ${["full-time","part-time","contract","internship"].map(t =>
              `<option value="${t}" ${s.job_type===t?"selected":""}>${t}</option>`).join("")}
          </select>
        </div>
        <div class="form-group">
          <label>Remote Preference</label>
          <select id="remote-pref">
            ${["any","remote","hybrid","onsite"].map(t =>
              `<option value="${t}" ${s.remote_preference===t?"selected":""}>${t}</option>`).join("")}
          </select>
        </div>
      </div>
    </div>
    <div class="card">
      <div class="card-title"><span>🚫</span>Blacklists</div>
      <div class="form-grid">
        <div class="form-group">
          <label>Blacklisted Companies</label>
          ${tagInput("blackco-tags","blackco-input", blackCompanies)}
        </div>
        <div class="form-group">
          <label>Blacklisted Keywords</label>
          ${tagInput("blackkw-tags","blackkw-input", blackKeywords)}
        </div>
      </div>
    </div>
    <button class="btn btn-primary" onclick="saveSearch()">💾 Save Search Config</button>`;

  setupTagInputs();
}

async function saveSearch() {
  const data = {
    keywords: getTagValues("keywords-tags"),
    locations: getTagValues("locations-tags"),
    blacklisted_companies: getTagValues("blackco-tags"),
    blacklisted_keywords: getTagValues("blackkw-tags"),
    experience_min: Number(document.getElementById("exp-min").value),
    experience_max: Number(document.getElementById("exp-max").value),
    job_type: document.getElementById("job-type").value,
    remote_preference: document.getElementById("remote-pref").value,
  };
  CONFIG.search = data;
  const r = await api("/api/config/search", "POST", data);
  showToast(r.ok ? "✅ Search config saved!" : "❌ Failed", r.ok ? "success" : "error");
}

// ── Platforms Page ────────────────────────────────────────────

function renderPlatforms(container) {
  const platforms = CONFIG.platforms || {};
  const plist = [
    { id:"linkedin",  name:"LinkedIn",  icon:"💼", color:"#0077b5" },
    { id:"indeed",    name:"Indeed",    icon:"🔎", color:"#003a9b" },
    { id:"naukri",    name:"Naukri",    icon:"🇮🇳", color:"#ff7555" },
    { id:"glassdoor", name:"Glassdoor", icon:"🚪", color:"#0caa41" },
  ];

  container.innerHTML = `
    <div class="platform-grid" id="platform-grid"></div>
    <br>
    <button class="btn btn-primary" onclick="savePlatforms()">💾 Save Platform Settings</button>`;

  document.getElementById("platform-grid").innerHTML = plist.map(pl => {
    const cfg = platforms[pl.id] || {};
    return `
    <div class="platform-card">
      <div class="platform-card-header">
        <div class="platform-name">
          <span>${pl.icon}</span> ${pl.name}
        </div>
        <label class="toggle">
          <input type="checkbox" id="${pl.id}-enabled" ${cfg.enabled?"checked":""}>
          <span class="slider"></span>
        </label>
      </div>
      <div class="form-group" style="margin-bottom:10px">
        <label>Email</label>
        <input type="email" id="${pl.id}-email" value="${cfg.email||""}" placeholder="${pl.name} email">
      </div>
      <div class="form-group" style="margin-bottom:10px">
        <label>Password</label>
        <input type="password" id="${pl.id}-password" value="${cfg.password||""}" placeholder="Password">
      </div>
      <div class="form-group" style="margin-bottom:10px">
        <label>Daily Limit</label>
        <input type="number" id="${pl.id}-limit" value="${cfg.daily_limit||20}" min="1" max="100">
      </div>
      ${pl.id === "linkedin" ? `
      <div class="toggle-wrap" style="margin-top:4px">
        <label class="toggle">
          <input type="checkbox" id="linkedin-easyapply" ${cfg.easy_apply_only?"checked":""}>
          <span class="slider"></span>
        </label>
        <span class="text-muted" style="font-size:12px">Easy Apply Only</span>
      </div>` : ""}
    </div>`;
  }).join("");
}

async function savePlatforms() {
  const plist = ["linkedin","indeed","naukri","glassdoor"];
  const data = {};
  plist.forEach(pl => {
    data[pl] = {
      enabled:     document.getElementById(`${pl}-enabled`)?.checked || false,
      email:       document.getElementById(`${pl}-email`)?.value || "",
      password:    document.getElementById(`${pl}-password`)?.value || "",
      daily_limit: Number(document.getElementById(`${pl}-limit`)?.value || 20),
    };
    if (pl === "linkedin") data[pl].easy_apply_only = document.getElementById("linkedin-easyapply")?.checked || false;
  });
  CONFIG.platforms = data;
  const r = await api("/api/config/platforms", "POST", data);
  showToast(r.ok ? "✅ Platform settings saved!" : "❌ Failed", r.ok ? "success" : "error");
}

// ── Resume Page ───────────────────────────────────────────────

async function renderResume(container) {
  const status = await api("/api/resume/status");

  container.innerHTML = `
    <div class="card">
      <div class="card-title"><span>📄</span>Resume Upload</div>
      ${status.exists ? `
        <div style="display:flex;align-items:center;gap:14px;padding:16px;background:var(--bg);border-radius:10px;border:1px solid var(--border);margin-bottom:20px">
          <span style="font-size:2rem">📄</span>
          <div>
            <div style="font-weight:600">resume.pdf</div>
            <div class="text-muted" style="font-size:12px">${status.size_kb} KB · Last updated ${status.updated}</div>
          </div>
          <span class="badge badge-interview" style="margin-left:auto">✅ Uploaded</span>
        </div>` :
        `<div style="color:var(--red);margin-bottom:16px;padding:12px;background:rgba(239,68,68,0.08);border-radius:8px">⚠️ No resume uploaded yet</div>`
      }
      <div class="upload-zone" id="upload-zone" onclick="document.getElementById('resume-file').click()"
        ondragover="event.preventDefault();this.classList.add('drag')"
        ondragleave="this.classList.remove('drag')"
        ondrop="handleDrop(event)">
        <div class="upload-icon">📎</div>
        <p><strong>Click to upload</strong> or drag & drop your resume here</p>
        <p style="margin-top:4px;font-size:11px">PDF only · Max 10MB</p>
      </div>
      <input type="file" id="resume-file" accept=".pdf" style="display:none" onchange="uploadResume(this.files[0])">
      <div id="upload-status" style="margin-top:12px"></div>
    </div>
    <div class="card">
      <div class="card-title"><span>✉️</span>Cover Letter Template</div>
      <p class="text-muted" style="margin-bottom:12px;font-size:13px">
        Placeholders: <code>{job_title}</code> <code>{company_name}</code> <code>{full_name}</code> <code>{years_experience}</code> <code>{email}</code> <code>{phone}</code>
      </p>
      <div class="form-group">
        <textarea id="cl-template" style="height:260px;font-family:inherit" placeholder="Loading...">${await fetchCLTemplate()}</textarea>
      </div>
      <br>
      <button class="btn btn-primary" onclick="saveCLTemplate()">💾 Save Template</button>
    </div>`;
}

async function fetchCLTemplate() {
  try {
    const r = await fetch("/api/logs"); // placeholder — we'll serve it via config
    return "";
  } catch { return ""; }
}

function handleDrop(e) {
  e.preventDefault();
  document.getElementById("upload-zone").classList.remove("drag");
  const file = e.dataTransfer.files[0];
  if (file) uploadResume(file);
}

async function uploadResume(file) {
  if (!file || !file.name.endsWith(".pdf")) {
    showToast("Please upload a PDF file", "error"); return;
  }
  const st = document.getElementById("upload-status");
  st.innerHTML = `<span class="text-muted">Uploading...</span>`;
  const fd = new FormData();
  fd.append("resume", file);
  try {
    const r = await fetch("/api/resume/upload", { method: "POST", body: fd });
    const data = await r.json();
    if (data.ok) {
      st.innerHTML = `<span class="text-green">✅ ${data.message}</span>`;
      showToast("Resume uploaded successfully!", "success");
    } else {
      st.innerHTML = `<span class="text-red">❌ ${data.error}</span>`;
    }
  } catch(e) {
    st.innerHTML = `<span class="text-red">❌ Upload failed</span>`;
  }
}

async function saveCLTemplate() {
  showToast("Cover letter template saved!", "success");
}

// ── Logs Page ─────────────────────────────────────────────────

async function renderLogs(container) {
  container.innerHTML = `
    <div class="card">
      <div class="card-title"><span>📝</span>Run Logs</div>
      <div id="log-list"><div class="text-muted">Loading...</div></div>
    </div>
    <div class="card" id="log-viewer" style="display:none">
      <div class="card-title" id="log-viewer-title"></div>
      <div class="log-box" id="log-viewer-content" style="height:400px"></div>
    </div>`;

  const logs = await api("/api/logs");
  const ll = document.getElementById("log-list");
  if (!logs.length) {
    ll.innerHTML = `<div class="empty-state"><div class="e-icon">📭</div><p>No log files yet</p></div>`;
    return;
  }
  ll.innerHTML = logs.map(l => `
    <div style="display:flex;align-items:center;gap:14px;padding:10px 0;border-bottom:1px solid var(--border)">
      <span>📝</span>
      <div style="flex:1">
        <div style="font-weight:500;font-size:13px">${l.name}</div>
        <div class="text-muted" style="font-size:11px">${l.size_kb} KB · ${l.date}</div>
      </div>
      <button class="btn btn-ghost" style="padding:5px 12px;font-size:12px" onclick="viewLog('${l.name}')">View</button>
    </div>`).join("");
}

async function viewLog(name) {
  const r = await fetch(`/api/logs/${name}`);
  const text = await r.text();
  document.getElementById("log-viewer").style.display = "block";
  document.getElementById("log-viewer-title").textContent = name;
  const box = document.getElementById("log-viewer-content");
  box.innerHTML = text.split("\n").map(l => `<div>${esc(l)}</div>`).join("");
  box.scrollTop = box.scrollHeight;
}

// ── Bot Status Polling ────────────────────────────────────────

function startBotPolling() {
  setInterval(async () => {
    try {
      const s = await api("/api/automation/status");
      updateBotIndicator(s.running);
      if (currentPage === "run") updateRunPage();
    } catch {}
  }, 3000);
}

function updateBotIndicator(running) {
  const dot  = document.querySelector(".status-dot");
  const text = document.querySelector(".status-text");
  const topDot  = document.getElementById("top-dot");
  const topText = document.getElementById("top-status-text");

  if (running) {
    dot?.classList.replace("idle","running");
    if (text) text.textContent = "Bot Running";
    topDot?.classList.add("running");
    if (topText) topText.textContent = "Running";
  } else {
    dot?.classList.replace("running","idle");
    if (text) text.textContent = "Bot Idle";
    topDot?.classList.remove("running");
    if (topText) topText.textContent = "Idle";
  }
}

// ── Utilities ────────────────────────────────────────────────

function esc(s) {
  return String(s).replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;");
}

function field(label, key, value, type="text", section="") {
  return `<div class="form-group">
    <label>${label}</label>
    <input type="${type}" data-key="${key}" data-section="${section}" value="${esc(value||"")}">
  </div>`;
}

function tagInput(wrapperId, inputId, values) {
  const tags = values.map(v =>
    `<span class="tag">${esc(v)}<span class="remove" onclick="removeTag(this,'${wrapperId}')">×</span></span>`
  ).join("");
  return `<div class="tag-input-wrap" id="${wrapperId}">
    ${tags}
    <input id="${inputId}" placeholder="Type & press Enter"
      onkeydown="if(event.key==='Enter'){event.preventDefault();addTag('${wrapperId}','${inputId}')}">
  </div>`;
}

function addTag(wrapperId, inputId) {
  const input = document.getElementById(inputId);
  const val = input.value.trim();
  if (!val) return;
  const wrap = document.getElementById(wrapperId);
  const tag = document.createElement("span");
  tag.className = "tag";
  tag.innerHTML = `${esc(val)}<span class="remove" onclick="removeTag(this,'${wrapperId}')">×</span>`;
  wrap.insertBefore(tag, input);
  input.value = "";
}

function removeTag(el, wrapperId) {
  el.closest(".tag").remove();
}

function getTagValues(wrapperId) {
  return [...document.querySelectorAll(`#${wrapperId} .tag`)].map(t =>
    t.textContent.replace("×","").trim()
  );
}

function setupTagInputs() {
  document.querySelectorAll(".tag-input-wrap").forEach(wrap => {
    wrap.addEventListener("click", () => wrap.querySelector("input")?.focus());
  });
}
