```markdown
# go

This repository is a production-oriented, automated proxy scanner scaffold.

Key files and folders
- `src/` - Python scanner sources and FastAPI health endpoints
- `bootstrap.sh` - idempotent local bootstrap (creates `cores/` stubs, optionally downloads real cores)
- `run_smoke_scan.py` - a lightweight smoke-run that generates `output/merged_nodes.txt` and `output/merged_sub_base64.txt`
- `Dockerfile`, `docker-compose.yml` - container images for running the scanner
- `.github/workflows/deploy_and_scan.yml` - CI workflow to run scheduled scans and optionally deploy Firebase functions (requires secrets)

CI & required secrets

To run the full CI workflow and enable deployment/scans you must add the following GitHub repository secrets:

- `GCP_SA_KEY` - JSON service account key for Google Cloud (optional if you use `FIREBASE_TOKEN` instead)
- `GCP_PROJECT_ID` - Google Cloud project id used by Firebase deployments
- `FIREBASE_TOKEN` - Firebase CLI token (alternative to `GCP_SA_KEY` for deploying functions)
- `SCAN_REPORT_URL` - Optional HTTP endpoint to receive scan reports
- `SCAN_REPORT_API_KEY` - Optional API key used to authenticate report uploads

How to bootstrap locally

1. Create required directories (bootstrap will do this automatically):

	bash ./bootstrap.sh

2. To download real core binaries (opt-in), run:

	DOWNLOAD_CORES=1 bash ./bootstrap.sh

Notes
- CI workflows that deploy to Firebase will not run successfully until you add the required secrets to the repository Settings → Secrets.
- The repository intentionally includes stubbed binaries in `cores/` so local testing and unit tests can run without network access.

License and contribution

This scaffold is provided as-is. Contributions welcome via pull requests.

```
# go