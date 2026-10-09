#!/usr/bin/env bash
# Prepara en GCP (proyecto nexura-preproduccion-qa) la integracion Azure DevOps -> GCP por
# Workload Identity Federation, replicando lo que ya existe en pre-qa-functions:
#   pool azure-devops-pool / provider azure-devops-vstoken / SAs azure-deployer + deploy-sa.
#
# Debe ejecutarlo alguien con rol de administrador en el proyecto (Owner, o IAM Admin +
# Workload Identity Pool Admin + Service Usage Admin). Es idempotente en lo posible:
# los 'create' que ya existan fallan sin dañar nada.
#
# Despues de correrlo, crear la service connection en ADO (ver README o la guia en el
# chat): tipo "Google Cloud (WIF)", nombre EXACTO gcp-nexura-preproduccion-qa.
set -euo pipefail

PROJECT_ID="nexura-preproduccion-qa"
PROJECT_NUMBER="999421923761"
REGION="us-east1"

# Azure DevOps
ADO_ORG="nexura"
ADO_ORG_ID="98176ab1-0c26-482c-b5c7-0f224f8ac725"   # issuer vstoken.dev.azure.com/<id>
ADO_PROJECT="Nexura Platform Microservicios"
SERVICE_CONNECTION="gcp-nexura-preproduccion-qa"

POOL="azure-devops-pool"
PROVIDER="azure-devops-vstoken"
DEPLOYER="azure-deployer"     # SA que asume la identidad federada (solo lanza builds)
BUILDER="deploy-sa"           # SA que EJECUTA el build y despliega
RUNTIME_SA="${PROJECT_NUMBER}-compute@developer.gserviceaccount.com"  # SA de runtime de los servicios
STAGING_BUCKET="${PROJECT_ID}_cloudbuild"

gcloud config set project "${PROJECT_ID}"

# 1. APIs (sts es indispensable para WIF)
gcloud services enable sts.googleapis.com iamcredentials.googleapis.com \
  cloudbuild.googleapis.com run.googleapis.com artifactregistry.googleapis.com

# 2. Pool + provider OIDC de Azure DevOps (solo acepta subjects de la org nexura)
gcloud iam workload-identity-pools create "${POOL}" --location=global \
  --display-name="Azure DevOps"
gcloud iam workload-identity-pools providers create-oidc "${PROVIDER}" \
  --location=global --workload-identity-pool="${POOL}" \
  --display-name="Azure DevOps (issuer vstoken)" \
  --issuer-uri="https://vstoken.dev.azure.com/${ADO_ORG_ID}" \
  --allowed-audiences="api://AzureADTokenExchange" \
  --attribute-mapping="google.subject=assertion.sub" \
  --attribute-condition="assertion.sub.startsWith('sc://${ADO_ORG}/')"

# 3. Service accounts
gcloud iam service-accounts create "${DEPLOYER}" --display-name="Azure DevOps deployer (WIF)"
gcloud iam service-accounts create "${BUILDER}"  --display-name="Cloud Build deploy SA"

DEPLOYER_EMAIL="${DEPLOYER}@${PROJECT_ID}.iam.gserviceaccount.com"
BUILDER_EMAIL="${BUILDER}@${PROJECT_ID}.iam.gserviceaccount.com"

# 4. Solo la service connection de ADO puede asumir azure-deployer
gcloud iam service-accounts add-iam-policy-binding "${DEPLOYER_EMAIL}" \
  --role=roles/iam.workloadIdentityUser \
  --member="principal://iam.googleapis.com/projects/${PROJECT_NUMBER}/locations/global/workloadIdentityPools/${POOL}/subject/sc://${ADO_ORG}/${ADO_PROJECT}/${SERVICE_CONNECTION}"

# 5. azure-deployer: lanzar builds y actuar como deploy-sa
gcloud projects add-iam-policy-binding "${PROJECT_ID}" \
  --member="serviceAccount:${DEPLOYER_EMAIL}" --role=roles/cloudbuild.builds.editor
gcloud iam service-accounts add-iam-policy-binding "${BUILDER_EMAIL}" \
  --member="serviceAccount:${DEPLOYER_EMAIL}" --role=roles/iam.serviceAccountUser

# 6. deploy-sa: escribir imagenes, desplegar en Cloud Run, loguear, y actuar como la SA de runtime
for ROLE in roles/artifactregistry.writer roles/run.developer roles/logging.logWriter; do
  gcloud projects add-iam-policy-binding "${PROJECT_ID}" \
    --member="serviceAccount:${BUILDER_EMAIL}" --role="${ROLE}"
done
gcloud iam service-accounts add-iam-policy-binding "${RUNTIME_SA}" \
  --member="serviceAccount:${BUILDER_EMAIL}" --role=roles/iam.serviceAccountUser

# 7. Bucket de staging del codigo fuente (gcloud builds submit --gcs-source-staging-dir)
gcloud storage buckets create "gs://${STAGING_BUCKET}" --location="${REGION}" \
  --uniform-bucket-level-access
gcloud storage buckets add-iam-policy-binding "gs://${STAGING_BUCKET}" \
  --member="serviceAccount:${DEPLOYER_EMAIL}" --role=roles/storage.objectAdmin
gcloud storage buckets add-iam-policy-binding "gs://${STAGING_BUCKET}" \
  --member="serviceAccount:${DEPLOYER_EMAIL}" --role=roles/storage.legacyBucketReader
gcloud storage buckets add-iam-policy-binding "gs://${STAGING_BUCKET}" \
  --member="serviceAccount:${BUILDER_EMAIL}" --role=roles/storage.objectViewer

echo
echo "Listo. Datos para la service connection de ADO:"
echo "  Workload Identity Provider: projects/${PROJECT_NUMBER}/locations/global/workloadIdentityPools/${POOL}/providers/${PROVIDER}"
echo "  Service account:            ${DEPLOYER_EMAIL}"
echo "  Project ID / number:        ${PROJECT_ID} / ${PROJECT_NUMBER}"
