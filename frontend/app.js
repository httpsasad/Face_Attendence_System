/* ============================================================
   FaceAttend AI — Frontend Logic
   ============================================================ */

const API = 'http://127.0.0.1:5000';
let socket;
let capturedImageData = null;
let webcamStream = null;
let recognitionActive = false;

/* ── Socket.IO ─────────────────────────────────────────────────────────── */
function initSocket() {
  const socketUrl = window.location.protocol === 'file:' ? 'http://localhost:5000' : window.location.origin;
  socket = io(socketUrl, { transports: ['websocket', 'polling'] });

  socket.on('connect', () => {
    setServerStatus(true);
  });

  socket.on('disconnect', () => {
    setServerStatus(false);
  });

  socket.on('stats_update', (stats) => {
    updateStatCards(stats);
  });

  socket.on('attendance_marked', (data) => {
    showToast(`✅ ${data.name} marked Present (${data.confidence}%)`, 'success');
    prependActivity(data, document.getElementById('activityFeed'));
    prependActivity(data, document.getElementById('liveActivityFeed'));
    refreshStats();
  });

  socket.on('student_registered', (data) => {
    showToast(`🎉 ${data.name} registered successfully!`, 'success');
    loadStudents();
  });
}

function setServerStatus(online) {
  const dot = document.getElementById('serverDot');
  const label = document.getElementById('serverStatus');
  const sysBadge = document.getElementById('sysStatus');
  if (online) {
    dot.classList.remove('red');
    label.textContent = 'Connected';
    if (sysBadge) { sysBadge.textContent = 'Online'; sysBadge.className = 'badge present'; }
  } else {
    dot.classList.add('red');
    label.textContent = 'Disconnected';
    if (sysBadge) { sysBadge.textContent = 'Offline'; sysBadge.className = 'badge absent'; }
  }
}

/* ── Navigation ────────────────────────────────────────────────────────── */
function showSection(name) {
  document.querySelectorAll('.section').forEach(s => s.classList.remove('active'));
  document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
  const sec = document.getElementById('sec-' + name);
  if (sec) sec.classList.add('active');
  const nav = document.querySelector(`.nav-item[data-section="${name}"]`);
  if (nav) nav.classList.add('active');

  // On-demand loads
  if (name === 'records')  loadAttendance();
  if (name === 'students') loadStudents();
  if (name === 'reports')  loadReportStats();
  if (name === 'settings') loadSettingsInfo();
}

document.querySelectorAll('.nav-item[data-section]').forEach(item => {
  item.addEventListener('click', () => showSection(item.dataset.section));
});

/* ── Stats ─────────────────────────────────────────────────────────────── */
async function refreshStats() {
  try {
    const res = await fetch(`${API}/api/stats`);
    const stats = await res.json();
    updateStatCards(stats);
    populateDeptDropdowns(stats.departments || []);
  } catch (e) { /* silent */ }
}

function updateStatCards(stats) {
  animateNumber('statTotal',   stats.total_students);
  animateNumber('statPresent', stats.present_today);
  animateNumber('statAbsent',  stats.absent_today);
  document.getElementById('statPct').textContent = stats.attendance_percentage + '%';

  // Ring
  const pct = stats.attendance_percentage;
  const circumference = 408.41;
  const offset = circumference - (pct / 100) * circumference;
  document.getElementById('ringFill').style.strokeDashoffset = offset;
  document.getElementById('ringValue').textContent = pct + '%';
  document.getElementById('ringPresent').textContent = stats.present_today;
  document.getElementById('ringAbsent').textContent  = stats.absent_today;
  document.getElementById('ringTotal').textContent   = stats.total_students;

  // Activity feed
  if (stats.recent_activity && stats.recent_activity.length > 0) {
    const feed = document.getElementById('activityFeed');
    feed.innerHTML = '';
    stats.recent_activity.forEach(a => appendActivityItem(a, feed));
  }
}

function animateNumber(id, target) {
  const el = document.getElementById(id);
  if (!el) return;
  const start = parseInt(el.textContent) || 0;
  const duration = 600;
  const startTime = performance.now();
  function update(now) {
    const elapsed = now - startTime;
    const progress = Math.min(elapsed / duration, 1);
    const val = Math.round(start + (target - start) * easeOut(progress));
    el.textContent = val;
    if (progress < 1) requestAnimationFrame(update);
  }
  requestAnimationFrame(update);
}

function easeOut(t) { return 1 - Math.pow(1 - t, 3); }

function populateDeptDropdowns(depts) {
  ['filterDept', 'rpDept'].forEach(id => {
    const sel = document.getElementById(id);
    if (!sel) return;
    const current = sel.value;
    sel.innerHTML = '<option value="">All Departments</option>';
    depts.forEach(d => {
      const opt = document.createElement('option');
      opt.value = d; opt.textContent = d;
      sel.appendChild(opt);
    });
    sel.value = current;
  });
}

/* ── Activity Feed ─────────────────────────────────────────────────────── */
function appendActivityItem(data, container) {
  if (!container) return;
  const emptyState = container.querySelector('.empty-state');
  if (emptyState) emptyState.remove();
  const item = buildActivityItem(data);
  container.appendChild(item);
}

function prependActivity(data, container) {
  if (!container) return;
  const emptyState = container.querySelector('.empty-state');
  if (emptyState) emptyState.remove();
  const item = buildActivityItem(data);
  container.insertBefore(item, container.firstChild);
  // Keep max 20 items
  while (container.children.length > 20) container.removeChild(container.lastChild);
}

function buildActivityItem(data) {
  const item = document.createElement('div');
  item.className = 'activity-item';
  const initial = (data.name || '?')[0].toUpperCase();
  const statusClass = (data.status || 'present').toLowerCase();
  const timeStr = data.time || new Date().toTimeString().slice(0,8);
  const genderStr = data.gender ? (data.gender === 'Female' ? '👩 Female' : '👨 Male') : '';
  const ageStr = data.age ? `Age ${data.age}` : '';
  const infoMeta = [genderStr, ageStr, data.department, timeStr].filter(Boolean).join(' · ');

  item.innerHTML = `
    <div class="activity-avatar" id="av-${data.student_id}">
      <img src="/api/photo/${data.student_id}" alt="${initial}"
           onerror="this.style.display='none';this.parentElement.textContent='${initial}'"/>
    </div>
    <div class="activity-info">
      <div class="activity-name">${data.name}</div>
      <div class="activity-meta">${infoMeta}</div>
    </div>
    <span class="badge ${statusClass}">${data.status || 'Present'}</span>
  `;
  return item;
}

/* ── Live Recognition ──────────────────────────────────────────────────── */
async function toggleRecognition() {
  try {
    const res = await fetch(`${API}/api/recognition/toggle`, { method: 'POST' });
    const data = await res.json();
    recognitionActive = data.active;
    updateRecognitionUI(recognitionActive);
  } catch (e) {
    showToast('Failed to toggle recognition', 'error');
  }
}

function updateRecognitionUI(active) {
  const btn = document.getElementById('btnToggleRecog');
  const dot = document.getElementById('camDot');
  const statusTxt = document.getElementById('camStatusText');
  if (active) {
    btn.innerHTML = `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="16" height="16"><rect x="6" y="4" width="4" height="16"/><rect x="14" y="4" width="4" height="16"/></svg> Stop Recognition`;
    btn.className = 'btn btn-danger';
    dot.style.background = 'var(--green)';
    dot.style.boxShadow = '0 0 8px var(--green)';
    statusTxt.textContent = 'Live';
  } else {
    btn.innerHTML = `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="16" height="16"><polygon points="5 3 19 12 5 21 5 3"/></svg> Start Recognition`;
    btn.className = 'btn btn-primary';
    dot.style.background = 'var(--orange)';
    dot.style.boxShadow = '0 0 8px var(--orange)';
    statusTxt.textContent = 'Paused';
  }
}

/* ── Webcam Registration (Using Backend Stream) ──────────────────────────── */
async function openWebcam() {
  const liveImg = document.getElementById('liveStream');
  const videoBox = document.getElementById('regVideo');
  
  // Use the backend stream instead of local getUserMedia to avoid camera locks
  videoBox.style.display = 'none';
  document.getElementById('webcamPlaceholder').style.display = 'none';
  document.getElementById('capturedImg').style.display = 'block';
  document.getElementById('capturedImg').src = liveImg.src; // Show live stream in preview box
  
  document.getElementById('btnCapture').disabled = false;
  document.getElementById('btnRetake').style.display = 'none';
  capturedImageData = null;
  document.getElementById('btnSubmitReg').disabled = true;
}

function capturePhoto() {
  const liveImg = document.getElementById('liveStream');
  const canvas = document.getElementById('regCanvas');
  const preview = document.getElementById('capturedImg');

  canvas.width = 640;
  canvas.height = 480;
  const ctx = canvas.getContext('2d');
  
  // Draw the current frame from the backend stream
  ctx.drawImage(liveImg, 0, 0, 640, 480);
  capturedImageData = canvas.toDataURL('image/jpeg', 0.9);

  // Show frozen preview
  preview.src = capturedImageData;

  document.getElementById('btnCapture').disabled = true;
  document.getElementById('btnRetake').style.display = 'inline-flex';
  document.getElementById('btnSubmitReg').disabled = false;

  showToast('📸 Face captured! Fill the form and click Register.', 'info');
}

function retakePhoto() {
  capturedImageData = null;
  document.getElementById('btnRetake').style.display = 'none';
  document.getElementById('btnSubmitReg').disabled = true;
  openWebcam();
}

async function submitRegistration() {
  const name = document.getElementById('regName').value.trim();
  const sid  = document.getElementById('regId').value.trim();
  const dept = document.getElementById('regDept').value.trim();
  const role = document.getElementById('regRole').value;

  if (!name || !sid || !dept) { showToast('Please fill all required fields.', 'error'); return; }
  if (!capturedImageData)     { showToast('Please capture a face photo first.', 'error'); return; }

  const btn = document.getElementById('btnSubmitReg');
  btn.disabled = true;
  btn.innerHTML = '<div class="spinner"></div> Registering...';

  try {
    const res = await fetch(`${API}/api/register`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ student_id: sid, name, department: dept, role, image: capturedImageData })
    });
    const data = await res.json();
    if (data.success) {
      showToast(data.message, 'success');
      resetRegForm();
      refreshStats();
    } else {
      showToast(data.message || 'Registration failed.', 'error');
    }
  } catch (e) {
    showToast('Server error. Please try again.', 'error');
  } finally {
    btn.disabled = false;
    btn.innerHTML = `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="16" height="16"><path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><line x1="19" y1="8" x2="19" y2="14"/><line x1="22" y1="11" x2="16" y2="11"/></svg> Register Person`;
  }
}

function resetRegForm() {
  ['regName','regId','regDept'].forEach(id => document.getElementById(id).value = '');
  document.getElementById('regRole').value = 'Student';
  capturedImageData = null;
  document.getElementById('capturedImg').style.display = 'none';
  document.getElementById('regVideo').style.display = 'none';
  document.getElementById('webcamPlaceholder').style.display = 'flex';
  document.getElementById('webcamPlaceholder').style.flexDirection = 'column';
  document.getElementById('webcamPlaceholder').style.alignItems = 'center';
  document.getElementById('btnCapture').disabled = true;
  document.getElementById('btnRetake').style.display = 'none';
  document.getElementById('btnSubmitReg').disabled = true;
  if (webcamStream) { webcamStream.getTracks().forEach(t => t.stop()); webcamStream = null; }
}

/* ── Attendance Records ────────────────────────────────────────────────── */
async function loadAttendance() {
  const search = document.getElementById('searchInput').value;
  const dept   = document.getElementById('filterDept').value;
  const from   = document.getElementById('filterFrom').value;
  const to     = document.getElementById('filterTo').value;

  const params = new URLSearchParams();
  if (search) params.set('search', search);
  if (dept)   params.set('department', dept);
  if (from)   params.set('date_from', from);
  if (to)     params.set('date_to', to);

  const tbody = document.getElementById('attendanceBody');
  tbody.innerHTML = '<tr><td colspan="9"><div class="empty-state"><div class="spinner"></div></div></td></tr>';

  try {
    const res = await fetch(`${API}/api/attendance?${params}`);
    const records = await res.json();
    document.getElementById('recordCount').textContent = `${records.length} record${records.length !== 1 ? 's' : ''}`;
    if (records.length === 0) {
      tbody.innerHTML = '<tr><td colspan="9"><div class="empty-state"><p>No records found</p></div></td></tr>';
      return;
    }
    tbody.innerHTML = '';
    records.forEach((r, i) => {
      const tr = document.createElement('tr');
      const gTag = r.gender ? `<span class="badge ${r.gender.toLowerCase() === 'female' ? 'late' : 'present'}">${r.gender === 'Female' ? '👩 Female' : '👨 Male'}</span>` : '—';
      const aTag = r.age ? `<code style="font-size:11px;color:var(--cyan)">${r.age}</code>` : '—';
      tr.innerHTML = `
        <td style="color:var(--text3)">${i + 1}</td>
        <td><code style="font-size:11px;color:var(--cyan)">${r.student_id}</code></td>
        <td><strong>${r.name}</strong></td>
        <td>${r.department || '—'}</td>
        <td>${gTag}</td>
        <td>${aTag}</td>
        <td>${r.date}</td>
        <td>${r.time}</td>
        <td><span class="badge ${(r.status||'present').toLowerCase()}">${r.status || 'Present'}</span></td>
      `;
      tbody.appendChild(tr);
    });
  } catch (e) {
    tbody.innerHTML = '<tr><td colspan="9"><div class="empty-state"><p>Failed to load records</p></div></td></tr>';
  }
}

function clearFilters() {
  ['searchInput','filterDept','filterFrom','filterTo'].forEach(id => document.getElementById(id).value = '');
  loadAttendance();
}

/* ── Students Grid ─────────────────────────────────────────────────────── */
async function loadStudents() {
  const grid = document.getElementById('studentsGrid');
  grid.innerHTML = '<div class="empty-state"><div class="spinner"></div></div>';
  try {
    const res = await fetch(`${API}/api/students`);
    const students = await res.json();
    if (students.length === 0) {
      grid.innerHTML = '<div class="empty-state"><p>No students registered yet.</p></div>';
      return;
    }
    grid.innerHTML = '';
    students.forEach(s => {
      const card = document.createElement('div');
      card.className = 'student-card';
      const initial = (s.name || '?')[0].toUpperCase();
      const gTag = s.gender ? (s.gender === 'Female' ? '👩 Female' : '👨 Male') : '';
      const aTag = s.age ? `Age ${s.age}` : '';
      const studentMetaStr = [gTag, aTag, s.department, s.role].filter(Boolean).join(' · ');

      card.innerHTML = `
        <div class="student-photo">
          <img src="/api/photo/${s.student_id}" alt="${initial}"
               onerror="this.style.display='none';this.parentElement.textContent='${initial}'"/>
        </div>
        <div class="student-name">${s.name}</div>
        <div class="student-meta">${studentMetaStr}</div>
        <div class="student-id">${s.student_id}</div>
        <div style="margin-top:12px;">
          <button class="btn btn-danger btn-sm" onclick="deleteStudent('${s.student_id}','${s.name}')">Delete</button>
        </div>
      `;
      grid.appendChild(card);
    });
  } catch (e) {
    grid.innerHTML = '<div class="empty-state"><p>Failed to load students</p></div>';
  }
}

async function deleteStudent(sid, name) {
  if (!confirm(`Delete ${name} (${sid}) from the system?`)) return;
  try {
    await fetch(`${API}/api/students/${sid}`, { method: 'DELETE' });
    showToast(`${name} removed from system.`, 'info');
    loadStudents();
    refreshStats();
  } catch (e) {
    showToast('Failed to delete student.', 'error');
  }
}

/* ── Export CSV ────────────────────────────────────────────────────────── */
function exportCSV() {
  const dept = document.getElementById('filterDept').value;
  const from = document.getElementById('filterFrom').value;
  const to   = document.getElementById('filterTo').value;
  const p = new URLSearchParams();
  if (dept) p.set('department', dept);
  if (from) p.set('date_from', from);
  if (to)   p.set('date_to', to);
  window.open(`${API}/api/export?${p}`, '_blank');
}

function exportCSVReport() {
  const dept = document.getElementById('rpDept').value;
  const from = document.getElementById('rpFrom').value;
  const to   = document.getElementById('rpTo').value;
  const p = new URLSearchParams();
  if (dept) p.set('department', dept);
  if (from) p.set('date_from', from);
  if (to)   p.set('date_to', to);
  window.open(`${API}/api/export?${p}`, '_blank');
}

/* ── Reports ───────────────────────────────────────────────────────────── */
async function loadReportStats() {
  try {
    const res = await fetch(`${API}/api/stats`);
    const stats = await res.json();
    document.getElementById('rpTotal').textContent   = stats.total_students;
    document.getElementById('rpPresent').textContent = stats.present_today;
    document.getElementById('rpRate').textContent    = stats.attendance_percentage + '%';
    populateDeptDropdowns(stats.departments || []);
  } catch (e) { /* silent */ }
}

/* ── Settings Info ─────────────────────────────────────────────────────── */
async function loadSettingsInfo() {
  try {
    const res = await fetch(`${API}/api/stats`);
    const stats = await res.json();
    document.getElementById('sysfaces').textContent  = stats.total_students;
    document.getElementById('sysRecords').textContent = stats.present_today + ' today';
  } catch (e) { /* silent */ }
}

/* ── Toast Notifications ───────────────────────────────────────────────── */
function showToast(msg, type = 'info') {
  const icons = { success: '✅', error: '❌', info: 'ℹ️' };
  const container = document.getElementById('toast-container');
  const toast = document.createElement('div');
  toast.className = `toast ${type}`;
  toast.innerHTML = `<span class="toast-icon">${icons[type] || 'ℹ️'}</span><span class="toast-msg">${msg}</span>`;
  container.appendChild(toast);
  setTimeout(() => {
    toast.classList.add('hiding');
    toast.addEventListener('animationend', () => toast.remove());
  }, 3800);
}

/* ── Date Display ──────────────────────────────────────────────────────── */
function setDashDate() {
  const el = document.getElementById('dashDate');
  if (el) {
    const now = new Date();
    el.textContent = now.toLocaleDateString('en-US', { weekday:'long', year:'numeric', month:'long', day:'numeric' });
  }
}

/* ── Init ──────────────────────────────────────────────────────────────── */
window.addEventListener('DOMContentLoaded', () => {
  setDashDate();
  initSocket();
  refreshStats();

  // Auto-refresh stats every 30s
  setInterval(refreshStats, 30000);

  // Set today's date as default filter
  const today = new Date().toISOString().split('T')[0];
  document.getElementById('filterTo').value = today;
  document.getElementById('rpTo').value = today;
});
