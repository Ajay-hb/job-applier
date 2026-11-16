"""
Flask Dashboard API
Serves a web dashboard to monitor and manage job applications.
"""

from flask import Flask, jsonify, render_template_string, request
from flask_cors import CORS
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from tracker.db import get_all_applications, get_stats, update_status, init_db

app = Flask(__name__)
CORS(app)

DASHBOARD_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Job Applier Dashboard</title>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: 'Segoe UI', sans-serif; background: #0f172a; color: #e2e8f0; min-height: 100vh; }
  .header { background: linear-gradient(135deg, #1e40af, #7c3aed); padding: 24px 32px; display: flex; align-items: center; gap: 16px; }
  .header h1 { font-size: 1.8rem; font-weight: 700; }
  .header span { font-size: 2rem; }
  .stats { display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: 16px; padding: 24px 32px; }
  .stat-card { background: #1e293b; border-radius: 12px; padding: 20px; text-align: center; border: 1px solid #334155; }
  .stat-card .num { font-size: 2.5rem; font-weight: 800; color: #60a5fa; }
  .stat-card .label { font-size: 0.85rem; color: #94a3b8; margin-top: 4px; }
  .stat-card.interview .num { color: #34d399; }
  .stat-card.rejected .num { color: #f87171; }
  .stat-card.offer .num { color: #fbbf24; }
  .table-wrap { padding: 0 32px 32px; }
  .table-wrap h2 { margin-bottom: 16px; font-size: 1.2rem; color: #94a3b8; }
  table { width: 100%; border-collapse: collapse; background: #1e293b; border-radius: 12px; overflow: hidden; }
  th { background: #0f172a; padding: 12px 16px; text-align: left; font-size: 0.75rem; text-transform: uppercase; letter-spacing: 1px; color: #64748b; }
  td { padding: 12px 16px; border-bottom: 1px solid #334155; font-size: 0.9rem; }
  tr:last-child td { border-bottom: none; }
  .badge { display: inline-block; padding: 2px 10px; border-radius: 999px; font-size: 0.75rem; font-weight: 600; }
  .badge-applied { background: #1d4ed8; color: #bfdbfe; }
  .badge-interview { background: #065f46; color: #6ee7b7; }
  .badge-rejected { background: #7f1d1d; color: #fca5a5; }
  .badge-offer { background: #78350f; color: #fde68a; }
  .platform { display: inline-block; padding: 2px 8px; border-radius: 4px; font-size: 0.72rem; font-weight: 600; background: #334155; color: #94a3b8; }
  .filters { padding: 0 32px 16px; display: flex; gap: 10px; flex-wrap: wrap; }
  .filter-btn { background: #1e293b; border: 1px solid #334155; color: #94a3b8; padding: 6px 16px; border-radius: 999px; cursor: pointer; font-size: 0.85rem; transition: all 0.2s; }
  .filter-btn.active, .filter-btn:hover { background: #1e40af; border-color: #3b82f6; color: #fff; }
  a.job-link { color: #60a5fa; text-decoration: none; }
  a.job-link:hover { text-decoration: underline; }
</style>
</head>
<body>
<div class="header"><span>🤖</span><h1>Job Applier Dashboard</h1></div>
<div class="stats" id="stats-container"></div>
<div class="filters">
  <button class="filter-btn active" onclick="filterApps('all', this)">All</button>
  <button class="filter-btn" onclick="filterApps('applied', this)">Applied</button>
  <button class="filter-btn" onclick="filterApps('interview', this)">Interview</button>
  <button class="filter-btn" onclick="filterApps('rejected', this)">Rejected</button>
  <button class="filter-btn" onclick="filterApps('offer', this)">Offer</button>
</div>
<div class="table-wrap">
  <h2>Applications</h2>
  <table>
    <thead><tr><th>#</th><th>Role</th><th>Company</th><th>Location</th><th>Platform</th><th>Status</th><th>Date</th></tr></thead>
    <tbody id="app-tbody"></tbody>
  </table>
</div>
<script>
let allApps = [];
async function loadStats() {
  const r = await fetch('/api/stats');
  const s = await r.json();
  document.getElementById('stats-container').innerHTML = `
    <div class="stat-card"><div class="num">${s.total}</div><div class="label">Total Applied</div></div>
    <div class="stat-card interview"><div class="num">${s.interviews}</div><div class="label">Interviews</div></div>
    <div class="stat-card rejected"><div class="num">${s.rejected}</div><div class="label">Rejected</div></div>
    <div class="stat-card offer"><div class="num">${s.offers}</div><div class="label">Offers 🎉</div></div>
  `;
}
async function loadApps(status='') {
  const url = status && status !== 'all' ? `/api/applications?status=${status}` : '/api/applications';
  const r = await fetch(url);
  allApps = await r.json();
  renderTable(allApps);
}
function renderTable(apps) {
  const tbody = document.getElementById('app-tbody');
  if (!apps.length) { tbody.innerHTML = '<tr><td colspan="7" style="text-align:center;color:#64748b;padding:32px">No applications yet</td></tr>'; return; }
  tbody.innerHTML = apps.map((a, i) => `
    <tr>
      <td style="color:#64748b">${i+1}</td>
      <td><a class="job-link" href="${a.job_url||'#'}" target="_blank">${a.job_title}</a></td>
      <td>${a.company}</td>
      <td style="color:#94a3b8">${a.location||'-'}</td>
      <td><span class="platform">${a.platform}</span></td>
      <td><span class="badge badge-${a.status}">${a.status}</span></td>
      <td style="color:#64748b;font-size:0.8rem">${(a.date_applied||'').substring(0,10)}</td>
    </tr>`).join('');
}
function filterApps(status, btn) {
  document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
  loadApps(status);
}
loadStats();
loadApps();
setInterval(() => { loadStats(); loadApps(); }, 30000);
</script>
</body>
</html>
"""


@app.route("/")
def index():
    return render_template_string(DASHBOARD_HTML)


@app.route("/api/stats")
def stats():
    return jsonify(get_stats())


@app.route("/api/applications")
def applications():
    status = request.args.get("status")
    platform = request.args.get("platform")
    return jsonify(get_all_applications(platform=platform, status=status))


@app.route("/api/update_status", methods=["POST"])
def update():
    data = request.json
    update_status(data["job_url"], data["status"], data.get("notes", ""))
    return jsonify({"ok": True})


if __name__ == "__main__":
    init_db()
    print("🌐 Dashboard running at http://localhost:5000")
    app.run(debug=True, port=5000)
