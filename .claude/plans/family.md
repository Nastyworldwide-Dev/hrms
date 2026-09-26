CLASS: a release step (tag, GitHub Release) done by hand and so sometimes skipped
scripts/release.sh — same-root (new: one command tags, pushes, creates the GitHub Release)
design/gates/release-tags.test.mjs — same-root (new: every changelog version has a tag or names the build that carried it)
docs/glass/CHANGELOG.md alpha.8/alpha.9 — same-root (say they shipped in alpha.10)
.github/workflows/build-and-commit-assets.yml — not-affected — its assets-* rolling release is the Frappe asset bundle, not a version release
