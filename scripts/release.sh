#!/usr/bin/env bash
# One way to release the Nadi PWA (owner, 26 Sep 2026: tags kept going missing).
#
#   scripts/release.sh            tag + push + GitHub Release for the version in
#                                 frontend/package.json (the changelog entry must exist)
#   scripts/release.sh --backfill create any missing GitHub Release for existing
#                                 v2.0.0* tags, notes read from the changelog
#
# The version bump and changelog entry are a commit made before this runs; this
# script refuses to tag a version the changelog does not describe.
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"

log=docs/glass/CHANGELOG.md

notes_for() {
	# the changelog body of one version, heading excluded
	awk -v v="$1" '
		$0 ~ "^## \\[" v "\\]" { on = 1; next }
		on && /^## \[/ { exit }
		on { print }
	' "$log"
}

release_for() {
	local version=$1 tag="v$1" pre=""
	if gh release view "$tag" >/dev/null 2>&1; then
		echo "[release] $tag already has a GitHub Release"
		return
	fi
	[[ $version == *-* ]] && pre="--prerelease"
	notes_for "$version" > /tmp/nadi-release-notes.md
	gh release create "$tag" $pre --verify-tag --title "Nadi $version" --notes-file /tmp/nadi-release-notes.md
	echo "[release] created GitHub Release $tag"
}

if [[ ${1:-} == --backfill ]]; then
	for tag in $(git tag -l 'v2.0.0*' --sort=creatordate); do
		release_for "${tag#v}"
	done
	exit 0
fi

version=$(node -p "require('./frontend/package.json').version")
tag="v$version"
grep -q "^## \[$version\]" "$log" || { echo "[release] no changelog entry for $version" >&2; exit 1; }
[[ -z $(git status --porcelain --untracked-files=no -- frontend/package.json "$log") ]] || {
	echo "[release] commit the version bump and changelog first" >&2
	exit 1
}
if ! git rev-parse -q --verify "refs/tags/$tag" >/dev/null; then
	git tag -a "$tag" -m "Release $tag"
	echo "[release] tagged $tag"
fi
PIPELINE_SKIP_EVIDENCE=${PIPELINE_SKIP_EVIDENCE:-1} git push -q --follow-tags origin "$(git branch --show-current)"
release_for "$version"
