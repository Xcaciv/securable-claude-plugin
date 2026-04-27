#!/usr/bin/env bash
set -euo pipefail

TAG="${1:-${GITHUB_REF_NAME:-}}"
PLUGIN_ID="${PLUGIN_ID:-securable}"
DIST_DIR="${DIST_DIR:-dist}"
REPOSITORY="${GITHUB_REPOSITORY:-}"
PLUGIN_JSON_PATH=".claude-plugin/plugin.json"

if [[ -z "${TAG}" ]]; then
  echo "Tag is required. Pass it as the first argument or set GITHUB_REF_NAME." >&2
  exit 1
fi

if [[ -z "${REPOSITORY}" ]]; then
  echo "GITHUB_REPOSITORY is required (format: owner/repo)." >&2
  exit 1
fi

if [[ ! -f "${PLUGIN_JSON_PATH}" ]]; then
  echo "Missing ${PLUGIN_JSON_PATH}" >&2
  exit 1
fi

ZIP_NAME="${PLUGIN_ID}-${TAG}.zip"
ZIP_URL="https://github.com/${REPOSITORY}/releases/download/${TAG}/${ZIP_NAME}"

mkdir -p "${DIST_DIR}"

jq -n \
  --arg tag "${TAG}" \
  --arg zip_url "${ZIP_URL}" \
  --argjson plugin "$(cat "${PLUGIN_JSON_PATH}")" \
  '{
    name: ($plugin.name + "-marketplace"),
    owner: {
      name: ($plugin.author.name // "")
    },
    metadata: {
      description: ($plugin.description // "")
    },
    plugins: [
      {
        name: $plugin.name,
        source: $zip_url,
        description: ($plugin.description // ""),
        version: $tag,
        author: ($plugin.author // {}),
        homepage: ($plugin.homepage // ""),
        repository: ($plugin.repository // ""),
        license: ($plugin.license // ""),
        keywords: ($plugin.keywords // []),
        category: "security",
        tags: ["release", $tag]
      }
    ]
  }' > "${DIST_DIR}/marketplace.json"

echo "Generated ${DIST_DIR}/marketplace.json"
echo "ZIP URL: ${ZIP_URL}"
