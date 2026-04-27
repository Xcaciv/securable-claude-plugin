#!/usr/bin/env bash
set -euo pipefail

# --- CONFIG ---
PLUGIN_ID="${PLUGIN_ID:-securable}"
DIST_DIR="${DIST_DIR:-dist}"
TAG="${1:-${GITHUB_REF_NAME:-}}"

if [[ -z "${TAG}" ]]; then
  echo "Tag is required. Pass it as the first argument or set GITHUB_REF_NAME." >&2
  exit 1
fi

ZIP_NAME="${PLUGIN_ID}-${TAG}.zip"

# --- PREP ---
echo "-> Cleaning dist directory"
rm -rf "${DIST_DIR}"
mkdir -p "${DIST_DIR}"

echo "-> Creating temporary build directory"
BUILD_DIR="$(mktemp -d)"
PLUGIN_DIR="${BUILD_DIR}/${PLUGIN_ID}"
mkdir -p "${PLUGIN_DIR}"

cleanup() {
  rm -rf "${BUILD_DIR}"
}
trap cleanup EXIT

# --- COPY FILES ---
echo "-> Copying plugin files into build directory"
rsync -av \
  --exclude ".git" \
  --exclude "dist" \
  --exclude ".DS_Store" \
  --exclude ".*.swp" \
  ./ "${PLUGIN_DIR}/"

# --- ZIP ---
echo "-> Creating ZIP archive"
(
  cd "${BUILD_DIR}"
  zip -r "${ZIP_NAME}" "${PLUGIN_ID}"
)

mv "${BUILD_DIR}/${ZIP_NAME}" "${DIST_DIR}/"

# --- HASH ---
echo "-> Generating SHA256 hash"
if command -v sha256sum >/dev/null 2>&1; then
  sha256sum "${DIST_DIR}/${ZIP_NAME}" | awk '{print $1}' > "${DIST_DIR}/${ZIP_NAME}.sha256"
else
  shasum -a 256 "${DIST_DIR}/${ZIP_NAME}" | awk '{print $1}' > "${DIST_DIR}/${ZIP_NAME}.sha256"
fi

# --- DONE ---
echo
echo "ZIP created: ${DIST_DIR}/${ZIP_NAME}"
echo "SHA256 written to: ${DIST_DIR}/${ZIP_NAME}.sha256"
echo
echo "SHA256:"
cat "${DIST_DIR}/${ZIP_NAME}.sha256"
echo
echo "Done."
