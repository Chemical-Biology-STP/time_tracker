// Options page script for Time Tracker Companion

let groups = [];

document.addEventListener('DOMContentLoaded', async () => {
  await loadSettings();
  await loadGroups();
  await checkConnection();
  
  // Event listeners
  document.getElementById('saveBtn').addEventListener('click', saveSettings);
  document.getElementById('testBtn').addEventListener('click', checkConnection);
  document.getElementById('backendUrl').addEventListener('change', () => {
    loadGroups();
    checkConnection();
  });
});

async function loadSettings() {
  const settings = await chrome.storage.sync.get({
    backendUrl: 'http://localhost:5001',
    promptIntervalMinutes: 30,
    defaultGroupId: null,
    notificationsEnabled: true
  });
  
  document.getElementById('backendUrl').value = settings.backendUrl;
  document.getElementById('interval').value = settings.promptIntervalMinutes;
  document.getElementById('notifications').checked = settings.notificationsEnabled;
}

async function saveSettings() {
  const settings = {
    backendUrl: document.getElementById('backendUrl').value.trim(),
    promptIntervalMinutes: parseInt(document.getElementById('interval').value),
    defaultGroupId: document.getElementById('defaultGroup').value ? 
      parseInt(document.getElementById('defaultGroup').value) : null,
    notificationsEnabled: document.getElementById('notifications').checked
  };
  
  await chrome.storage.sync.set(settings);
  
  // Show saved message
  const savedMessage = document.getElementById('savedMessage');
  savedMessage.classList.add('show');
  setTimeout(() => savedMessage.classList.remove('show'), 2000);
}

async function loadGroups() {
  const backendUrl = document.getElementById('backendUrl').value.trim();
  const defaultGroupSelect = document.getElementById('defaultGroup');
  const groupsList = document.getElementById('groupsList');
  
  try {
    const response = await fetch(`${backendUrl}/api/groups`);
    if (!response.ok) throw new Error('Failed to fetch');
    
    groups = await response.json();
    
    // Get current default
    const settings = await chrome.storage.sync.get({ defaultGroupId: null });
    
    // Update default group dropdown
    defaultGroupSelect.innerHTML = '<option value="">None</option>';
    groups.forEach(group => {
      const option = document.createElement('option');
      option.value = group.id;
      option.textContent = group.name;
      if (group.id === settings.defaultGroupId) {
        option.selected = true;
      }
      defaultGroupSelect.appendChild(option);
    });
    
    // Update groups list
    if (groups.length === 0) {
      groupsList.innerHTML = '<div class="group-item" style="color: #888;">No groups available</div>';
    } else {
      groupsList.innerHTML = groups.map(group => `
        <div class="group-item">
          <div>
            <div class="group-name">${escapeHtml(group.name)}</div>
            <div class="group-project">${escapeHtml(group.project_name || '')}</div>
          </div>
          <button class="delete-btn" data-id="${group.id}" title="Delete group">🗑️</button>
        </div>
      `).join('');
      
      // Add delete handlers
      groupsList.querySelectorAll('.delete-btn').forEach(btn => {
        btn.addEventListener('click', () => deleteGroup(parseInt(btn.dataset.id)));
      });
    }
    
  } catch (error) {
    defaultGroupSelect.innerHTML = '<option value="">Failed to load</option>';
    groupsList.innerHTML = '<div class="group-item" style="color: #e74c3c;">Could not connect to server</div>';
  }
}

async function deleteGroup(groupId) {
  const group = groups.find(g => g.id === groupId);
  if (!confirm(`Delete "${group.name}" and all its entries?`)) {
    return;
  }
  
  const backendUrl = document.getElementById('backendUrl').value.trim();
  
  try {
    const response = await fetch(`${backendUrl}/api/groups/${groupId}`, {
      method: 'DELETE'
    });
    
    if (response.ok) {
      // Clear default if it was deleted
      const settings = await chrome.storage.sync.get({ defaultGroupId: null });
      if (settings.defaultGroupId === groupId) {
        await chrome.storage.sync.set({ defaultGroupId: null });
      }
      await loadGroups();
    } else {
      alert('Failed to delete group');
    }
  } catch (error) {
    alert('Error deleting group: ' + error.message);
  }
}

async function checkConnection() {
  const backendUrl = document.getElementById('backendUrl').value.trim();
  const statusDot = document.getElementById('statusDot');
  const statusText = document.getElementById('statusText');
  
  statusDot.className = 'status-dot checking';
  statusText.textContent = 'Checking...';
  
  try {
    const response = await fetch(`${backendUrl}/api/health`, {
      signal: AbortSignal.timeout(5000)
    });
    
    if (response.ok) {
      statusDot.className = 'status-dot connected';
      statusText.textContent = 'Connected';
    } else {
      throw new Error('Not OK');
    }
  } catch {
    statusDot.className = 'status-dot disconnected';
    statusText.textContent = 'Disconnected';
  }
}

function escapeHtml(text) {
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}
