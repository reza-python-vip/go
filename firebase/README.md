Firebase scaffolding and deployment notes
=====================================

This folder provides templates and instructions to deploy Firestore, Hosting, Cloud Functions, Cloud Storage, and Cloud Tasks for the proxy-scanner project.

Important: this repository does not create any cloud resources. To deploy, you must run the commands below with your Google Cloud / Firebase project and service-account credentials.

Quick steps
-----------

1. Create or choose a GCP project and enable the following APIs:
   - Cloud Functions
   - Cloud Tasks
   - Firestore
   - Cloud Storage
   - Identity Platform (optional for Auth)

2. Install tools:
   - gcloud CLI: https://cloud.google.com/sdk/docs/install
   - Firebase CLI: https://firebase.google.com/docs/cli

3. Authenticate and set project:

   gcloud auth login
   gcloud config set project YOUR_PROJECT_ID

4. Create a service account for CI with the minimal required roles (Firestore Service Agent, Cloud Functions Invoker, Cloud Tasks Enqueuer, Storage Admin or Storage Object Admin depending on needs). Generate a JSON key and store it as a GitHub Actions secret or in your CI vault.

5. Deploy (preview):

   bash scripts/deploy_firebase.sh --preview

6. Deploy (production):

   bash scripts/deploy_firebase.sh --deploy

Files in this folder
--------------------
- `firebase.json` - Firebase hosting + functions config
- `.firebaserc` - Firebase project alias placeholder
- `firestore.rules` - Example Firestore rules (readonly public data + basic admin path)
- `storage.rules` - Example Firebase Storage rules (restrict upload to authenticated service accounts)
- `functions/package.json` and `functions/index.js` - simple HTTP Cloud Function that receives scan results and writes to Firestore/Cloud Storage (stub)

See `scripts/deploy_firebase.sh` for a safe deploy wrapper.
