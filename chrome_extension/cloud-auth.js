// Cloud auth for Time Tracker.
//
// Handles signing the user into Firebase using their Chrome/Google account
// (via chrome.identity), keeping the resulting Firebase ID token fresh, and
// persisting the session in chrome.storage.local so every extension context
// (popup, options page, background service worker) can read it.
//
// This intentionally avoids the Firebase JS SDK (which doesn't run cleanly
// in a Manifest V3 service worker without extra bundling/offscreen-document
// setup) and instead talks directly to the small set of REST endpoints the
// SDK itself would call:
//   - identitytoolkit.googleapis.com  (exchange Google token -> Firebase session)
//   - securetoken.googleapis.com      (refresh an expired Firebase ID token)

const CloudAuth = {
  STORAGE_KEY: 'cloudAuth',

  // Refresh proactively when the ID token has less than this much life left.
  REFRESH_MARGIN_MS: 60 * 1000,

  /**
   * Read the persisted auth session, if any.
   * Shape: { uid, email, idToken, refreshToken, idTokenExpiresAt }
   */
  async getSession() {
    const data = await chrome.storage.local.get({ [this.STORAGE_KEY]: null });
    return data[this.STORAGE_KEY];
  },

  async _saveSession(session) {
    await chrome.storage.local.set({ [this.STORAGE_KEY]: session });
  },

  async isSignedIn() {
    const session = await this.getSession();
    return !!(session && session.idToken);
  },

  /**
   * Interactively sign the user in with their Google account and establish
   * a Firebase session. Safe to call again later non-interactively to
   * silently re-check/renew the session (interactive=false).
   */
  async signIn(interactive = true) {
    const googleToken = await this._getGoogleToken(interactive);
    const firebaseSession = await this._exchangeGoogleToken(googleToken);
    await this._saveSession(firebaseSession);
    return firebaseSession;
  },

  /**
   * Sign the user out: revoke cached Chrome OAuth tokens and drop the
   * local Firebase session. Local data in chrome.storage.local is left
   * untouched (signing out of sync should not delete anything on-device).
   */
  async signOut() {
    try {
      await chrome.identity.clearAllCachedAuthTokens();
    } catch (e) {
      // Older Chrome versions may not support this; not fatal.
      console.warn('clearAllCachedAuthTokens failed:', e);
    }
    await chrome.storage.local.remove(this.STORAGE_KEY);
  },

  /**
   * Return a currently-valid Firebase ID token, refreshing it first if it's
   * expired or close to expiring. Returns null if the user isn't signed in.
   * Throws if signed in but the refresh fails for a reason other than "not
   * signed in" (e.g. network error) so callers can distinguish and retry.
   */
  async getValidIdToken() {
    const session = await this.getSession();
    if (!session || !session.refreshToken) return null;

    const expiresSoon = Date.now() >= (session.idTokenExpiresAt - this.REFRESH_MARGIN_MS);
    if (!expiresSoon) return session.idToken;

    const refreshed = await this._refreshIdToken(session.refreshToken);
    return refreshed.idToken;
  },

  async getUid() {
    const session = await this.getSession();
    return session ? session.uid : null;
  },

  // ---- Internal helpers -----------------------------------------------

  /** Get a Google OAuth2 access token via chrome.identity. */
  async _getGoogleToken(interactive) {
    const result = await chrome.identity.getAuthToken({
      interactive,
      scopes: ['https://www.googleapis.com/auth/userinfo.email'],
    });
    if (!result || !result.token) {
      throw new Error('Could not get a Google account token. Please sign in to Chrome.');
    }
    return result.token;
  },

  /**
   * Remove a specific cached Google token (e.g. because Firebase rejected
   * it) so the next getAuthToken call fetches a fresh one instead of the
   * same stale/invalid one.
   */
  async _dropCachedGoogleToken(token) {
    try {
      await chrome.identity.removeCachedAuthToken({ token });
    } catch (e) {
      // Best-effort; ignore.
    }
  },

  /** Exchange a Google OAuth2 access token for a Firebase session. */
  async _exchangeGoogleToken(googleToken) {
    const apiKey = FirebaseConfig.FIREBASE_API_KEY;
    const url = `https://identitytoolkit.googleapis.com/v1/accounts:signInWithIdp?key=${apiKey}`;

    let response;
    try {
      response = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          postBody: `access_token=${encodeURIComponent(googleToken)}&providerId=google.com`,
          requestUri: 'http://localhost',
          returnIdpCredential: true,
          returnSecureToken: true,
        }),
      });
    } catch (networkErr) {
      throw new Error(`Could not reach Firebase Auth: ${networkErr.message}`);
    }

    const data = await response.json().catch(() => ({}));

    if (!response.ok) {
      // A bad/expired Google token should not get stuck in Chrome's cache.
      await this._dropCachedGoogleToken(googleToken);
      const msg = (data && data.error && data.error.message) || `HTTP ${response.status}`;
      throw new Error(`Sign-in failed: ${msg}`);
    }

    return {
      uid: data.localId,
      email: data.email || '',
      idToken: data.idToken,
      refreshToken: data.refreshToken,
      idTokenExpiresAt: Date.now() + Number(data.expiresIn || '3600') * 1000,
    };
  },

  /** Exchange a refresh token for a new Firebase ID token. */
  async _refreshIdToken(refreshToken) {
    const apiKey = FirebaseConfig.FIREBASE_API_KEY;
    const url = `https://securetoken.googleapis.com/v1/token?key=${apiKey}`;

    let response;
    try {
      response = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: `grant_type=refresh_token&refresh_token=${encodeURIComponent(refreshToken)}`,
      });
    } catch (networkErr) {
      throw new Error(`Could not reach Firebase Auth (refresh): ${networkErr.message}`);
    }

    const data = await response.json().catch(() => ({}));

    if (!response.ok) {
      const msg = (data && data.error && data.error.message) || `HTTP ${response.status}`;
      // A refresh token can become permanently invalid (revoked access,
      // password change upstream, etc). Clear the session so the UI can
      // prompt the user to sign in again rather than retrying forever.
      if (msg === 'TOKEN_EXPIRED' || msg === 'INVALID_REFRESH_TOKEN' || msg === 'USER_NOT_FOUND') {
        await chrome.storage.local.remove(this.STORAGE_KEY);
      }
      throw new Error(`Session refresh failed: ${msg}`);
    }

    const session = await this.getSession() || {};
    const updated = {
      ...session,
      uid: data.user_id || session.uid,
      idToken: data.id_token,
      refreshToken: data.refresh_token,
      idTokenExpiresAt: Date.now() + Number(data.expires_in || '3600') * 1000,
    };
    await this._saveSession(updated);
    return updated;
  },
};

if (typeof globalThis !== 'undefined') {
  globalThis.CloudAuth = CloudAuth;
}
