// Storage utilities for Time Tracker
//
// Data lives in chrome.storage.local (no size-per-item quota, unlike
// chrome.storage.sync which caps every key at 8KB and is what previously
// caused "kQuotaBytesPerItem quota exceeded" once entries built up).
//
// Cross-device sync is now handled separately by signing into a Google
// account and syncing through Firestore (see cloud-auth.js / firestore-client.js
// / sync-engine.js). This file stays the source of truth for the local
// on-disk shape and exposes the same public methods as before so popup.js
// and options.js don't need to change how they call Storage.
//
// Every group/project/entry gets two bookkeeping fields used only by the
// sync engine:
//   - updatedAt: ms timestamp of the last local change to this item.
//   - syncedAt:  ms timestamp this exact version was last pushed to
//                Firestore (0 / absent = never synced yet).

/** One-time copy of any pre-existing chrome.storage.sync data into
 * chrome.storage.local, so upgrading the extension doesn't strand data
 * that used to live in sync storage. Runs at most once per profile;
 * subsequent calls are a no-op via the 'migratedFromSync' flag. Old sync
 * data is left in place afterwards as a safety net, not read again. */
let _migrationPromise = null;
function ensureMigrated() {
  if (!_migrationPromise) {
    _migrationPromise = (async () => {
      const localFlag = await chrome.storage.local.get({ migratedFromSync: false });
      if (localFlag.migratedFromSync) return;

      let syncData = {};
      try {
        syncData = await chrome.storage.sync.get({
          groups: [],
          projects: [],
          entries: [],
          promptIntervalMinutes: undefined,
          defaultGroupId: undefined,
          notificationsEnabled: undefined,
          hourlyRate: undefined,
          workingDays: undefined,
          workStartTime: undefined,
          workEndTime: undefined,
        });
      } catch (e) {
        console.warn('Could not read legacy sync storage (continuing with empty data):', e);
      }

      const now = Date.now();
      const stamp = item => ({ ...item, updatedAt: item.updatedAt || now, syncedAt: 0 });

      const settings = {};
      ['promptIntervalMinutes', 'defaultGroupId', 'notificationsEnabled',
        'hourlyRate', 'workingDays', 'workStartTime', 'workEndTime'].forEach(key => {
        if (syncData[key] !== undefined) settings[key] = syncData[key];
      });

      await chrome.storage.local.set({
        groups: (syncData.groups || []).map(stamp),
        projects: (syncData.projects || []).map(stamp),
        entries: (syncData.entries || []).map(stamp),
        settings,
        settingsMeta: { updatedAt: Object.keys(settings).length ? now : 0, syncedAt: 0 },
        migratedFromSync: true,
      });
    })();
  }
  return _migrationPromise;
}

/** Kick off a debounced background sync after a local mutation. Safe to
 * call even if cloud sync was never configured/signed in -- SyncEngine
 * checks sign-in state itself before doing any network work. */
function notifySync() {
  try {
    if (globalThis.SyncEngine && typeof globalThis.SyncEngine.schedulePush === 'function') {
      globalThis.SyncEngine.schedulePush();
    }
  } catch (e) {
    console.warn('Sync notify failed:', e);
  }
}

/** Record that an item was deleted locally so the next sync cycle deletes
 * it from Firestore too. */
async function queueDelete(collection, id) {
  try {
    if (globalThis.SyncEngine && typeof globalThis.SyncEngine.queueDelete === 'function') {
      await globalThis.SyncEngine.queueDelete(collection, id);
    }
  } catch (e) {
    console.warn('Queue delete failed:', e);
  }
}

const Storage = {
  // Get all research groups
  async getGroups() {
    await ensureMigrated();
    const data = await chrome.storage.local.get({ groups: [] });
    return data.groups;
  },

  // Save all groups
  async saveGroups(groups) {
    await ensureMigrated();
    await chrome.storage.local.set({ groups });
  },

  // Add a new group
  async addGroup(name, managerName = '', projectName = '') {
    const groups = await this.getGroups();
    const id = Date.now(); // Simple unique ID
    const newGroup = { id, name, managerName, projectName, updatedAt: Date.now(), syncedAt: 0 };
    groups.push(newGroup);
    await this.saveGroups(groups);
    notifySync();
    return newGroup;
  },

  // Delete a group and its entries and projects
  async deleteGroup(groupId) {
    const groups = await this.getGroups();
    const filtered = groups.filter(g => g.id !== groupId);
    await this.saveGroups(filtered);
    await queueDelete('groups', groupId);

    // Also delete entries for this group
    const entries = await this.getEntries();
    const removedEntries = entries.filter(e => e.groupId === groupId);
    const remainingEntries = entries.filter(e => e.groupId !== groupId);
    await this.saveEntries(remainingEntries);
    for (const e of removedEntries) await queueDelete('entries', e.id);

    // Also delete projects for this group
    const projects = await this.getProjects();
    const removedProjects = projects.filter(p => p.groupId === groupId);
    const remainingProjects = projects.filter(p => p.groupId !== groupId);
    await this.saveProjects(remainingProjects);
    for (const p of removedProjects) await queueDelete('projects', p.id);

    notifySync();
  },

  // Get all projects
  async getProjects() {
    await ensureMigrated();
    const data = await chrome.storage.local.get({ projects: [] });
    return data.projects;
  },

  // Save all projects
  async saveProjects(projects) {
    await ensureMigrated();
    await chrome.storage.local.set({ projects });
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
    const newProject = { id, groupId, name, archived: false, updatedAt: Date.now(), syncedAt: 0 };
    projects.push(newProject);
    await this.saveProjects(projects);
    notifySync();
    return newProject;
  },

  // Archive/unarchive a project
  async archiveProject(projectId, archived = true) {
    const projects = await this.getProjects();
    const project = projects.find(p => p.id === projectId);
    if (project) {
      project.archived = archived;
      project.updatedAt = Date.now();
      await this.saveProjects(projects);
      notifySync();
    }
    return project;
  },

  // Delete a project
  async deleteProject(projectId) {
    const projects = await this.getProjects();
    const filtered = projects.filter(p => p.id !== projectId);
    await this.saveProjects(filtered);
    await queueDelete('projects', projectId);

    // Clear projectId from entries that used this project
    const entries = await this.getEntries();
    let changed = false;
    const now = Date.now();
    entries.forEach(e => {
      if (e.projectId === projectId) { e.projectId = null; e.updatedAt = now; changed = true; }
    });
    if (changed) await this.saveEntries(entries);

    notifySync();
  },

  // Get all time entries
  async getEntries() {
    await ensureMigrated();
    const data = await chrome.storage.local.get({ entries: [] });
    return data.entries;
  },

  // Save all entries
  async saveEntries(entries) {
    await ensureMigrated();
    await chrome.storage.local.set({ entries });
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
      totalHours: Math.round(totalHours * 100) / 100,
      updatedAt: Date.now(),
      syncedAt: 0,
    };
    
    entries.push(newEntry);
    await this.saveEntries(entries);
    notifySync();
    return newEntry;
  },

  // Delete an entry
  async deleteEntry(entryId) {
    const entries = await this.getEntries();
    const filtered = entries.filter(e => e.id !== entryId);
    await this.saveEntries(filtered);
    await queueDelete('entries', entryId);
    notifySync();
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

    entry.updatedAt = Date.now();
    
    await this.saveEntries(entries);
    notifySync();
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
    await ensureMigrated();
    const data = await chrome.storage.local.get({
      settings: {},
      settingsMeta: { updatedAt: 0, syncedAt: 0 },
    });
    const defaults = {
      promptIntervalMinutes: 30,
      defaultGroupId: null,
      notificationsEnabled: true,
      hourlyRate: 107.93,
      workingDays: [1, 2, 3, 4, 5],  // Mon-Fri
      workStartTime: '09:00',
      workEndTime: '17:00',
    };
    return { ...defaults, ...data.settings };
  },

  // Save settings
  async saveSettings(settings) {
    await ensureMigrated();
    const data = await chrome.storage.local.get({
      settings: {},
      settingsMeta: { updatedAt: 0, syncedAt: 0 },
    });
    const merged = { ...data.settings, ...settings };
    await chrome.storage.local.set({
      settings: merged,
      settingsMeta: { updatedAt: Date.now(), syncedAt: data.settingsMeta.syncedAt },
    });
    notifySync();
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

// Make available globally. Uses globalThis (rather than `window`) so this
// module works the same way in popup/options pages and in the background
// service worker, which has no `window`.
if (typeof globalThis !== 'undefined') {
  globalThis.Storage = Storage;
}
