#!/usr/bin/env bash
# Split a release zip if it exceeds GitHub's ~2 GiB asset limit.
set -euo pipefail

zip_path="${1:?zip path required}"
# Stay under 2147483648 bytes with headroom for metadata.
max_bytes=$((1900 * 1024 * 1024))

if [[ ! -f "$zip_path" ]]; then
  echo "split-release-zip: not found: $zip_path" >&2
  exit 1
fi

size=$(wc -c < "$zip_path" | tr -d ' ')
human=$(du -h "$zip_path" | cut -f1)
echo "Release zip size: $human ($size bytes)"

if (( size <= max_bytes )); then
  echo "Release zip fits GitHub asset limit."
  exit 0
fi

echo "Release zip exceeds GitHub asset limit; splitting..."
prefix="${zip_path}."
rm -f "${prefix}"*
split -b 1900M "$zip_path" "$prefix"
rm -f "$zip_path"
ls -lh "${prefix}"*
echo "Upload all parts (${prefix}*) and reassemble with: cat ${prefix}* > ${zip_path##*/}"
