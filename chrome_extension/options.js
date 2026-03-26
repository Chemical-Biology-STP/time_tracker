// Options page script for Time Tracker

let groups = [];

document.addEventListener('DOMContentLoaded', async () => {
  // Display extension version
  const versionEl = document.getElementById('extensionVersion');
  if (versionEl) {
    versionEl.textContent = chrome.runtime.getManifest().version;
  }
  
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
  
  // Project event listeners
  document.getElementById('projectGroupFilter').addEventListener('change', loadProjects);
  document.getElementById('addProjectBtn').addEventListener('click', showNewProjectForm);
  document.getElementById('saveProjectBtn').addEventListener('click', saveNewProject);
  document.getElementById('cancelProjectBtn').addEventListener('click', hideNewProjectForm);
});

async function loadSettings() {
  const settings = await Storage.getSettings();
  
  document.getElementById('interval').value = settings.promptIntervalMinutes;
  document.getElementById('notifications').checked = settings.notificationsEnabled;
  document.getElementById('hourlyRate').value = settings.hourlyRate || 107.93;
  
  // Working days (default Mon-Fri: 1,2,3,4,5)
  const workingDays = settings.workingDays || [1, 2, 3, 4, 5];
  document.querySelectorAll('.day-btn').forEach(btn => {
    const day = parseInt(btn.dataset.day);
    if (workingDays.includes(day)) {
      btn.classList.add('active');
    }
    btn.addEventListener('click', () => btn.classList.toggle('active'));
  });
  
  // Working hours
  document.getElementById('workStartTime').value = settings.workStartTime || '09:00';
  document.getElementById('workEndTime').value = settings.workEndTime || '17:00';
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
  
  // Update project group filter
  const projectGroupFilter = document.getElementById('projectGroupFilter');
  const currentProjectGroup = projectGroupFilter.value;
  projectGroupFilter.innerHTML = '<option value="">Select a group</option>';
  groups.forEach(g => {
    const option = document.createElement('option');
    option.value = g.id;
    option.textContent = g.name;
    projectGroupFilter.appendChild(option);
  });
  if (currentProjectGroup) {
    projectGroupFilter.value = currentProjectGroup;
  }
  
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
  // Get selected working days
  const workingDays = [];
  document.querySelectorAll('.day-btn.active').forEach(btn => {
    workingDays.push(parseInt(btn.dataset.day));
  });
  
  const settings = {
    promptIntervalMinutes: parseInt(document.getElementById('interval').value),
    notificationsEnabled: document.getElementById('notifications').checked,
    hourlyRate: parseFloat(document.getElementById('hourlyRate').value) || 107.93,
    defaultGroupId: document.getElementById('defaultGroup').value ? 
      parseInt(document.getElementById('defaultGroup').value) : null,
    workingDays: workingDays,
    workStartTime: document.getElementById('workStartTime').value,
    workEndTime: document.getElementById('workEndTime').value
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

// ── Project Management ──

async function loadProjects() {
  const groupId = document.getElementById('projectGroupFilter').value;
  const list = document.getElementById('projectsList');
  const addBtn = document.getElementById('addProjectBtn');
  
  if (!groupId) {
    list.innerHTML = '<div class="empty-state">Select a group to see projects</div>';
    addBtn.disabled = true;
    return;
  }
  
  addBtn.disabled = false;
  const projects = await Storage.getProjectsByGroup(parseInt(groupId), true);
  
  if (projects.length === 0) {
    list.innerHTML = '<div class="empty-state">No projects yet. Add one to get started!</div>';
    return;
  }
  
  list.innerHTML = projects.map(p => `
    <div class="project-item ${p.archived ? 'archived' : ''}">
      <span class="project-name">${escapeHtml(p.name)}${p.archived ? ' (archived)' : ''}</span>
      <div class="project-actions">
        <button class="archive-btn" data-archive-id="${p.id}" data-archived="${p.archived}" title="${p.archived ? 'Unarchive' : 'Archive'}">
          ${p.archived ? '📂' : '📁'}
        </button>
        <button class="delete-btn" data-delete-project-id="${p.id}" title="Delete project">🗑️</button>
      </div>
    </div>
  `).join('');
  
  // Archive handlers
  list.querySelectorAll('[data-archive-id]').forEach(btn => {
    btn.addEventListener('click', async () => {
      const id = parseInt(btn.dataset.archiveId);
      const isArchived = btn.dataset.archived === 'true';
      await Storage.archiveProject(id, !isArchived);
      await loadProjects();
    });
  });
  
  // Delete handlers
  list.querySelectorAll('[data-delete-project-id]').forEach(btn => {
    btn.addEventListener('click', async () => {
      const id = parseInt(btn.dataset.deleteProjectId);
      if (!confirm('Delete this project? Entries will keep their data but lose the project link.')) return;
      await Storage.deleteProject(id);
      await loadProjects();
    });
  });
}

function showNewProjectForm() {
  document.getElementById('newProjectForm').classList.add('show');
  document.getElementById('newProjectNameInput').focus();
}

function hideNewProjectForm() {
  document.getElementById('newProjectForm').classList.remove('show');
  document.getElementById('newProjectNameInput').value = '';
}

async function saveNewProject() {
  const name = document.getElementById('newProjectNameInput').value.trim();
  const groupId = document.getElementById('projectGroupFilter').value;
  
  if (!name) {
    alert('Please enter a project name');
    return;
  }
  if (!groupId) {
    alert('Please select a group first');
    return;
  }
  
  await Storage.addProject(parseInt(groupId), name);
  hideNewProjectForm();
  await loadProjects();
}
