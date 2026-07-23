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

// Make available across contexts (popup/options pages use `window`,
// the background service worker uses `self`/`globalThis`). Classic scripts
// loaded together already share one global scope, so this is mostly a
// defensive/explicit export rather than a strict requirement.
if (typeof globalThis !== 'undefined') {
  globalThis.FirebaseConfig = FirebaseConfig;
}
