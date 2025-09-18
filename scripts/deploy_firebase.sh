#!/usr/bin/env bash
set -euo pipefail

# Safe deploy wrapper for Firebase resources. This script will only run commands
# you explicitly allow via --deploy. --preview shows the commands that would run.

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DRY=1

usage(){
  cat <<'USAGE'
Usage: deploy_firebase.sh [--preview|--deploy]

--preview : show commands that would run
--deploy  : perform deployment (requires gcloud & firebase CLI and authenticated user)
USAGE
}

if [ "${1:-}" = "--deploy" ]; then
  DRY=0
elif [ "${1:-}" = "--preview" ]; then
  DRY=1
else
  usage
  exit 0
fi

echo "[deploy] project dir: $ROOT_DIR/firebase"

CMDs=(
  "gcloud services enable firestore.googleapis.com cloudfunctions.googleapis.com cloudtasks.googleapis.com storage.googleapis.com"
  "gcloud firestore databases create --region=us-central"
  "cd $ROOT_DIR/firebase/functions && npm install"
  "firebase deploy --only functions,hosting --project \\$FIREBASE_PROJECT"
)

for c in "${CMDs[@]}"; do
  if [ $DRY -eq 1 ]; then
    echo "[preview] $c"
  else
    echo "[run] $c"
    eval "$c"
  fi
done

echo "[deploy] done (dry=$DRY)"
