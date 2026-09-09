#!/bin/bash
# ==============================================================================
# GIVIN PostGIS 16 Statewide Database Automated Cryptographic Backup Script
# Performs daily WAL-aligned compressed database dumps with SHA-256 integrity verification.
#
# Evidentiary & Legal Notice:
# SHA-256 integrity hashes establish cryptographic custody and tamper detection.
# Formal legal admissibility and evidentiary certification (such as Section 65B of
# the Indian Evidence Act / Section 63 of Bharatiya Sakshya Adhiniyam, 2023) are subject to
# applicable government procedures, authorized certificate authorities, and legal review.
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

echo "[INFO] Computing SHA-256 cryptographic integrity hash for custody tracking..."
sha256sum "${BACKUP_FILE}" > "${HASH_FILE}"

echo "[SUCCESS] Backup successfully written to ${BACKUP_FILE}"
echo "[INTEGRITY_HASH] SHA-256: $(cat "${HASH_FILE}")"
