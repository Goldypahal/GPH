#!/bin/bash
# ==============================================================================
# GIVIN PostGIS 16 Statewide Database Automated Cryptographic Backup Script
# Conforms to Section 65B Chain of Custody & GSDC Air-Gapped Archival Policies
# ==============================================================================

set -euo pipefail

BACKUP_DIR="${BACKUP_DIR:-/var/backups/givin}"
TIMESTAMP=$(date -u +"%Y%m%d_%H%M%SZ")
BACKUP_FILE="${BACKUP_DIR}/givin_postgis_${TIMESTAMP}.sql.gz"
HASH_FILE="${BACKUP_DIR}/givin_postgis_${TIMESTAMP}.sha256"

mkdir -p "${BACKUP_DIR}"

echo "[INFO] Initiating PostGIS database dump at ${TIMESTAMP}..."
pg_dump -h "${PGHOST:-localhost}" \
        -p "${PGPORT:-5432}" \
        -U "${PGUSER:-givin_admin}" \
        -d "${PGDATABASE:-givin_statewide}" \
        -F c -b -v \
        | gzip -9 > "${BACKUP_FILE}"

echo "[INFO] Computing SHA-256 cryptographic seal for Section 65B compliance..."
sha256sum "${BACKUP_FILE}" > "${HASH_FILE}"

echo "[SUCCESS] Backup successfully written to ${BACKUP_FILE}"
echo "[SEAL] SHA-256 Hash: $(cat "${HASH_FILE}")"
