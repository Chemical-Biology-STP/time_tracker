// Popup script for Time Tracker Companion

let settings = {};
let groups = [];

document.addEventListener('DOMContentLoaded', async () => {
  // Load settings
  settings = await chrome.storage.sync.get({
    backendUrl: 'http://localhost:5001',
    promptIntervalMinutes: 30,
    defaultGroupId: null
  });
  
  // Set up UI
  initializeTimeFields();
  await loadGroups();
  await checkConnection();
  
  // Event listeners
  document.getElementById('submitBtn').addEventListener('click', submitEntry);
  document.getElementById('settingsBtn').addEventListener('click', openSettings);
  document.getElementById('webLink').addEventListener('click', openWebUI);
});

function initializeTimeFields() {
  const now = new Date();
  const intervalMs = settings.promptIntervalMinutes * 60 * 1000;
  const start = new Date(now.getTime() - intervalMs);
  
  document.getElementById('endTime').value = formatTime(now);
  document.getElementById('startTime').value = formatTime(start);
}

function formatTime(date) {
  return date.toTimeString().slice(0, 5);
}

async function loadGroups() {
  const groupSelect = document.getElementById('group');
  
  try {
    const response = await fetch(`${settings.backendUrl}/api/groups`);
    if (!response.ok) throw new Error('Failed to fetch groups');
    
    groups = await response.json();
    
    groupSelect.innerHTML = '';
    
    if (groups.length === 0) {
      groupSelect.innerHTML = '<option value="">No groups available</option>';
      return;
    }
    
    groupSelect.innerHTML = '<option value="">Select a group</option>';
    groups.forEach(group => {
      const option = document.createElement('option');
      option.value = group.id;
      option.textContent = group.name;
      if (group.id === settings.defaultGroupId) {
        option.selected = true;
      }
      groupSelect.appendChild(option);
    });
    
  } catch (error) {
    groupSelect.innerHTML = '<option value="">Failed to load groups</option>';
    showError('Could not connect to server');
  }
}

async function checkConnection() {
  const statusDot = document.getElementById('statusDot');
  const statusText = document.getElementById('statusText');
  
  try {
    const response = await fetch(`${settings.backendUrl}/api/health`, {
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

async function submitEntry() {
  const task = document.getElementById('task').value.trim();
  const groupId = document.getElementById('group').value;
  const startTime = document.getElementById('startTime').value;
  const endTime = document.getElementById('endTime').value;
  
  // Validation
  if (!task) {
    showError('Please enter a task description');
    return;
  }
  
  if (!groupId) {
    showError('Please select a research group');
    return;
  }
  
  if (!startTime || !endTime) {
    showError('Please enter start and end times');
    return;
  }
  
  // Disable button
  const submitBtn = document.getElementById('submitBtn');
  submitBtn.disabled = true;
  submitBtn.textContent = 'Submitting...';
  hideError();
  hideSuccess();
  
  try {
    const response = await fetch(`${settings.backendUrl}/api/entries`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        research_group_id: parseInt(groupId),
        task_description: task,
        date: new Date().toISOString().split('T')[0],
        start_time: startTime,
        end_time: endTime
      })
    });
    
    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.error || 'Failed to create entry');
    }
    
    const result = await response.json();
    showSuccess(`Logged ${result.total_hours.toFixed(2)} hours`);
    
    // Clear form
    document.getElementById('task').value = '';
    initializeTimeFields();
    
  } catch (error) {
    showError(error.message);
  } finally {
    submitBtn.disabled = false;
    submitBtn.textContent = 'Submit';
  }
}

function showError(message) {
  const errorEl = document.getElementById('error');
  errorEl.textContent = message;
  errorEl.classList.add('show');
}

function hideError() {
  document.getElementById('error').classList.remove('show');
}

function showSuccess(message) {
  const successEl = document.getElementById('success');
  successEl.textContent = message;
  successEl.classList.add('show');
}

function hideSuccess() {
  document.getElementById('success').classList.remove('show');
}

function openSettings(e) {
  e.preventDefault();
  chrome.runtime.openOptionsPage();
}

function openWebUI(e) {
  e.preventDefault();
  chrome.tabs.create({ url: settings.backendUrl });
}
