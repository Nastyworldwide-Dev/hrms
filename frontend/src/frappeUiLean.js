// What this app uses from frappe-ui, and nothing else (alpha.12 C4).
//
// frappe-ui's index re-exports its whole component set, and the package does
// not declare itself side-effect free, so `import { createResource } from
// "frappe-ui"` pulled the rich-text editor (prosemirror, tiptap), 157 KB of
// feather icons, the markdown converter and popper into EVERY first download:
// 1.47 MB of JS before anything drew, 10.4 s to first paint on a slow phone.
// vite.config.js aliases the bare "frappe-ui" import to this file, so no call
// site changes; deep imports ("frappe-ui/src/...", "frappe-ui/vite") are not
// affected. A new frappe-ui import must be added here (the build fails loudly
// on a missing export).
export { createResource, createListResource, createDocumentResource, resourcesPlugin } from "../node_modules/frappe-ui/src/resources/index.js"
export { frappeRequest } from "../node_modules/frappe-ui/src/utils/frappeRequest.js"
export { setConfig } from "../node_modules/frappe-ui/src/utils/config.js"
export { default as call } from "../node_modules/frappe-ui/src/utils/call.js"
export { default as debounce } from "../node_modules/frappe-ui/src/utils/debounce.ts"
export { toast, Toasts } from "../node_modules/frappe-ui/src/components/toast.js"
export { default as ErrorMessage } from "../node_modules/frappe-ui/src/components/ErrorMessage.vue"
