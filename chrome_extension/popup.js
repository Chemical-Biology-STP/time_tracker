// Popup script for Time Tracker

let groups = [];
let settings = {};
let calYear, calMonth;

document.addEventListener('DOMContentLoaded', async () => {
  groups = await Storage.getGroups();
  settings = await Storage.getSettings();
  
  const now = new Date();
  calYear = now.getFullYear();
  calMonth = now.getMonth();
  
  initializeTabs();
  initializeLogPanel();
  initializeEntriesPanel();
  initializeSummaryPanel();
  
  document.getElementById('submitBtn').addEventListener('click', submitEntry);
  document.getElementById('settingsBtn').addEventListener('click', openSettings);
  document.getElementById('exportBtn').addEventListener('click', exportCSV);
  document.getElementById('entriesGroupFilter').addEventListener('change', onEntriesGroupChange);
  document.getElementById('entriesProjectFilter').addEventListener('change', loadEntries);
  document.getElementById('entriesYearFilter').addEventListener('change', loadEntries);
  document.getElementById('entriesMonthFilter').addEventListener('change', loadEntries);
  document.getElementById('summaryGroupFilter').addEventListener('change', loadSummary);
  document.getElementById('summaryYearFilter').addEventListener('change', loadSummary);
  document.getElementById('summaryMonthFilter').addEventListener('change', loadSummary);
  document.getElementById('group').addEventListener('change', onGroupChange);
  document.getElementById('calPrev').addEventListener('click', () => { calMonth--; if (calMonth < 0) { calMonth = 11; calYear--; } renderCalendar(); });
  document.getElementById('calNext').addEventListener('click', () => { calMonth++; if (calMonth > 11) { calMonth = 0; calYear++; } renderCalendar(); });
  document.getElementById('dayDetailClose').addEventListener('click', () => { document.getElementById('dayDetail').style.display = 'none'; });
});

function initializeTabs() {
  document.querySelectorAll('.tab').forEach(tab => {
    tab.addEventListener('click', () => {
      document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
      tab.classList.add('active');
      document.querySelectorAll('.panel').forEach(p => p.classList.remove('active'));
      document.getElementById(tab.dataset.panel).classList.add('active');
      
      if (tab.dataset.panel === 'entries') loadEntries();
      if (tab.dataset.panel === 'summary') loadSummary();
      if (tab.dataset.panel === 'calendar') renderCalendar();
    });
  });
}

function initializeLogPanel() {
  const groupSelect = document.getElementById('group');
  groupSelect.innerHTML = '<option value="">Select a group</option>';
  
  if (groups.length === 0) {
    groupSelect.innerHTML = '<option value="">No groups - add in Settings</option>';
  } else {
    groups.forEach(g => {
      const option = document.createElement('option');
      option.value = g.id;
      option.textContent = g.name;
      if (g.id === settings.defaultGroupId) option.selected = true;
      groupSelect.appendChild(option);
    });
  }
  
  const now = new Date();
  const intervalMs = settings.promptIntervalMinutes * 60 * 1000;
  const start = new Date(now.getTime() - intervalMs);
  
  document.getElementById('entryDate').value = now.toISOString().split('T')[0];
  document.getElementById('endTime').value = formatTime(now);
  document.getElementById('startTime').value = formatTime(start);
}

function initializeEntriesPanel() {
  const filter = document.getElementById('entriesGroupFilter');
  filter.innerHTML = '<option value="">All Groups</option>';
  groups.forEach(g => {
    const option = document.createElement('option');
    option.value = g.id;
    option.textContent = g.name;
    filter.appendChild(option);
  });
  // Reset project filter
  document.getElementById('entriesProjectFilter').innerHTML = '<option value="">All Projects</option>';
  populateDateFilters('entries');
  loadEntries();
}

function initializeSummaryPanel() {
  const filter = document.getElementById('summaryGroupFilter');
  filter.innerHTML = '<option value="">All Groups</option>';
  groups.forEach(g => {
    const option = document.createElement('option');
    option.value = g.id;
    option.textContent = g.name;
    filter.appendChild(option);
  });
  populateDateFilters('summary');
  loadSummary();
}

async function populateDateFilters(prefix) {
  const entries = await Storage.getEntries();
  const years = new Set();
  entries.forEach(e => { if (e.date) years.add(e.date.substring(0, 4)); });
  
  const yearFilter = document.getElementById(`${prefix}YearFilter`);
  yearFilter.innerHTML = '<option value="">All Years</option>';
  Array.from(years).sort().reverse().forEach(year => {
    const option = document.createElement('option');
    option.value = year;
    option.textContent = year;
    yearFilter.appendChild(option);
  });
  
  const monthFilter = document.getElementById(`${prefix}MonthFilter`);
  monthFilter.innerHTML = '<option value="">All Months</option>';
  const months = ['January','February','March','April','May','June','July','August','September','October','November','December'];
  months.forEach((m, i) => {
    const option = document.createElement('option');
    option.value = String(i + 1).padStart(2, '0');
    option.textContent = m;
    monthFilter.appendChild(option);
  });
}

async function getFilteredEntries(prefix) {
  const groupId = document.getElementById(`${prefix}GroupFilter`).value;
  const year = document.getElementById(`${prefix}YearFilter`).value;
  const month = document.getElementById(`${prefix}MonthFilter`).value;
  let entries = await Storage.getEntries();
  
  if (groupId) entries = entries.filter(e => e.groupId === parseInt(groupId));
  if (year) entries = entries.filter(e => e.date && e.date.startsWith(year));
  if (month) entries = entries.filter(e => e.date && e.date.substring(5, 7) === month);
  
  // Project filter (entries panel only)
  if (prefix === 'entries') {
    const projectId = document.getElementById('entriesProjectFilter').value;
    if (projectId === 'none') {
      entries = entries.filter(e => !e.projectId);
    } else if (projectId) {
      entries = entries.filter(e => e.projectId === parseInt(projectId));
    }
  }
  
  return entries;
}

async function onEntriesGroupChange() {
  const groupId = document.getElementById('entriesGroupFilter').value;
  const projectFilter = document.getElementById('entriesProjectFilter');
  projectFilter.innerHTML = '<option value="">All Projects</option>';
  
  if (groupId) {
    const projects = await Storage.getProjectsByGroup(parseInt(groupId), true);
    if (projects.length > 0) {
      projectFilter.innerHTML += '<option value="none">No Project</option>';
      projects.forEach(p => {
        const option = document.createElement('option');
        option.value = p.id;
        option.textContent = p.name + (p.archived ? ' (archived)' : '');
        projectFilter.appendChild(option);
      });
    }
  }
  
  loadEntries();
}

async function loadEntries() {
  let entries = await getFilteredEntries('entries');
  entries.sort((a, b) => b.date.localeCompare(a.date) || (a.startTime || '').localeCompare(b.startTime || ''));
  
  const container = document.getElementById('entriesList');
  if (entries.length === 0) {
    container.innerHTML = '<div class="empty-state">No entries found</div>';
    return;
  }
  
  const groupMap = {};
  groups.forEach(g => groupMap[g.id] = g);
  
  const projects = await Storage.getProjects();
  const projectMap = {};
  projects.forEach(p => projectMap[p.id] = p);
  
  container.innerHTML = entries.slice(0, 50).map(e => {
    const group = groupMap[e.groupId] || { name: 'Unknown' };
    const project = e.projectId ? projectMap[e.projectId] : null;
    const projectLabel = project ? ` • ${escapeHtml(project.name)}` : '';
    return `
      <div class="entry-item" data-id="${e.id}">
        <div class="entry-header">
          <div class="entry-date">${e.date} • ${escapeHtml(group.name)}${projectLabel}</div>
          <div>
            <button class="edit-btn" data-edit-id="${e.id}" title="Edit entry" style="background:none;border:none;color:#0078d4;font-size:14px;cursor:pointer;padding:0 4px;">✏️</button>
            <button class="delete-btn" data-delete-id="${e.id}" title="Delete entry">×</button>
          </div>
        </div>
        <div class="entry-task">${escapeHtml(e.taskDescription)}</div>
        <div class="entry-meta">
          <span>${e.startTime} - ${e.endTime}</span>
          <span class="entry-hours">${e.totalHours}h</span>
        </div>
      </div>
    `;
  }).join('');
  
  // Attach delete handlers
  container.querySelectorAll('[data-delete-id]').forEach(btn => {
    btn.addEventListener('click', () => deleteEntry(parseInt(btn.dataset.deleteId)));
  });
  
  // Attach edit handlers
  container.querySelectorAll('[data-edit-id]').forEach(btn => {
    btn.addEventListener('click', () => openEditModal(parseInt(btn.dataset.editId)));
  });
}

async function loadSummary() {
  const entries = await getFilteredEntries('summary');
  const hourlyRate = settings.hourlyRate || 107.93;
  
  const totalHours = entries.reduce((sum, e) => sum + e.totalHours, 0);
  const dailyHours = {};
  entries.forEach(e => { dailyHours[e.date] = (dailyHours[e.date] || 0) + e.totalHours; });
  const daysWorked = Object.keys(dailyHours).length;
  const avgHours = daysWorked > 0 ? (totalHours / daysWorked) : 0;
  
  document.getElementById('totalHours').textContent = totalHours.toFixed(1);
  document.getElementById('totalPay').textContent = '£' + (totalHours * hourlyRate).toFixed(0);
  document.getElementById('daysWorked').textContent = daysWorked;
  document.getElementById('avgHours').textContent = avgHours.toFixed(1);
  
  // Heatmap
  renderHeatmap(dailyHours);
  
  // Weekly chart
  renderWeeklyChart(entries);
  
  // Monthly breakdown
  renderMonthlyTable(entries, totalHours, hourlyRate);
}

function renderHeatmap(dailyHours) {
  const wrap = document.getElementById('heatmapWrap');
  wrap.innerHTML = '';
  
  if (Object.keys(dailyHours).length === 0) {
    wrap.innerHTML = '<div style="text-align:center;color:#999;font-size:12px;padding:8px;">No data</div>';
    return;
  }
  
  const today = new Date();
  const startDate = new Date(today);
  startDate.setDate(startDate.getDate() - (20 * 7) - startDate.getDay());
  
  const maxHours = Math.max(...Object.values(dailyHours), 1);
  
  function getColor(hours) {
    if (!hours || hours === 0) return '#ebedf0';
    const r = hours / maxHours;
    if (r <= 0.25) return '#9be9a8';
    if (r <= 0.5) return '#40c463';
    if (r <= 0.75) return '#30a14e';
    return '#216e39';
  }
  
  const grid = document.createElement('div');
  grid.className = 'heatmap-grid';
  
  const d = new Date(startDate);
  while (d <= today) {
    const ds = d.toISOString().split('T')[0];
    const hrs = dailyHours[ds] || 0;
    const cell = document.createElement('div');
    cell.className = 'hm-cell';
    cell.style.background = getColor(hrs);
    if (hrs > 0) cell.title = `${ds}: ${hrs.toFixed(1)}h`;
    grid.appendChild(cell);
    d.setDate(d.getDate() + 1);
  }
  
  wrap.appendChild(grid);
}

let weeklyChartInstance = null;

function renderWeeklyChart(entries) {
  const weeklyHours = {};
  entries.forEach(e => {
    if (!e.date) return;
    const d = new Date(e.date + 'T00:00:00');
    const jan1 = new Date(d.getFullYear(), 0, 1);
    const weekNum = Math.ceil(((d - jan1) / 86400000 + jan1.getDay() + 1) / 7);
    const key = `${d.getFullYear()}-W${String(weekNum).padStart(2, '0')}`;
    weeklyHours[key] = (weeklyHours[key] || 0) + e.totalHours;
  });
  
  const labels = Object.keys(weeklyHours).sort();
  const data = labels.map(k => weeklyHours[k]);
  const sliceStart = Math.max(0, labels.length - 12);
  
  const canvas = document.getElementById('weeklyChart');
  
  if (weeklyChartInstance) {
    weeklyChartInstance.destroy();
    weeklyChartInstance = null;
  }
  
  if (labels.length === 0) return;
  
  // Load Chart.js dynamically if not loaded
  if (typeof Chart === 'undefined') {
    const script = document.createElement('script');
    script.src = 'chart.min.js';
    script.onload = () => createWeeklyChart(canvas, labels.slice(sliceStart), data.slice(sliceStart));
    document.head.appendChild(script);
  } else {
    createWeeklyChart(canvas, labels.slice(sliceStart), data.slice(sliceStart));
  }
}

function createWeeklyChart(canvas, labels, data) {
  weeklyChartInstance = new Chart(canvas, {
    type: 'bar',
    data: {
      labels: labels,
      datasets: [{
        label: 'Hours',
        data: data,
        backgroundColor: '#0078d4',
        borderRadius: 3,
        maxBarThickness: 30
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
        tooltip: {
          callbacks: {
            label: ctx => ctx.parsed.y.toFixed(1) + ' hours'
          }
        }
      },
      scales: {
        y: {
          beginAtZero: true,
          grid: { color: '#f0f0f0' },
          ticks: { callback: v => v + 'h', font: { size: 10 } }
        },
        x: {
          grid: { display: false },
          ticks: { font: { size: 9 } }
        }
      }
    }
  });
}

function renderMonthlyTable(entries, totalHours, hourlyRate) {
  const monthly = {};
  entries.forEach(e => {
    if (!e.date) return;
    const key = e.date.substring(0, 7);
    if (!monthly[key]) monthly[key] = { hours: 0, entries: 0 };
    monthly[key].hours += e.totalHours;
    monthly[key].entries++;
  });
  
  const sorted = Object.entries(monthly).sort((a, b) => b[0].localeCompare(a[0]));
  const container = document.getElementById('monthlyTable');
  
  if (sorted.length === 0) {
    container.innerHTML = '<div style="text-align:center;color:#999;font-size:12px;padding:8px;">No data</div>';
    return;
  }
  
  let html = `<table class="monthly-table"><thead><tr>
    <th>Month</th><th>Entries</th><th>Hours</th><th>Pay</th><th></th>
  </tr></thead><tbody>`;
  
  sorted.forEach(([month, data]) => {
    const pct = totalHours > 0 ? (data.hours / totalHours * 100) : 0;
    html += `<tr>
      <td>${month}</td>
      <td>${data.entries}</td>
      <td>${data.hours.toFixed(1)}</td>
      <td>£${(data.hours * hourlyRate).toFixed(0)}</td>
      <td><div class="bar-cell"><div class="bar-fill" style="width:${pct}%"></div></div></td>
    </tr>`;
  });
  
  html += '</tbody></table>';
  container.innerHTML = html;
}

// ── Calendar ──

async function renderCalendar() {
  const entries = await Storage.getEntries();
  const monthNames = ['January','February','March','April','May','June','July','August','September','October','November','December'];
  
  document.getElementById('calTitle').textContent = `${monthNames[calMonth]} ${calYear}`;
  
  // Filter entries for this month
  const prefix = `${calYear}-${String(calMonth + 1).padStart(2, '0')}`;
  const monthEntries = entries.filter(e => e.date && e.date.startsWith(prefix));
  
  // Group by day
  const byDay = {};
  monthEntries.forEach(e => {
    const day = parseInt(e.date.substring(8, 10));
    if (!byDay[day]) byDay[day] = [];
    byDay[day].push(e);
  });
  
  // Sort entries within each day by start time
  Object.values(byDay).forEach(dayEntries => {
    dayEntries.sort((a, b) => (a.startTime || '').localeCompare(b.startTime || ''));
  });
  
  // Build calendar grid
  const firstDay = new Date(calYear, calMonth, 1).getDay();
  const daysInMonth = new Date(calYear, calMonth + 1, 0).getDate();
  const startDay = firstDay === 0 ? 6 : firstDay - 1; // Monday start
  
  const today = new Date();
  const isCurrentMonth = today.getFullYear() === calYear && today.getMonth() === calMonth;
  
  const groupMap = {};
  groups.forEach(g => groupMap[g.id] = g);
  
  let html = '<div class="cal-weekdays">';
  ['Mon','Tue','Wed','Thu','Fri','Sat','Sun'].forEach(d => {
    html += `<div class="cal-wd">${d}</div>`;
  });
  html += '</div>';
  
  let dayNum = 1;
  let started = false;
  
  for (let week = 0; week < 6; week++) {
    if (dayNum > daysInMonth) break;
    html += '<div class="cal-week">';
    
    for (let dow = 0; dow < 7; dow++) {
      if (!started && dow < startDay) {
        html += '<div class="cal-cell empty"></div>';
        continue;
      }
      started = true;
      
      if (dayNum > daysInMonth) {
        html += '<div class="cal-cell empty"></div>';
        continue;
      }
      
      const dayEntries = byDay[dayNum] || [];
      const totalHrs = dayEntries.reduce((s, e) => s + e.totalHours, 0);
      const hasData = dayEntries.length > 0;
      const isToday = isCurrentMonth && dayNum === today.getDate();
      
      let cls = 'cal-cell';
      if (hasData) cls += ' has-data';
      if (isToday) cls += ' is-today';
      
      html += `<div class="${cls}" ${hasData ? `data-cal-day="${dayNum}"` : ''}>`;
      html += `<span class="day-num">${dayNum}</span>`;
      if (totalHrs > 0) html += `<span class="day-hrs">${totalHrs.toFixed(1)}h</span>`;
      if (dayEntries.length > 0) {
        html += `<div class="day-task">${escapeHtml(dayEntries[0].taskDescription.substring(0, 25))}</div>`;
        if (dayEntries.length > 1) {
          html += `<div class="day-task" style="color:#999;">+${dayEntries.length - 1} more</div>`;
        }
      }
      html += '</div>';
      dayNum++;
    }
    html += '</div>';
  }
  
  document.getElementById('calGrid').innerHTML = html;
  document.getElementById('dayDetail').style.display = 'none';
  
  // Attach day click handlers
  document.querySelectorAll('[data-cal-day]').forEach(cell => {
    cell.addEventListener('click', () => showDayDetail(parseInt(cell.dataset.calDay)));
  });
  
  // Store entries for detail view
  window._calByDay = byDay;
  window._calGroupMap = groupMap;
}

async function showDayDetail(day) {
  const entries = window._calByDay[day] || [];
  const groupMap = window._calGroupMap || {};
  const monthNames = ['January','February','March','April','May','June','July','August','September','October','November','December'];
  
  if (entries.length === 0) return;
  
  const projects = await Storage.getProjects();
  const projectMap = {};
  projects.forEach(p => projectMap[p.id] = p);
  
  document.getElementById('dayDetailTitle').textContent = `${day} ${monthNames[calMonth]} ${calYear}`;
  
  let html = '';
  let totalHrs = 0;
  entries.forEach(e => {
    totalHrs += e.totalHours;
    const group = groupMap[e.groupId] || { name: 'Unknown' };
    const project = e.projectId ? projectMap[e.projectId] : null;
    const label = project ? `${group.name} • ${project.name}` : group.name;
    html += `<div class="day-detail-entry">
      <div class="day-detail-task">${escapeHtml(e.taskDescription)}</div>
      <div class="day-detail-meta">
        <span>${escapeHtml(label)}</span>
        <span>${e.startTime} – ${e.endTime}</span>
        <span class="day-detail-hrs">${e.totalHours.toFixed(1)}h</span>
      </div>
    </div>`;
  });
  
  html += `<div class="day-detail-entry" style="background:#f8f9fa;">
    <div class="day-detail-meta">
      <span style="font-weight:600;color:#333;">Total</span>
      <span></span>
      <span class="day-detail-hrs">${totalHrs.toFixed(1)}h</span>
    </div>
  </div>`;
  
  document.getElementById('dayDetailContent').innerHTML = html;
  document.getElementById('dayDetail').style.display = 'block';
}

// ── Shared functions ──

async function onGroupChange() {
  const groupId = document.getElementById('group').value;
  const projectFormGroup = document.getElementById('projectFormGroup');
  const projectSelect = document.getElementById('project');
  
  if (!groupId) {
    projectFormGroup.style.display = 'none';
    projectSelect.innerHTML = '<option value="">No project</option>';
    return;
  }
  
  const projects = await Storage.getProjectsByGroup(parseInt(groupId));
  
  if (projects.length === 0) {
    projectFormGroup.style.display = 'none';
    projectSelect.innerHTML = '<option value="">No project</option>';
    return;
  }
  
  projectSelect.innerHTML = '<option value="">No project</option>';
  projects.forEach(p => {
    const option = document.createElement('option');
    option.value = p.id;
    option.textContent = p.name;
    projectSelect.appendChild(option);
  });
  projectFormGroup.style.display = 'block';
}

async function submitEntry() {
  const task = document.getElementById('task').value.trim();
  const groupId = document.getElementById('group').value;
  const entryDate = document.getElementById('entryDate').value;
  const startTime = document.getElementById('startTime').value;
  const endTime = document.getElementById('endTime').value;
  
  if (!task) { showMessage('Please enter a task description', 'error'); return; }
  if (!groupId) { showMessage('Please select a research group', 'error'); return; }
  if (!entryDate) { showMessage('Please select a date', 'error'); return; }
  if (!startTime || !endTime) { showMessage('Please enter start and end times', 'error'); return; }
  
  const btn = document.getElementById('submitBtn');
  btn.disabled = true;
  btn.textContent = 'Saving...';
  
  try {
    const projectId = document.getElementById('project').value ? parseInt(document.getElementById('project').value) : null;
    const entry = await Storage.addEntry(parseInt(groupId), task, entryDate, startTime, endTime, projectId);
    showMessage(`Logged ${entry.totalHours} hours`, 'success');
    document.getElementById('task').value = '';
    initializeLogPanel();
  } catch (error) {
    showMessage('Failed to save: ' + error.message, 'error');
  } finally {
    btn.disabled = false;
    btn.textContent = 'Submit';
  }
}

async function exportCSV() {
  const hourlyRate = settings.hourlyRate || 107.93;
  const csv = await Storage.exportCSV(hourlyRate);
  const BOM = '\uFEFF';
  const blob = new Blob([BOM + csv], { type: 'text/csv;charset=utf-8' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `time-tracker-${new Date().toISOString().split('T')[0]}.csv`;
  a.click();
  URL.revokeObjectURL(url);
}

function openSettings() { chrome.runtime.openOptionsPage(); }

function showMessage(text, type) {
  const el = document.getElementById('logMessage');
  el.textContent = text;
  el.className = 'message ' + type;
  if (type === 'success') setTimeout(() => el.className = 'message', 3000);
}

function formatTime(date) { return date.toTimeString().slice(0, 5); }

function escapeHtml(text) {
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}

async function deleteEntry(entryId) {
  if (!confirm('Delete this entry?')) return;
  try {
    await Storage.deleteEntry(entryId);
    loadEntries();
    loadSummary();
  } catch (error) {
    alert('Failed to delete entry: ' + error.message);
  }
}

// ── Edit Entry Modal ──

let editingEntryId = null;

async function openEditModal(entryId) {
  const entries = await Storage.getEntries();
  const entry = entries.find(e => e.id === entryId);
  if (!entry) return;
  
  editingEntryId = entryId;
  
  // Populate group picker
  const groupSelect = document.getElementById('editGroup');
  groupSelect.innerHTML = '';
  groups.forEach(g => {
    const opt = document.createElement('option');
    opt.value = g.id;
    opt.textContent = g.name;
    if (g.id === entry.groupId) opt.selected = true;
    groupSelect.appendChild(opt);
  });
  
  // Load projects for current group
  await loadEditProjects(entry.groupId, entry.projectId);
  
  // Populate fields
  document.getElementById('editTask').value = entry.taskDescription;
  document.getElementById('editDate').value = entry.date;
  document.getElementById('editStart').value = entry.startTime;
  document.getElementById('editEnd').value = entry.endTime;
  
  document.getElementById('editModal').style.display = 'block';
}

async function loadEditProjects(groupId, selectedProjectId) {
  const projectSelect = document.getElementById('editProject');
  projectSelect.innerHTML = '<option value="">None</option>';
  
  if (groupId) {
    const projects = await Storage.getProjectsByGroup(parseInt(groupId), true);
    projects.forEach(p => {
      const opt = document.createElement('option');
      opt.value = p.id;
      opt.textContent = p.name + (p.archived ? ' (archived)' : '');
      if (p.id === selectedProjectId) opt.selected = true;
      projectSelect.appendChild(opt);
    });
  }
}

function closeEditModal() {
  document.getElementById('editModal').style.display = 'none';
  editingEntryId = null;
}

async function saveEditEntry() {
  if (!editingEntryId) return;
  
  const updates = {
    groupId: parseInt(document.getElementById('editGroup').value),
    projectId: document.getElementById('editProject').value ? parseInt(document.getElementById('editProject').value) : null,
    taskDescription: document.getElementById('editTask').value.trim(),
    date: document.getElementById('editDate').value,
    startTime: document.getElementById('editStart').value,
    endTime: document.getElementById('editEnd').value
  };
  
  if (!updates.taskDescription) { alert('Task description required'); return; }
  if (!updates.date || !updates.startTime || !updates.endTime) { alert('Date and times required'); return; }
  
  await Storage.updateEntry(editingEntryId, updates);
  closeEditModal();
  loadEntries();
  loadSummary();
}

// Wire up edit modal buttons on load
document.addEventListener('DOMContentLoaded', () => {
  document.getElementById('editCancelBtn').addEventListener('click', closeEditModal);
  document.getElementById('editSaveBtn').addEventListener('click', saveEditEntry);
  document.getElementById('editGroup').addEventListener('change', async function() {
    await loadEditProjects(parseInt(this.value), null);
  });
  document.getElementById('editModal').addEventListener('click', function(e) {
    if (e.target === this) closeEditModal();
  });
});
