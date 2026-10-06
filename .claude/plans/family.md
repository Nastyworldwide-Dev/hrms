CLASS: an icon-only button with no name and a 20 px hit area (axe button-name critical + target-size), in vendor code every screen reaches through a toast.
frontend/patches/frappe-ui+0.1.105.patch same-root (Toast.vue close: aria-label="Close", 44 px min hit area, -m-3 so the toast keeps its size; applied by postinstall patch-package)
frontend/src/components/glass/toast.js not-affected — wraps frappe-ui toast, renders no button
frontend/src/components/glass/GIconButton.vue not-affected — requires a label (its own test)
