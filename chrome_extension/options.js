// Options page script for Time Tracker

let groups = [];

document.addEventListener('DOMContentLoaded', async () => {
  await loadSettings();
  await loadGroups();
  
  // Event listeners
  document.getElementById('saveBtn').addEventListener('click', saveSettings);
  document.getElementById('addGroupBtn').addEventListener('click', showNewGroupForm);
  document.getElementById('saveGroupBtn').addEventListener('click', saveNewGroup);
  document.getElementById('cancelGroupBtn').addEventListener('click', hideNewGroupForm);
  document.getElementById('exportJsonBtn').addEventListener('click', exportJSON);
  document.getElementById('exportCsvBtn').addEventListener('click', exportCSV);
  document.getElementById('clearDataBtn').addEventListener('click', clearAllData);
});

async function loadSettings() {
  const settings = await Storage.getSettings();
  
  document.getElementById('interval').value = settings.promptIntervalMinutes;
  document.getElementById('notifications').checked = settings.notificationsEnabled;
  document.getElementById('hourlyRate').value = settings.hourlyRate || 107.93;
}

async function loadGroups() {
  groups = await Storage.getGroups();
  const settings = await Storage.getSettings();
  
  // Update default group dropdown
  const defaultSelect = document.getElementById('defaultGroup');
  defaultSelect.innerHTML = '<option value="">None</option>';
  groups.forEach(g => {
    const option = document.createElement('option');
    option.value = g.id;
    option.textContent = g.name;
    if (g.id === settings.defaultGroupId) option.selected = true;
    defaultSelect.appendChild(option);
  });
  
  // Update groups list
  const list = document.getElementById('groupsList');
  
  if (groups.length === 0) {
    list.innerHTML = '<div class="empty-state">No groups yet. Add one to get started!</div>';
    return;
  }
  
  list.innerHTML = groups.map(g => `
    <div class="group-item">
      <div class="group-info">
        <div class="group-name">${escapeHtml(g.name)}</div>
        <div class="group-meta">
          ${g.projectName ? escapeHtml(g.projectName) : ''}
          ${g.managerName ? ' • ' + escapeHtml(g.managerName) : ''}
        </div>
      </div>
      <button class="delete-btn" data-id="${g.id}" title="Delete group">🗑️</button>
    </div>
  `).join('');
  
  // Add delete handlers
  list.querySelectorAll('.delete-btn').forEach(btn => {
    btn.addEventListener('click', () => deleteGroup(parseInt(btn.dataset.id)));
  });
}

async function saveSettings() {
  const settings = {
    promptIntervalMinutes: parseInt(document.getElementById('interval').value),
    notificationsEnabled: document.getElementById('notifications').checked,
    hourlyRate: parseFloat(document.getElementById('hourlyRate').value) || 107.93,
    defaultGroupId: document.getElementById('defaultGroup').value ? 
      parseInt(document.getElementById('defaultGroup').value) : null
  };
  
  await Storage.saveSettings(settings);
  
  // Show saved message
  const msg = document.getElementById('savedMessage');
  msg.classList.add('show');
  setTimeout(() => msg.classList.remove('show'), 2000);
}

function showNewGroupForm() {
  document.getElementById('newGroupForm').classList.add('show');
  document.getElementById('newGroupName').focus();
}

function hideNewGroupForm() {
  document.getElementById('newGroupForm').classList.remove('show');
  document.getElementById('newGroupName').value = '';
  document.getElementById('newManagerName').value = '';
  document.getElementById('newProjectName').value = '';
}

async function saveNewGroup() {
  const name = document.getElementById('newGroupName').value.trim();
  const managerName = document.getElementById('newManagerName').value.trim();
  const projectName = document.getElementById('newProjectName').value.trim();
  
  if (!name) {
    alert('Please enter a group name');
    return;
  }
  
  await Storage.addGroup(name, managerName, projectName);
  hideNewGroupForm();
  await loadGroups();
}

async function deleteGroup(groupId) {
  const group = groups.find(g => g.id === groupId);
  if (!confirm(`Delete "${group.name}" and all its entries?`)) {
    return;
  }
  
  await Storage.deleteGroup(groupId);
  
  // Clear default if deleted
  const settings = await Storage.getSettings();
  if (settings.defaultGroupId === groupId) {
    await Storage.saveSettings({ ...settings, defaultGroupId: null });
  }
  
  await loadGroups();
}

async function exportJSON() {
  const data = await Storage.exportData();
  const json = JSON.stringify(data, null, 2);
  
  const blob = new Blob([json], { type: 'application/json' });
  const url = URL.createObjectURL(blob);
  
  const a = document.createElement('a');
  a.href = url;
  a.download = `time-tracker-backup-${new Date().toISOString().split('T')[0]}.json`;
  a.click();
  
  URL.revokeObjectURL(url);
}

async function exportCSV() {
  const settings = await Storage.getSettings();
  const hourlyRate = settings.hourlyRate || 107.93;
  const csv = await Storage.exportCSV(hourlyRate);
  
  // Add UTF-8 BOM for Excel compatibility
  const BOM = '\uFEFF';
  const blob = new Blob([BOM + csv], { type: 'text/csv;charset=utf-8' });
  const url = URL.createObjectURL(blob);
  
  const a = document.createElement('a');
  a.href = url;
  a.download = `time-tracker-${new Date().toISOString().split('T')[0]}.csv`;
  a.click();
  
  URL.revokeObjectURL(url);
}

async function clearAllData() {
  if (!confirm('Are you sure you want to delete ALL data? This cannot be undone.')) {
    return;
  }
  
  if (!confirm('Really delete everything? Last chance!')) {
    return;
  }
  
  await chrome.storage.sync.clear();
  await loadGroups();
  await loadSettings();
  
  alert('All data has been cleared.');
}

function escapeHtml(text) {
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}
