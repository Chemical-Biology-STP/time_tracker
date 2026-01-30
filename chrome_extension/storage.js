// Storage utilities for Time Tracker
// Uses Chrome sync storage - data syncs across devices with same Google account

const Storage = {
  // Get all research groups
  async getGroups() {
    const data = await chrome.storage.sync.get({ groups: [] });
    return data.groups;
  },

  // Save all groups
  async saveGroups(groups) {
    await chrome.storage.sync.set({ groups });
  },

  // Add a new group
  async addGroup(name, managerName = '', projectName = '') {
    const groups = await this.getGroups();
    const id = Date.now(); // Simple unique ID
    const newGroup = { id, name, managerName, projectName };
    groups.push(newGroup);
    await this.saveGroups(groups);
    return newGroup;
  },

  // Delete a group and its entries
  async deleteGroup(groupId) {
    const groups = await this.getGroups();
    const filtered = groups.filter(g => g.id !== groupId);
    await this.saveGroups(filtered);
    
    // Also delete entries for this group
    const entries = await this.getEntries();
    const filteredEntries = entries.filter(e => e.groupId !== groupId);
    await this.saveEntries(filteredEntries);
  },

  // Get all time entries
  async getEntries() {
    const data = await chrome.storage.sync.get({ entries: [] });
    return data.entries;
  },

  // Save all entries
  async saveEntries(entries) {
    await chrome.storage.sync.set({ entries });
  },

  // Add a new time entry
  async addEntry(groupId, taskDescription, date, startTime, endTime) {
    const entries = await this.getEntries();
    
    // Calculate hours
    const [startH, startM] = startTime.split(':').map(Number);
    const [endH, endM] = endTime.split(':').map(Number);
    const totalHours = ((endH * 60 + endM) - (startH * 60 + startM)) / 60;
    
    const id = Date.now();
    const newEntry = {
      id,
      groupId,
      taskDescription,
      date,
      startTime,
      endTime,
      totalHours: Math.round(totalHours * 100) / 100
    };
    
    entries.push(newEntry);
    await this.saveEntries(entries);
    return newEntry;
  },

  // Delete an entry
  async deleteEntry(entryId) {
    const entries = await this.getEntries();
    const filtered = entries.filter(e => e.id !== entryId);
    await this.saveEntries(filtered);
  },

  // Get entries for a specific group
  async getEntriesByGroup(groupId) {
    const entries = await this.getEntries();
    return entries.filter(e => e.groupId === groupId);
  },

  // Get entries for a date range
  async getEntriesByDateRange(startDate, endDate) {
    const entries = await this.getEntries();
    return entries.filter(e => e.date >= startDate && e.date <= endDate);
  },

  // Get settings
  async getSettings() {
    const data = await chrome.storage.sync.get({
      promptIntervalMinutes: 30,
      defaultGroupId: null,
      notificationsEnabled: true,
      hourlyRate: 107.93
    });
    return data;
  },

  // Save settings
  async saveSettings(settings) {
    await chrome.storage.sync.set(settings);
  },

  // Export all data as JSON
  async exportData() {
    const groups = await this.getGroups();
    const entries = await this.getEntries();
    const settings = await this.getSettings();
    
    return {
      exportDate: new Date().toISOString(),
      groups,
      entries,
      settings
    };
  },

  // Export entries as CSV
  async exportCSV() {
    const groups = await this.getGroups();
    const entries = await this.getEntries();
    
    const groupMap = {};
    groups.forEach(g => groupMap[g.id] = g);
    
    const headers = ['Date', 'Group', 'Project', 'Manager', 'Task', 'Start', 'End', 'Hours'];
    const rows = entries.map(e => {
      const group = groupMap[e.groupId] || { name: 'Unknown', projectName: '', managerName: '' };
      return [
        e.date,
        group.name,
        group.projectName,
        group.managerName,
        `"${e.taskDescription.replace(/"/g, '""')}"`,
        e.startTime,
        e.endTime,
        e.totalHours
      ].join(',');
    });
    
    return [headers.join(','), ...rows].join('\n');
  },

  // Get summary statistics
  async getSummary(groupId = null) {
    let entries = await this.getEntries();
    
    if (groupId) {
      entries = entries.filter(e => e.groupId === groupId);
    }
    
    const totalHours = entries.reduce((sum, e) => sum + e.totalHours, 0);
    const totalEntries = entries.length;
    
    // Group by date
    const byDate = {};
    entries.forEach(e => {
      byDate[e.date] = (byDate[e.date] || 0) + e.totalHours;
    });
    
    return {
      totalHours: Math.round(totalHours * 100) / 100,
      totalEntries,
      byDate
    };
  }
};

// Make available globally
if (typeof window !== 'undefined') {
  window.Storage = Storage;
}
