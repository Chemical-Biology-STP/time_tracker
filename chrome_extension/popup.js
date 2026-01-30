// Popup script for Time Tracker

let groups = [];
let settings = {};

document.addEventListener('DOMContentLoaded', async () => {
  // Load data
  groups = await Storage.getGroups();
  settings = await Storage.getSettings();
  
  // Initialize UI
  initializeTabs();
  initializeLogPanel();
  initializeEntriesPanel();
  initializeSummaryPanel();
  
  // Event listeners
  document.getElementById('submitBtn').addEventListener('click', submitEntry);
  document.getElementById('settingsBtn').addEventListener('click', openSettings);
  document.getElementById('exportBtn').addEventListener('click', exportCSV);
  document.getElementById('entriesGroupFilter').addEventListener('change', loadEntries);
  document.getElementById('summaryGroupFilter').addEventListener('change', loadSummary);
});

function initializeTabs() {
  document.querySelectorAll('.tab').forEach(tab => {
    tab.addEventListener('click', () => {
      // Update tabs
      document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
      tab.classList.add('active');
      
      // Update panels
      document.querySelectorAll('.panel').forEach(p => p.classList.remove('active'));
      document.getElementById(tab.dataset.panel).classList.add('active');
      
      // Refresh data when switching tabs
      if (tab.dataset.panel === 'entries') loadEntries();
      if (tab.dataset.panel === 'summary') loadSummary();
    });
  });
}

function initializeLogPanel() {
  // Populate groups dropdown
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
  
  // Set default times
  const now = new Date();
  const intervalMs = settings.promptIntervalMinutes * 60 * 1000;
  const start = new Date(now.getTime() - intervalMs);
  
  document.getElementById('endTime').value = formatTime(now);
  document.getElementById('startTime').value = formatTime(start);
}

function initializeEntriesPanel() {
  // Populate filter dropdown
  const filter = document.getElementById('entriesGroupFilter');
  filter.innerHTML = '<option value="">All Groups</option>';
  groups.forEach(g => {
    const option = document.createElement('option');
    option.value = g.id;
    option.textContent = g.name;
    filter.appendChild(option);
  });
  
  loadEntries();
}

function initializeSummaryPanel() {
  // Populate filter dropdown
  const filter = document.getElementById('summaryGroupFilter');
  filter.innerHTML = '<option value="">All Groups</option>';
  groups.forEach(g => {
    const option = document.createElement('option');
    option.value = g.id;
    option.textContent = g.name;
    filter.appendChild(option);
  });
  
  loadSummary();
}

async function loadEntries() {
  const groupId = document.getElementById('entriesGroupFilter').value;
  let entries = await Storage.getEntries();
  
  if (groupId) {
    entries = entries.filter(e => e.groupId === parseInt(groupId));
  }
  
  // Sort by date descending
  entries.sort((a, b) => b.date.localeCompare(a.date) || b.id - a.id);
  
  const container = document.getElementById('entriesList');
  
  if (entries.length === 0) {
    container.innerHTML = '<div class="empty-state">No entries yet</div>';
    return;
  }
  
  const groupMap = {};
  groups.forEach(g => groupMap[g.id] = g);
  
  container.innerHTML = entries.slice(0, 50).map(e => {
    const group = groupMap[e.groupId] || { name: 'Unknown' };
    return `
      <div class="entry-item">
        <div class="entry-date">${e.date} • ${group.name}</div>
        <div class="entry-task">${escapeHtml(e.taskDescription)}</div>
        <div class="entry-meta">
          <span>${e.startTime} - ${e.endTime}</span>
          <span class="entry-hours">${e.totalHours}h</span>
        </div>
      </div>
    `;
  }).join('');
}

async function loadSummary() {
  const groupId = document.getElementById('summaryGroupFilter').value;
  const summary = await Storage.getSummary(groupId ? parseInt(groupId) : null);
  
  document.getElementById('totalHours').textContent = summary.totalHours.toFixed(1);
  document.getElementById('totalEntries').textContent = summary.totalEntries;
  
  // Calculate pay
  const hourlyRate = settings.hourlyRate || 107.93;
  const totalPay = summary.totalHours * hourlyRate;
  document.getElementById('totalPay').textContent = '£' + totalPay.toFixed(2);
}

async function submitEntry() {
  const task = document.getElementById('task').value.trim();
  const groupId = document.getElementById('group').value;
  const startTime = document.getElementById('startTime').value;
  const endTime = document.getElementById('endTime').value;
  
  // Validation
  if (!task) {
    showMessage('Please enter a task description', 'error');
    return;
  }
  
  if (!groupId) {
    showMessage('Please select a research group', 'error');
    return;
  }
  
  if (!startTime || !endTime) {
    showMessage('Please enter start and end times', 'error');
    return;
  }
  
  // Disable button
  const btn = document.getElementById('submitBtn');
  btn.disabled = true;
  btn.textContent = 'Saving...';
  
  try {
    const entry = await Storage.addEntry(
      parseInt(groupId),
      task,
      new Date().toISOString().split('T')[0],
      startTime,
      endTime
    );
    
    showMessage(`Logged ${entry.totalHours} hours`, 'success');
    
    // Clear form
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
  const csv = await Storage.exportCSV();
  
  const blob = new Blob([csv], { type: 'text/csv' });
  const url = URL.createObjectURL(blob);
  
  const a = document.createElement('a');
  a.href = url;
  a.download = `time-tracker-${new Date().toISOString().split('T')[0]}.csv`;
  a.click();
  
  URL.revokeObjectURL(url);
}

function openSettings() {
  chrome.runtime.openOptionsPage();
}

function showMessage(text, type) {
  const el = document.getElementById('logMessage');
  el.textContent = text;
  el.className = 'message ' + type;
  
  if (type === 'success') {
    setTimeout(() => el.className = 'message', 3000);
  }
}

function formatTime(date) {
  return date.toTimeString().slice(0, 5);
}

function escapeHtml(text) {
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}
