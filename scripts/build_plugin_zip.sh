#!/usr/bin/env bash
set -euo pipefail

# --- CONFIG ---
PLUGIN_ID="${PLUGIN_ID:-securable}"
DIST_DIR="${DIST_DIR:-dist}"
TAG="${1:-${GITHUB_REF_NAME:-}}"
PLUGIN_JSON_SOURCE=".claude-plugin/plugin.json"

if [[ -z "${TAG}" ]]; then
  echo "Tag is required. Pass it as the first argument or set GITHUB_REF_NAME." >&2
  exit 1
fi

if [[ ! -f "${PLUGIN_JSON_SOURCE}" ]]; then
  echo "Missing ${PLUGIN_JSON_SOURCE}" >&2
  exit 1
fi

ZIP_NAME="${PLUGIN_ID}-${TAG}.zip"
PLUGIN_VERSION="${TAG#v}"

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

# Ensure packaged plugin metadata lives at the plugin root with release version.
PYTHON_BIN=""
if command -v python3 >/dev/null 2>&1; then
  PYTHON_BIN="python3"
elif command -v python >/dev/null 2>&1; then
  PYTHON_BIN="python"
else
  echo "Python is required to generate ${PLUGIN_DIR}/plugin.json" >&2
  exit 1
fi

"${PYTHON_BIN}" - <<PYEOF
import json

source_path = "${PLUGIN_JSON_SOURCE}"
target_path = "${PLUGIN_DIR}/plugin.json"
version = "${PLUGIN_VERSION}"

with open(source_path, "r", encoding="utf-8") as f:
    plugin = json.load(f)

plugin["version"] = version

with open(target_path, "w", encoding="utf-8") as f:
    json.dump(plugin, f, indent=2)
    f.write("\n")
PYEOF

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
