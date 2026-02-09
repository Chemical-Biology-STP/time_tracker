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

  // Delete a group and its entries and projects
  async deleteGroup(groupId) {
    const groups = await this.getGroups();
    const filtered = groups.filter(g => g.id !== groupId);
    await this.saveGroups(filtered);
    
    // Also delete entries for this group
    const entries = await this.getEntries();
    const filteredEntries = entries.filter(e => e.groupId !== groupId);
    await this.saveEntries(filteredEntries);

    // Also delete projects for this group
    const projects = await this.getProjects();
    const filteredProjects = projects.filter(p => p.groupId !== groupId);
    await this.saveProjects(filteredProjects);
  },

  // Get all projects
  async getProjects() {
    const data = await chrome.storage.sync.get({ projects: [] });
    return data.projects;
  },

  // Save all projects
  async saveProjects(projects) {
    await chrome.storage.sync.set({ projects });
  },

  // Get projects for a specific group (excludes archived by default)
  async getProjectsByGroup(groupId, includeArchived = false) {
    const projects = await this.getProjects();
    return projects.filter(p => p.groupId === groupId && (includeArchived || !p.archived));
  },

  // Add a new project under a group
  async addProject(groupId, name) {
    const projects = await this.getProjects();
    const id = Date.now();
    const newProject = { id, groupId, name, archived: false };
    projects.push(newProject);
    await this.saveProjects(projects);
    return newProject;
  },

  // Archive/unarchive a project
  async archiveProject(projectId, archived = true) {
    const projects = await this.getProjects();
    const project = projects.find(p => p.id === projectId);
    if (project) {
      project.archived = archived;
      await this.saveProjects(projects);
    }
    return project;
  },

  // Delete a project
  async deleteProject(projectId) {
    const projects = await this.getProjects();
    const filtered = projects.filter(p => p.id !== projectId);
    await this.saveProjects(filtered);

    // Clear projectId from entries that used this project
    const entries = await this.getEntries();
    let changed = false;
    entries.forEach(e => {
      if (e.projectId === projectId) { e.projectId = null; changed = true; }
    });
    if (changed) await this.saveEntries(entries);
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
  async addEntry(groupId, taskDescription, date, startTime, endTime, projectId = null) {
    const entries = await this.getEntries();
    
    // Calculate hours
    const [startH, startM] = startTime.split(':').map(Number);
    const [endH, endM] = endTime.split(':').map(Number);
    const totalHours = ((endH * 60 + endM) - (startH * 60 + startM)) / 60;
    
    const id = Date.now();
    const newEntry = {
      id,
      groupId,
      projectId,
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

  // Update an existing entry
  async updateEntry(entryId, updates) {
    const entries = await this.getEntries();
    const entry = entries.find(e => e.id === entryId);
    if (!entry) return null;
    
    Object.assign(entry, updates);
    
    // Recalculate hours if times changed
    if (updates.startTime || updates.endTime) {
      const [startH, startM] = entry.startTime.split(':').map(Number);
      const [endH, endM] = entry.endTime.split(':').map(Number);
      entry.totalHours = Math.round(((endH * 60 + endM) - (startH * 60 + startM)) / 60 * 100) / 100;
    }
    
    await this.saveEntries(entries);
    return entry;
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
      hourlyRate: 107.93,
      workingDays: [1, 2, 3, 4, 5],  // Mon-Fri
      workStartTime: '09:00',
      workEndTime: '17:00'
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
    const projects = await this.getProjects();
    const settings = await this.getSettings();
    
    return {
      exportDate: new Date().toISOString(),
      groups,
      projects,
      entries,
      settings
    };
  },

  // Export entries as CSV
  async exportCSV(hourlyRate = 107.93) {
    const groups = await this.getGroups();
    const entries = await this.getEntries();
    const projects = await this.getProjects();
    
    const groupMap = {};
    groups.forEach(g => groupMap[g.id] = g);
    
    const projectMap = {};
    projects.forEach(p => projectMap[p.id] = p);
    
    const headers = ['Date', 'Group', 'Project', 'Manager', 'Task', 'Start', 'End', 'Hours', 'Amount (£)'];
    const rows = entries.map(e => {
      const group = groupMap[e.groupId] || { name: 'Unknown', projectName: '', managerName: '' };
      const project = e.projectId ? projectMap[e.projectId] : null;
      const projectName = project ? project.name : group.projectName;
      const amount = (e.totalHours * hourlyRate).toFixed(2);
      return [
        e.date,
        group.name,
        projectName,
        group.managerName,
        `"${e.taskDescription.replace(/"/g, '""')}"`,
        e.startTime,
        e.endTime,
        e.totalHours,
        amount
      ].join(',');
    });
    
    // Calculate totals
    const totalHours = entries.reduce((sum, e) => sum + e.totalHours, 0);
    const totalAmount = (totalHours * hourlyRate).toFixed(2);
    
    // Add empty row and totals
    rows.push('');
    rows.push(`,,,,,,Total,${totalHours.toFixed(2)},${totalAmount}`);
    
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
