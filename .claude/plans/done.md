GOAL: You shows "Nadi <version> · <release name>" and no date or time; the name is one source (package.json releaseName), heads the changelog, titles the GitHub Release.
DONE WHEN: Profile uses __APP_RELEASE_NAME__, no __APP_BUILD__ on any screen; release.sh titles "Nadi v — Name"; version gate checks name from alpha.14.
CHECK: node --test design/gates/version.test.mjs; WebKit You: "Nadi 2.0.0-alpha.13", no date/time
