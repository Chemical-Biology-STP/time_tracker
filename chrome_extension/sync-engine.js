// Sync engine for Time Tracker.
//
// Reconciles local chrome.storage.local data with Firestore for the
// signed-in user. This is intentionally a simple last-write-wins sync,
// which fits a single-user, low-write-frequency app like this one far
// better than a full CRDT/operational-transform system would.
//
// Local bookkeeping added to each group/project/entry item:
//   - updatedAt: ms timestamp, bumped by storage.js whenever the item
//     is created or modified.
//   - syncedAt: ms timestamp copied from updatedAt the last time this
//     exact item was successfully written to Firestore. Comparing the
//     two tells us whether an item still needs to be pushed, and also
//     lets us safely tell "not yet pushed" apart from "deleted remotely"
//     when a document is missing from the server's list.
//
// Deletions are tracked separately in chrome.storage.local under
// 'pendingDeletes' (per collection arrays of ids) because a deleted item
// no longer exists locally to carry its own bookkeeping.

const SyncEngine = {
  COLLECTIONS: ['groups', 'projects', 'entries'],
  DEBOUNCE_MS: 1500,

  _debounceTimer: null,
  _inFlight: null,

  // ---- Status (surfaced in options.js / popup.js UI) --------------------

  async _setStatus(patch) {
    const current = await this._getStatus();
    await chrome.storage.local.set({ syncStatus: { ...current, ...patch } });
  },

  async _getStatus() {
    const data = await chrome.storage.local.get({
      syncStatus: { state: 'idle', lastSyncedAt: null, lastError: null },
    });
    return data.syncStatus;
  },

  async getStatus() {
    return this._getStatus();
  },

  // ---- Public entry points -----------------------------------------------

  /**
   * Called by storage.js after a local mutation. Coalesces rapid calls
   * (e.g. several entries created in quick succession) into a single sync
   * run instead of firing one network round-trip per change.
   */
  schedulePush() {
    if (this._debounceTimer) clearTimeout(this._debounceTimer);
    this._debounceTimer = setTimeout(() => {
      this._debounceTimer = null;
      this.syncNow().catch(err => console.warn('Background sync failed:', err));
    }, this.DEBOUNCE_MS);
  },

  /**
   * Run a sync cycle immediately. Safe to call concurrently -- overlapping
   * calls join the same in-flight run rather than racing each other.
   */
  async syncNow() {
    if (this._inFlight) return this._inFlight;
    this._inFlight = this._runSync().finally(() => {
      this._inFlight = null;
    });
    return this._inFlight;
  },

  // ---- Core sync cycle -----------------------------------------------------

  async _runSync() {
    const isSignedIn = await CloudAuth.isSignedIn();
    if (!isSignedIn) return { skipped: true, reason: 'not-signed-in' };

    await this._setStatus({ state: 'syncing', lastError: null });

    try {
      const idToken = await CloudAuth.getValidIdToken();
      const uid = await CloudAuth.getUid();

      await this._pushDeletes(idToken, uid);
      for (const collection of this.COLLECTIONS) {
        await this._pushCollection(idToken, uid, collection);
      }
      await this._pushSettings(idToken, uid);

      for (const collection of this.COLLECTIONS) {
        await this._pullCollection(idToken, uid, collection);
      }
      await this._pullSettings(idToken, uid);

      const finishedAt = Date.now();
      await this._setStatus({ state: 'success', lastSyncedAt: finishedAt, lastError: null });
      return { skipped: false, finishedAt };
    } catch (err) {
      await this._setStatus({ state: 'error', lastError: err.message });
      throw err;
    }
  },

  // ---- Deletes ------------------------------------------------------------

  async _getPendingDeletes() {
    const data = await chrome.storage.local.get({
      pendingDeletes: { groups: [], projects: [], entries: [] },
    });
    return data.pendingDeletes;
  },

  async _savePendingDeletes(pendingDeletes) {
    await chrome.storage.local.set({ pendingDeletes });
  },

  /** Record an id as needing deletion from Firestore. Called by storage.js. */
  async queueDelete(collection, id) {
    const pendingDeletes = await this._getPendingDeletes();
    if (!pendingDeletes[collection].includes(id)) {
      pendingDeletes[collection].push(id);
      await this._savePendingDeletes(pendingDeletes);
    }
  },

  async _pushDeletes(idToken, uid) {
    const pendingDeletes = await this._getPendingDeletes();
    let changed = false;

    for (const collection of this.COLLECTIONS) {
      const remaining = [];
      for (const id of pendingDeletes[collection]) {
        try {
          await FirestoreClient.deleteDoc(idToken, uid, collection, String(id));
        } catch (err) {
          console.warn(`Failed to push delete for ${collection}/${id}:`, err);
          remaining.push(id); // retry next cycle
        }
      }
      if (remaining.length !== pendingDeletes[collection].length) changed = true;
      pendingDeletes[collection] = remaining;
    }

    if (changed) await this._savePendingDeletes(pendingDeletes);
  },

  // ---- Push (local -> Firestore) ------------------------------------------

  async _pushCollection(idToken, uid, collection) {
    const data = await chrome.storage.local.get({ [collection]: [] });
    const items = data[collection];
    let changed = false;

    for (const item of items) {
      const needsPush = !item.syncedAt || item.syncedAt < item.updatedAt;
      if (!needsPush) continue;

      try {
        await FirestoreClient.setDoc(idToken, uid, collection, String(item.id), item);
        item.syncedAt = item.updatedAt;
        changed = true;
      } catch (err) {
        console.warn(`Failed to push ${collection}/${item.id}:`, err);
        // Leave syncedAt as-is so this item is retried next cycle.
      }
    }

    if (changed) await chrome.storage.local.set({ [collection]: items });
  },

  async _pushSettings(idToken, uid) {
    const data = await chrome.storage.local.get({
      settings: null,
      settingsMeta: { updatedAt: 0, syncedAt: 0 },
    });
    if (!data.settings) return; // nothing saved locally yet

    const meta = data.settingsMeta;
    if (meta.syncedAt >= meta.updatedAt) return; // already up to date

    const payload = { ...data.settings, updatedAt: meta.updatedAt };
    try {
      await FirestoreClient.setDoc(idToken, uid, 'meta', 'settings', payload);
      await chrome.storage.local.set({
        settingsMeta: { updatedAt: meta.updatedAt, syncedAt: meta.updatedAt },
      });
    } catch (err) {
      console.warn('Failed to push settings:', err);
    }
  },

  // ---- Pull (Firestore -> local) ------------------------------------------

  async _pullCollection(idToken, uid, collection) {
    const remoteDocs = await FirestoreClient.listCollection(idToken, uid, collection);
    const remoteById = new Map(remoteDocs.map(doc => [Number(doc.id), doc.data]));

    const localData = await chrome.storage.local.get({ [collection]: [] });
    const localItems = localData[collection];
    const localById = new Map(localItems.map(item => [Number(item.id), item]));

    const pendingDeletes = await this._getPendingDeletes();
    const pendingDeleteIds = new Set(pendingDeletes[collection].map(Number));

    const merged = [];

    // Existing local items: keep, update from remote, or drop (remote delete).
    for (const [id, localItem] of localById) {
      const remoteItem = remoteById.get(id);

      if (!remoteItem) {
        // Missing on the server. If this item was actually synced before,
        // its absence means it was deleted on another device. If it was
        // never synced (brand new, or a delete we already pushed), keep
        // relying on the push step to reconcile instead of guessing here.
        if (localItem.syncedAt && !pendingDeleteIds.has(id)) {
          continue; // dropped -- remote delete wins
        }
        merged.push(localItem);
        continue;
      }

      if ((remoteItem.updatedAt || 0) > (localItem.updatedAt || 0)) {
        merged.push({ ...remoteItem, id, syncedAt: remoteItem.updatedAt });
      } else {
        merged.push(localItem);
      }
    }

    // Remote-only items (created on another device): add them locally.
    for (const [id, remoteItem] of remoteById) {
      if (!localById.has(id) && !pendingDeleteIds.has(id)) {
        merged.push({ ...remoteItem, id, syncedAt: remoteItem.updatedAt });
      }
    }

    await chrome.storage.local.set({ [collection]: merged });
  },

  async _pullSettings(idToken, uid) {
    const remote = await FirestoreClient.getDoc(idToken, uid, 'meta', 'settings');
    if (!remote) return;

    const data = await chrome.storage.local.get({
      settings: {},
      settingsMeta: { updatedAt: 0, syncedAt: 0 },
    });

    if ((remote.updatedAt || 0) > (data.settingsMeta.updatedAt || 0)) {
      const { updatedAt, ...settingsFields } = remote;
      await chrome.storage.local.set({
        settings: { ...data.settings, ...settingsFields },
        settingsMeta: { updatedAt: updatedAt || 0, syncedAt: updatedAt || 0 },
      });
    }
  },
};

if (typeof globalThis !== 'undefined') {
  globalThis.SyncEngine = SyncEngine;
}
