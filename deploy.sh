#!/bin/bash
set -e

# =============================================================================
# Strava Analyzer - Cloud Run Deployment Script
# =============================================================================
# Prerequisites:
#   1. gcloud CLI installed and authenticated
#   2. Docker installed (for local builds) OR use Cloud Build
#   3. .env file configured with required values
# =============================================================================

# Load environment variables from .env file
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [ -f "${SCRIPT_DIR}/.env" ]; then
    echo "Loading configuration from .env file..."
    set -a
    source "${SCRIPT_DIR}/.env"
    set +a
else
    echo "ERROR: .env file not found. Copy .env-template to .env and fill in values."
    exit 1
fi

# -----------------------------------------------------------------------------
# CONFIGURATION - These can be overridden in .env or set here
# -----------------------------------------------------------------------------
PROJECT_ID="${GCP_PROJECT_ID:-YOUR_GCP_PROJECT_ID}"
REGION="${GCP_REGION:-europe-west1}"
SERVICE_NAME="strava-analyzer"
GCS_BUCKET_NAME="${GCS_BUCKET_NAME:-YOUR_BUCKET_NAME}"
DOMAIN="${DOMAIN:-strava.bngrd.com}"
ADMIN_USERNAME="${ADMIN_USERNAME:-admin}"

# -----------------------------------------------------------------------------
# Derived values
# -----------------------------------------------------------------------------
IMAGE_NAME="${REGION}-docker.pkg.dev/${PROJECT_ID}/strava/${SERVICE_NAME}"

# -----------------------------------------------------------------------------
# Helper functions
# -----------------------------------------------------------------------------
log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $1"
}

# -----------------------------------------------------------------------------
# Step 1: Enable required APIs
# -----------------------------------------------------------------------------
enable_apis() {
    log "Enabling required GCP APIs..."
    gcloud services enable \
        run.googleapis.com \
        artifactregistry.googleapis.com \
        cloudbuild.googleapis.com \
        secretmanager.googleapis.com \
        storage.googleapis.com \
        --project="${PROJECT_ID}"
}

# -----------------------------------------------------------------------------
# Step 2: Create Artifact Registry repository
# -----------------------------------------------------------------------------
create_artifact_registry() {
    log "Creating Artifact Registry repository..."
    gcloud artifacts repositories create strava \
        --repository-format=docker \
        --location="${REGION}" \
        --project="${PROJECT_ID}" \
        --description="Strava Analyzer container images" \
        2>/dev/null || log "Repository already exists"
}

# -----------------------------------------------------------------------------
# Step 3: Create GCS bucket
# -----------------------------------------------------------------------------
create_gcs_bucket() {
    log "Creating GCS bucket..."
    gcloud storage buckets create "gs://${GCS_BUCKET_NAME}" \
        --project="${PROJECT_ID}" \
        --location="${REGION}" \
        --uniform-bucket-level-access \
        2>/dev/null || log "Bucket already exists"
}

# -----------------------------------------------------------------------------
# Step 4: Create secrets in Secret Manager
# -----------------------------------------------------------------------------
create_secrets() {
    log "Creating secrets in Secret Manager..."

    # Create secrets (ignore errors if they exist)
    echo -n "${STRAVA_CLIENT_ID}" | gcloud secrets create strava-client-id \
        --data-file=- --project="${PROJECT_ID}" 2>/dev/null || \
        echo -n "${STRAVA_CLIENT_ID}" | gcloud secrets versions add strava-client-id \
        --data-file=- --project="${PROJECT_ID}"

    echo -n "${STRAVA_CLIENT_SECRET}" | gcloud secrets create strava-client-secret \
        --data-file=- --project="${PROJECT_ID}" 2>/dev/null || \
        echo -n "${STRAVA_CLIENT_SECRET}" | gcloud secrets versions add strava-client-secret \
        --data-file=- --project="${PROJECT_ID}"

    echo -n "${STRAVA_VERIFY_TOKEN}" | gcloud secrets create strava-verify-token \
        --data-file=- --project="${PROJECT_ID}" 2>/dev/null || \
        echo -n "${STRAVA_VERIFY_TOKEN}" | gcloud secrets versions add strava-verify-token \
        --data-file=- --project="${PROJECT_ID}"

    echo -n "${JWT_SECRET_KEY}" | gcloud secrets create jwt-secret-key \
        --data-file=- --project="${PROJECT_ID}" 2>/dev/null || \
        echo -n "${JWT_SECRET_KEY}" | gcloud secrets versions add jwt-secret-key \
        --data-file=- --project="${PROJECT_ID}"

    echo -n "${ADMIN_PASSWORD_HASH}" | gcloud secrets create admin-password-hash \
        --data-file=- --project="${PROJECT_ID}" 2>/dev/null || \
        echo -n "${ADMIN_PASSWORD_HASH}" | gcloud secrets versions add admin-password-hash \
        --data-file=- --project="${PROJECT_ID}"

    log "Secrets created/updated"
}

# -----------------------------------------------------------------------------
# Step 5: Build and push container image
# -----------------------------------------------------------------------------
build_and_push() {
    log "Building and pushing container image using Cloud Build..."
    gcloud builds submit \
        --tag="${IMAGE_NAME}" \
        --project="${PROJECT_ID}"
}

# -----------------------------------------------------------------------------
# Step 6: Deploy to Cloud Run
# -----------------------------------------------------------------------------
deploy_cloud_run() {
    log "Deploying to Cloud Run..."
    gcloud run deploy "${SERVICE_NAME}" \
        --image="${IMAGE_NAME}" \
        --platform=managed \
        --region="${REGION}" \
        --project="${PROJECT_ID}" \
        --allow-unauthenticated \
        --set-env-vars="GCS_BUCKET_NAME=${GCS_BUCKET_NAME},GCP_PROJECT_ID=${PROJECT_ID},STRAVA_REDIRECT_URI=https://${DOMAIN}/auth/callback,ADMIN_USERNAME=${ADMIN_USERNAME}" \
        --set-secrets="STRAVA_CLIENT_ID=strava-client-id:latest,STRAVA_CLIENT_SECRET=strava-client-secret:latest,STRAVA_VERIFY_TOKEN=strava-verify-token:latest,JWT_SECRET_KEY=jwt-secret-key:latest,ADMIN_PASSWORD_HASH=admin-password-hash:latest" \
        --memory=512Mi \
        --cpu=1 \
        --min-instances=0 \
        --max-instances=10 \
        --timeout=60
}

# -----------------------------------------------------------------------------
# Step 7: Map custom domain
# -----------------------------------------------------------------------------
map_domain() {
    log "Mapping custom domain ${DOMAIN}..."
    gcloud run domain-mappings create \
        --service="${SERVICE_NAME}" \
        --domain="${DOMAIN}" \
        --region="${REGION}" \
        --project="${PROJECT_ID}" \
        2>/dev/null || log "Domain mapping already exists"

    log ""
    log "=============================================="
    log "IMPORTANT: Add this DNS record to your domain:"
    log "=============================================="
    gcloud run domain-mappings describe \
        --domain="${DOMAIN}" \
        --region="${REGION}" \
        --project="${PROJECT_ID}" \
        --format="value(status.resourceRecords)"
    log ""
}

# -----------------------------------------------------------------------------
# Step 8: Grant Cloud Run service account access to GCS and Secrets
# -----------------------------------------------------------------------------
grant_permissions() {
    log "Granting permissions to Cloud Run service account..."

    # Get the Cloud Run service account
    SA="${PROJECT_ID}@${PROJECT_ID}.iam.gserviceaccount.com"
    COMPUTE_SA="$(gcloud projects describe ${PROJECT_ID} --format='value(projectNumber)')-compute@developer.gserviceaccount.com"

    # Grant GCS access
    gcloud storage buckets add-iam-policy-binding "gs://${GCS_BUCKET_NAME}" \
        --member="serviceAccount:${COMPUTE_SA}" \
        --role="roles/storage.objectAdmin" \
        --project="${PROJECT_ID}"

    # Grant Secret Manager access
    gcloud secrets add-iam-policy-binding strava-client-id \
        --member="serviceAccount:${COMPUTE_SA}" \
        --role="roles/secretmanager.secretAccessor" \
        --project="${PROJECT_ID}"

    gcloud secrets add-iam-policy-binding strava-client-secret \
        --member="serviceAccount:${COMPUTE_SA}" \
        --role="roles/secretmanager.secretAccessor" \
        --project="${PROJECT_ID}"

    gcloud secrets add-iam-policy-binding strava-verify-token \
        --member="serviceAccount:${COMPUTE_SA}" \
        --role="roles/secretmanager.secretAccessor" \
        --project="${PROJECT_ID}"

    gcloud secrets add-iam-policy-binding jwt-secret-key \
        --member="serviceAccount:${COMPUTE_SA}" \
        --role="roles/secretmanager.secretAccessor" \
        --project="${PROJECT_ID}"

    gcloud secrets add-iam-policy-binding admin-password-hash \
        --member="serviceAccount:${COMPUTE_SA}" \
        --role="roles/secretmanager.secretAccessor" \
        --project="${PROJECT_ID}"

    log "Permissions granted"
}

# -----------------------------------------------------------------------------
# Main execution
# -----------------------------------------------------------------------------
main() {
    log "Starting deployment of Strava Analyzer to Cloud Run"
    log "Project: ${PROJECT_ID}"
    log "Region: ${REGION}"
    log "Domain: ${DOMAIN}"
    log ""

    enable_apis
    create_artifact_registry
    create_gcs_bucket
    create_secrets
    grant_permissions
    build_and_push
    deploy_cloud_run
    map_domain

    log ""
    log "=============================================="
    log "Deployment complete!"
    log "=============================================="
    log ""
    log "Service URL: https://${DOMAIN}"
    log ""
    log "Next steps:"
    log "1. Add the DNS record shown above to your domain"
    log "2. Register your Strava webhook at:"
    log "   https://www.strava.com/settings/api"
    log ""
    log "   Webhook callback URL: https://${DOMAIN}/strava/webhook"
    log "   Verify token: ${STRAVA_VERIFY_TOKEN}"
    log ""
    log "3. Complete OAuth by visiting:"
    log "   https://${DOMAIN}/auth/authorize"
    log ""
}

# Run main function
main "$@"
