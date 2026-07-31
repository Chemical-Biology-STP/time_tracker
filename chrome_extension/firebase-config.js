// Firebase / Google Cloud project configuration for Time Tracker cloud sync.
//
// Fill in the two values below after creating your Firebase project.
// See chrome_extension/CLOUD_SYNC_SETUP.md for the full step-by-step guide.
//
// Where to find these values:
// - FIREBASE_API_KEY: Firebase Console -> Project settings -> General ->
//   "Web API Key" (this is also the key shown under your Web app config).
// - FIREBASE_PROJECT_ID: Firebase Console -> Project settings -> General ->
//   "Project ID".
//
// Neither value is a secret in the traditional sense (they're visible in
// any Firebase web app's client bundle), but access to your data is
// enforced separately by Firestore Security Rules, not by hiding these
// values. See firestore.rules in this folder.

const FirebaseConfig = {
  FIREBASE_API_KEY: 'YOUR_FIREBASE_WEB_API_KEY',
  FIREBASE_PROJECT_ID: 'YOUR_FIREBASE_PROJECT_ID',

  // Firestore always uses the "(default)" database unless you explicitly
  // created a named database. Leave this as-is unless you know otherwise.
  FIRESTORE_DATABASE_ID: '(default)',
};

// Derived constant: base URL for all Firestore REST calls.
FirebaseConfig.FIRESTORE_BASE_URL =
  `https://firestore.googleapis.com/v1/projects/${FirebaseConfig.FIREBASE_PROJECT_ID}` +
  `/databases/${FirebaseConfig.FIRESTORE_DATABASE_ID}/documents`;

/**
 * Whether cloud sync has actually been configured for this installation.
 *
 * Cloud sync is an advanced, opt-in feature: it needs a Firebase project and
 * an OAuth client that only whoever deploys this extension can create. Until
 * all three values are filled in, the sync UI stays hidden and no sync work
 * runs, so users aren't shown a sign-in button that can only fail.
 *
 * To move data between devices without any of this setup, use Export/Import
 * JSON in Settings instead.
 */
FirebaseConfig.isConfigured = function () {
  const filled = v => typeof v === 'string' && v.length > 0 && !v.startsWith('YOUR_');

  if (!filled(this.FIREBASE_API_KEY) || !filled(this.FIREBASE_PROJECT_ID)) {
    return false;
  }

  // The OAuth client ID lives in manifest.json rather than this file, since
  // chrome.identity reads it from there directly.
  try {
    const oauth2 = chrome.runtime.getManifest().oauth2;
    return !!(oauth2 && filled(oauth2.client_id));
  } catch (e) {
    return false;
  }
};

// Make available across contexts (popup/options pages use `window`,
// the background service worker uses `self`/`globalThis`). Classic scripts
// loaded together already share one global scope, so this is mostly a
// defensive/explicit export rather than a strict requirement.
if (typeof globalThis !== 'undefined') {
  globalThis.FirebaseConfig = FirebaseConfig;
}
