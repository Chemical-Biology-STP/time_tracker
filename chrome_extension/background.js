// Background service worker for Time Tracker Companion

const DEFAULT_SETTINGS = {
  backendUrl: 'http://localhost:5001',
  promptIntervalMinutes: 30,
  defaultGroupId: null,
  notificationsEnabled: true
};

// Initialize alarm on install
chrome.runtime.onInstalled.addListener(() => {
  console.log('Time Tracker Companion installed');
  initializeAlarm();
});

// Initialize alarm on startup
chrome.runtime.onStartup.addListener(() => {
  initializeAlarm();
});

// Handle alarm
chrome.alarms.onAlarm.addListener((alarm) => {
  if (alarm.name === 'timeTrackerReminder') {
    showReminder();
  }
});

// Handle notification click
chrome.notifications.onClicked.addListener((notificationId) => {
  if (notificationId === 'timeTrackerReminder') {
    // Open the popup by focusing/creating a window
    chrome.action.openPopup();
  }
});

async function initializeAlarm() {
  const settings = await getSettings();
  
  // Clear existing alarm
  await chrome.alarms.clear('timeTrackerReminder');
  
  // Create new alarm
  chrome.alarms.create('timeTrackerReminder', {
    delayInMinutes: settings.promptIntervalMinutes,
    periodInMinutes: settings.promptIntervalMinutes
  });
  
  console.log(`Alarm set for every ${settings.promptIntervalMinutes} minutes`);
}

async function showReminder() {
  const settings = await getSettings();
  
  if (!settings.notificationsEnabled) {
    return;
  }
  
  // Check if server is reachable
  const connected = await checkConnection(settings.backendUrl);
  
  if (connected) {
    chrome.notifications.create('timeTrackerReminder', {
      type: 'basic',
      iconUrl: 'icons/icon128.png',
      title: 'Time Tracker',
      message: 'Time to log what you\'ve been working on!',
      priority: 2,
      requireInteraction: true
    });
  }
}

async function checkConnection(backendUrl) {
  try {
    const response = await fetch(`${backendUrl}/api/health`, {
      method: 'GET',
      signal: AbortSignal.timeout(5000)
    });
    return response.ok;
  } catch {
    return false;
  }
}

async function getSettings() {
  return new Promise((resolve) => {
    chrome.storage.sync.get(DEFAULT_SETTINGS, (result) => {
      resolve(result);
    });
  });
}

// Listen for settings changes to update alarm
chrome.storage.onChanged.addListener((changes, namespace) => {
  if (namespace === 'sync' && changes.promptIntervalMinutes) {
    initializeAlarm();
  }
});

// Message handler for popup/options communication
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.action === 'getSettings') {
    getSettings().then(sendResponse);
    return true;
  }
  if (request.action === 'checkConnection') {
    checkConnection(request.url).then(sendResponse);
    return true;
  }
});
