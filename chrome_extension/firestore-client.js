// Minimal Firestore REST client for Time Tracker.
//
// We talk to the plain Firestore REST API (rather than the Firebase JS SDK)
// so the extension can stay as simple classic scripts with no build step.
// Reference: https://firebase.google.com/docs/firestore/reference/rest/v1/projects.databases.documents
//
// All data for a given user lives under:
//   users/{uid}/groups/{id}
//   users/{uid}/projects/{id}
//   users/{uid}/entries/{id}
//   users/{uid}/meta/settings
//
// This module is deliberately unaware of auth/token refresh — callers pass
// in a valid Firebase ID token for each call (see sync-engine.js, which gets
// it from CloudAuth). That keeps this file focused on the wire format only.

const FirestoreClient = {
  // ---- JS <-> Firestore "Value" wire format ----------------------------
  //
  // https://firebase.google.com/docs/firestore/reference/rest/v1/Value

  _toValue(v) {
    if (v === null || v === undefined) return { nullValue: null };
    if (typeof v === 'boolean') return { booleanValue: v };
    if (typeof v === 'number') {
      return Number.isInteger(v)
        ? { integerValue: String(v) }
        : { doubleValue: v };
    }
    if (typeof v === 'string') return { stringValue: v };
    if (Array.isArray(v)) {
      return { arrayValue: { values: v.map(item => this._toValue(item)) } };
    }
    if (typeof v === 'object') {
      return { mapValue: { fields: this._toFields(v) } };
    }
    // Fallback: stringify anything unexpected rather than throwing.
    return { stringValue: String(v) };
  },

  _toFields(obj) {
    const fields = {};
    for (const [key, value] of Object.entries(obj)) {
      if (value === undefined) continue; // Firestore has no "undefined"
      fields[key] = this._toValue(value);
    }
    return fields;
  },

  _fromValue(value) {
    if (!value || typeof value !== 'object') return null;
    if ('nullValue' in value) return null;
    if ('booleanValue' in value) return value.booleanValue;
    if ('integerValue' in value) return parseInt(value.integerValue, 10);
    if ('doubleValue' in value) return value.doubleValue;
    if ('stringValue' in value) return value.stringValue;
    if ('timestampValue' in value) return value.timestampValue;
    if ('arrayValue' in value) {
      const values = (value.arrayValue && value.arrayValue.values) || [];
      return values.map(item => this._fromValue(item));
    }
    if ('mapValue' in value) {
      return this._fromFields((value.mapValue && value.mapValue.fields) || {});
    }
    return null;
  },

  _fromFields(fields) {
    const obj = {};
    for (const [key, value] of Object.entries(fields || {})) {
      obj[key] = this._fromValue(value);
    }
    return obj;
  },

  /** Extract the last path segment (document ID) from a Firestore doc name. */
  _idFromName(name) {
    const parts = name.split('/');
    return parts[parts.length - 1];
  },

  // ---- HTTP helpers ------------------------------------------------------

  async _request(idToken, method, url, body) {
    const options = {
      method,
      headers: { Authorization: `Bearer ${idToken}` },
    };
    if (body !== undefined) {
      options.headers['Content-Type'] = 'application/json';
      options.body = JSON.stringify(body);
    }

    let response;
    try {
      response = await fetch(url, options);
    } catch (networkErr) {
      throw new Error(`Firestore request failed (network): ${networkErr.message}`);
    }
    return response;
  },

  // ---- Public document/collection operations -----------------------------

  /**
   * List every document in a user's subcollection (groups/projects/entries).
   * Returns an array of { id, data } pairs. Handles pagination transparently.
   */
  async listCollection(idToken, uid, collection) {
    const results = [];
    let pageToken = '';

    do {
      const params = new URLSearchParams({ pageSize: '300' });
      if (pageToken) params.set('pageToken', pageToken);
      const url = `${FirebaseConfig.FIRESTORE_BASE_URL}/users/${uid}/${collection}?${params}`;

      const response = await this._request(idToken, 'GET', url);
      const data = await response.json().catch(() => ({}));

      if (!response.ok) {
        // A brand-new user has no subcollection yet; Firestore returns an
        // empty list (not 404) in that case, so a real error here is
        // genuinely exceptional.
        const msg = (data && data.error && data.error.message) || `HTTP ${response.status}`;
        throw new Error(`Failed to list ${collection}: ${msg}`);
      }

      for (const doc of data.documents || []) {
        results.push({
          id: this._idFromName(doc.name),
          data: this._fromFields(doc.fields),
        });
      }
      pageToken = data.nextPageToken || '';
    } while (pageToken);

    return results;
  },

  /** Fetch a single document. Returns null if it doesn't exist. */
  async getDoc(idToken, uid, collection, id) {
    const url = `${FirebaseConfig.FIRESTORE_BASE_URL}/users/${uid}/${collection}/${id}`;
    const response = await this._request(idToken, 'GET', url);

    if (response.status === 404) return null;

    const data = await response.json().catch(() => ({}));
    if (!response.ok) {
      const msg = (data && data.error && data.error.message) || `HTTP ${response.status}`;
      throw new Error(`Failed to get ${collection}/${id}: ${msg}`);
    }
    return this._fromFields(data.fields);
  },

  /**
   * Create or fully overwrite a document. We never pass an updateMask, so
   * this always replaces the whole document with `data` -- which is exactly
   * what we want since every write here already carries the complete,
   * current representation of the item.
   */
  async setDoc(idToken, uid, collection, id, data) {
    const url = `${FirebaseConfig.FIRESTORE_BASE_URL}/users/${uid}/${collection}/${id}`;
    const body = { fields: this._toFields(data) };
    const response = await this._request(idToken, 'PATCH', url, body);

    if (!response.ok) {
      const errBody = await response.json().catch(() => ({}));
      const msg = (errBody && errBody.error && errBody.error.message) || `HTTP ${response.status}`;
      throw new Error(`Failed to save ${collection}/${id}: ${msg}`);
    }
  },

  /** Delete a document. A missing document is treated as already-deleted. */
  async deleteDoc(idToken, uid, collection, id) {
    const url = `${FirebaseConfig.FIRESTORE_BASE_URL}/users/${uid}/${collection}/${id}`;
    const response = await this._request(idToken, 'DELETE', url);

    if (!response.ok && response.status !== 404) {
      const errBody = await response.json().catch(() => ({}));
      const msg = (errBody && errBody.error && errBody.error.message) || `HTTP ${response.status}`;
      throw new Error(`Failed to delete ${collection}/${id}: ${msg}`);
    }
  },
};

if (typeof globalThis !== 'undefined') {
  globalThis.FirestoreClient = FirestoreClient;
}
