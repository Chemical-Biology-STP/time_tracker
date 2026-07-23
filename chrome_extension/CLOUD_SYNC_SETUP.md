# Cloud Sync Setup (Firestore)

This extension can sync groups, projects, entries, and settings across
devices by signing in with your Google account. Data is stored in a
Firestore database that only you (the signed-in account) can read or
write, enforced by the security rules in `firestore.rules`.

This sync is optional. If you skip this setup, the extension keeps
working exactly as before, using only local storage on that one device
(now `chrome.storage.local`, which has no per-item size ceiling — the
issue that caused "kQuotaBytesPerItem quota exceeded" errors previously).

You only need to do this setup once. It takes about 10-15 minutes.

## 1. Create a Firebase project

1. Go to the [Firebase console](https://console.firebase.google.com/) and click **Add project**.
2. Give it any name (e.g. "time-tracker-sync"). Google Analytics is not needed — you can disable it.
3. Once created, open **Project settings** (gear icon) → **General** tab.
4. Note down the **Project ID** shown there — you'll need it in step 5.

## 2. Register a Web app and get the Web API key

1. Still in **Project settings** → **General**, scroll to "Your apps" and click the **Web** icon (`</>`) to register a new web app.
2. Give it any nickname (e.g. "chrome-extension"). You don't need Firebase Hosting.
3. After registering, Firebase shows a config snippet. Note down the `apiKey` value — this is your **Web API Key**.

## 3. Enable Firestore

1. In the left sidebar, go to **Build → Firestore Database**.
2. Click **Create database**.
3. Choose **Start in production mode** (we'll set proper rules in step 4 either way).
4. Pick any region close to you. This can't be changed later, but it doesn't materially affect a small personal dataset like this.

## 4. Set Firestore security rules

1. In Firestore, go to the **Rules** tab.
2. Replace the contents with the contents of [`firestore.rules`](./firestore.rules) in this folder:

   ```
   rules_version = '2';
   service cloud.firestore {
     match /databases/{database}/documents {
       match /users/{uid}/{document=**} {
         allow read, write: if request.auth != null && request.auth.uid == uid;
       }
     }
   }
   ```
3. Click **Publish**.

This restricts every document to only be readable/writable by the matching signed-in user — nobody else, including other users of this same extension, can read or write your data.

## 5. Enable Google as a sign-in provider

1. Go to **Build → Authentication → Sign-in method**.
2. Click **Add new provider**, choose **Google**, toggle it **Enabled**, and save.

(This step is required — Firebase rejects sign-in attempts for any provider that isn't explicitly enabled here, even though the extension itself does the actual Google sign-in through Chrome, not Firebase's UI.)

## 6. Create an OAuth Client ID for the extension

Chrome extensions authenticate with Google through `chrome.identity`, which needs an OAuth Client ID of type **Chrome Extension**, tied to this extension's ID.

1. Load the extension unpacked first (`chrome://extensions` → Developer mode → **Load unpacked** → select this `chrome_extension` folder) so Chrome assigns it an ID. Because `manifest.json` already includes a fixed `"key"` field, this ID will stay the same across reloads and reinstalls on any machine using this same source — copy it from the extension's card on `chrome://extensions`.
2. Go to the [Google Cloud Console credentials page](https://console.cloud.google.com/apis/credentials), and make sure the project selected in the top bar is the **same project** as your Firebase project (Firebase projects are Google Cloud projects under the hood).
3. If prompted, configure the **OAuth consent screen** first: User type "External" is fine for personal/small-team use; app name/support email are the only required fields. You do not need to submit for verification since this extension only requests the `userinfo.email` scope, which is non-sensitive.
4. Click **Create credentials → OAuth client ID**.
5. Application type: **Chrome Extension**.
6. Application ID: paste the extension ID from step 1.
7. Click **Create**. Copy the generated **Client ID** (ends in `.apps.googleusercontent.com`).

## 7. Fill in the config files

Edit `chrome_extension/manifest.json` and replace the placeholder client ID:

```json
"oauth2": {
  "client_id": "YOUR_OAUTH_CLIENT_ID.apps.googleusercontent.com",
  ...
}
```

Edit `chrome_extension/firebase-config.js` and fill in the two values from steps 1-2:

```js
const FirebaseConfig = {
  FIREBASE_API_KEY: 'YOUR_FIREBASE_WEB_API_KEY',
  FIREBASE_PROJECT_ID: 'YOUR_FIREBASE_PROJECT_ID',
  ...
};
```

## 8. Reload the extension and sign in

1. Go to `chrome://extensions` and click the reload icon on the Time Tracker card (this picks up the manifest changes from step 7).
2. Open the extension's **Settings** (options page) → **Cloud Sync** section → **Sign in with Google**.
3. Approve the permission prompt. You should see the status change to "Signed in" and then "Last synced …" shortly after.
4. Repeat steps 8.1-8.3 with the same source folder and config values on any other device, signing in with the **same Google account**, to sync data between them.

## Notes

- Only the `userinfo.email` scope is requested — enough to identify which Firestore user-space belongs to you, nothing about your broader Google account.
- The Web API Key and Project ID aren't secret in the way a password is (they're visible in any Firebase web app's client code); what actually protects your data is the Firestore Security Rule from step 4, which is why setting it correctly matters.
- If you ever want to stop syncing on a device, use **Sign Out** in Settings. Local data on that device is untouched — only the sync connection stops.
