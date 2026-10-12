#!/usr/bin/env bash
#
# Cut a release: bump the version, update CHANGELOG.md, commit, tag and push.
#
#   scripts/release.sh patch    # 0.2.0 -> 0.2.1  bug fixes only
#   scripts/release.sh minor    # 0.2.1 -> 0.3.0  new features
#   scripts/release.sh major    # 0.3.0 -> 1.0.0  breaking changes
#
# The version lives in backend/pyproject.toml (the source of truth, shown in the
# app's sidebar) and is mirrored into frontend/package.json and both lockfiles.
# Set RELEASE_TRAILER to append a trailer line (e.g. Co-Authored-By) to the commit.

set -euo pipefail
cd "$(dirname "$0")/.."

die() { printf 'release: %s\n' "$*" >&2; exit 1; }

level="${1:-}"
case "$level" in patch|minor|major) ;; *) die "usage: scripts/release.sh patch|minor|major" ;; esac

[ "$(git branch --show-current)" = "main" ] || die "releases are made from main"
[ -z "$(git status --porcelain)" ] || die "commit or stash your changes first"
git fetch --quiet --tags origin
git merge-base --is-ancestor origin/main HEAD || die "main is behind origin/main; pull first"

current="$(sed -n 's/^version = "\(.*\)"$/\1/p' backend/pyproject.toml)"
[[ "$current" =~ ^([0-9]+)\.([0-9]+)\.([0-9]+)$ ]] || die "can't read version from backend/pyproject.toml"
major="${BASH_REMATCH[1]}" minor="${BASH_REMATCH[2]}" patch="${BASH_REMATCH[3]}"
case "$level" in
  major) next="$((major + 1)).0.0" ;;
  minor) next="$major.$((minor + 1)).0" ;;
  patch) next="$major.$minor.$((patch + 1))" ;;
esac
tag="v$next"
git rev-parse --quiet --verify "refs/tags/$tag" >/dev/null && die "tag $tag already exists"

last_tag="$(git describe --tags --abbrev=0 --match 'v[0-9]*' 2>/dev/null || true)"
notes="$(git log --no-merges --format='- %s' ${last_tag:+"$last_tag"..}HEAD | grep -v '^- Release v' || true)"
[ -n "$notes" ] || die "no changes since ${last_tag:-the first commit}"

echo "Releasing $tag (was $current). Changes:"
echo "$notes"

# Bump the version everywhere it appears.
sed -i.bak "s/^version = \"$current\"$/version = \"$next\"/" backend/pyproject.toml && rm backend/pyproject.toml.bak
(cd backend && uv lock --quiet)
(cd frontend && npm version "$next" --no-git-tag-version --allow-same-version >/dev/null)

# Newest release first, below the file's title.
entry="$(printf '## %s (%s)\n\n%s\n' "$tag" "$(date +%Y-%m-%d)" "$notes")"
{
  head -n 2 CHANGELOG.md
  printf '%s\n\n' "$entry"
  tail -n +3 CHANGELOG.md
} > CHANGELOG.md.new && mv CHANGELOG.md.new CHANGELOG.md

git add backend/pyproject.toml backend/uv.lock frontend/package.json frontend/package-lock.json CHANGELOG.md
if [ -n "${RELEASE_TRAILER:-}" ]; then
  git commit --quiet -m "Release $tag" -m "$RELEASE_TRAILER"
else
  git commit --quiet -m "Release $tag"
fi
git tag -a "$tag" -m "$tag" -m "$notes"
git push --quiet origin main "$tag"
echo "Released $tag"
