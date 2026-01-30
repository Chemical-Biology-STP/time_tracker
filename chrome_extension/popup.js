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
  document.getElementById('entriesYearFilter').addEventListener('change', loadEntries);
  document.getElementById('entriesMonthFilter').addEventListener('change', loadEntries);
  document.getElementById('summaryGroupFilter').addEventListener('change', loadSummary);
  document.getElementById('summaryYearFilter').addEventListener('change', loadSummary);
  document.getElementById('summaryMonthFilter').addEventListener('change', loadSummary);
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
  
  populateDateFilters('entries');
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
  
  populateDateFilters('summary');
  loadSummary();
}

async function populateDateFilters(prefix) {
  const entries = await Storage.getEntries();
  
  // Get unique years and months from entries
  const years = new Set();
  entries.forEach(e => {
    if (e.date) {
      years.add(e.date.substring(0, 4));
    }
  });
  
  // Populate year filter
  const yearFilter = document.getElementById(`${prefix}YearFilter`);
  yearFilter.innerHTML = '<option value="">All Years</option>';
  Array.from(years).sort().reverse().forEach(year => {
    const option = document.createElement('option');
    option.value = year;
    option.textContent = year;
    yearFilter.appendChild(option);
  });
  
  // Populate month filter
  const monthFilter = document.getElementById(`${prefix}MonthFilter`);
  monthFilter.innerHTML = '<option value="">All Months</option>';
  const months = [
    { value: '01', label: 'January' },
    { value: '02', label: 'February' },
    { value: '03', label: 'March' },
    { value: '04', label: 'April' },
    { value: '05', label: 'May' },
    { value: '06', label: 'June' },
    { value: '07', label: 'July' },
    { value: '08', label: 'August' },
    { value: '09', label: 'September' },
    { value: '10', label: 'October' },
    { value: '11', label: 'November' },
    { value: '12', label: 'December' }
  ];
  months.forEach(m => {
    const option = document.createElement('option');
    option.value = m.value;
    option.textContent = m.label;
    monthFilter.appendChild(option);
  });
}

async function loadEntries() {
  const groupId = document.getElementById('entriesGroupFilter').value;
  const year = document.getElementById('entriesYearFilter').value;
  const month = document.getElementById('entriesMonthFilter').value;
  let entries = await Storage.getEntries();
  
  if (groupId) {
    entries = entries.filter(e => e.groupId === parseInt(groupId));
  }
  
  if (year) {
    entries = entries.filter(e => e.date && e.date.startsWith(year));
  }
  
  if (month) {
    entries = entries.filter(e => e.date && e.date.substring(5, 7) === month);
  }
  
  // Sort by date descending
  entries.sort((a, b) => b.date.localeCompare(a.date) || b.id - a.id);
  
  const container = document.getElementById('entriesList');
  
  if (entries.length === 0) {
    container.innerHTML = '<div class="empty-state">No entries found</div>';
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
  const year = document.getElementById('summaryYearFilter').value;
  const month = document.getElementById('summaryMonthFilter').value;
  
  let entries = await Storage.getEntries();
  
  if (groupId) {
    entries = entries.filter(e => e.groupId === parseInt(groupId));
  }
  
  if (year) {
    entries = entries.filter(e => e.date && e.date.startsWith(year));
  }
  
  if (month) {
    entries = entries.filter(e => e.date && e.date.substring(5, 7) === month);
  }
  
  const totalHours = entries.reduce((sum, e) => sum + e.totalHours, 0);
  const totalEntries = entries.length;
  
  document.getElementById('totalHours').textContent = totalHours.toFixed(1);
  document.getElementById('totalEntries').textContent = totalEntries;
  
  // Calculate pay
  const hourlyRate = settings.hourlyRate || 107.93;
  const totalPay = totalHours * hourlyRate;
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
