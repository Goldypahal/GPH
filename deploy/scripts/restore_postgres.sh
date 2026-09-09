#!/bin/bash
# ==============================================================================
# GIVIN PostGIS 16 Disaster Recovery Database Restore Script
# Validates Cryptographic Integrity Prior to Injection
# ==============================================================================

set -euo pipefail

if [ "$#" -ne 1 ]; then
    echo "Usage: $0 <path_to_backup_file.sql.gz>"
    exit 1
fi

BACKUP_FILE="$1"
HASH_FILE="${BACKUP_FILE%.sql.gz}.sha256"

if [ ! -f "${BACKUP_FILE}" ]; then
    echo "[ERROR] Backup file not found: ${BACKUP_FILE}"
    exit 1
fi

if [ -f "${HASH_FILE}" ]; then
    echo "[INFO] Verifying SHA-256 cryptographic seal..."
    sha256sum -c "${HASH_FILE}"
    echo "[PASS] Hash verification succeeded. Image is tamper-free."
else
    echo "[WARN] No .sha256 companion hash found. Proceeding with caution."
fi

echo "[INFO] Commencing restore into ${PGDATABASE:-givin_statewide}..."
gunzip -c "${BACKUP_FILE}" | pg_restore -h "${PGHOST:-localhost}" \
                                        -p "${PGPORT:-5432}" \
                                        -U "${PGUSER:-givin_admin}" \
                                        -d "${PGDATABASE:-givin_statewide}" \
                                        -v --clean --if-exists

echo "[SUCCESS] Database restoration complete."
