// Read-only synthetic probes. Executes actual source bodies with browser/network
// boundaries replaced by deterministic fakes. Assertions describe current defects.
import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import vm from "node:vm"
import { notificationRoute } from "../../../frontend/src/utils/notifications.js"

const root = new URL("../../../", import.meta.url)
const read = (path) => readFileSync(new URL(path, root), "utf8")
const stripImports = (src) => src.replace(/^import\s+[\s\S]*?from\s+["'][^"']+["']\s*\n/gm, "")
const output = []
const quietConsole = { info() {}, log() {}, error() {} }

// Foreground Firefox/Safari notification -> the actual worker click handler.
let shown
let click
let opened = 0
const foreground = vm.createContext({
  navigator: { userAgent: "Firefox/130" },
  window: { frappePushNotification: { serviceWorkerRegistration: {
    showNotification: (title, options) => { shown = options },
  } } },
})
vm.runInContext(read("frontend/src/utils/pushNotifications.js").replaceAll("export ", ""), foreground)
vm.runInContext('showNotification({data:{title:"Synthetic",click_action:"https://example.invalid/hrms/ot-requests/OT-TEST"}})', foreground)
const worker = vm.createContext({
  console: quietConsole,
  URL,
  location: "https://example.invalid/sw.js?config={}",
  navigator: { userAgent: "Firefox/130" },
  precacheAndRoute() {}, cleanupOutdatedCaches() {}, clientsClaim() {},
  initializeApp: (config) => config, getMessaging: () => ({}), onBackgroundMessage() {},
  clients: { openWindow() { opened++ } },
  self: { __WB_MANIFEST: [], skipWaiting() {}, addEventListener(event, handler) { if (event === "notificationclick") click = handler } },
})
vm.runInContext(stripImports(read("frontend/public/sw.js")), worker)
click({ notification: { ...shown, close() {} }, action: "", stopImmediatePropagation() {} })
assert.equal(opened, 0)
output.push("N-PUSH-CLICK reproduced: foreground Firefox body tap opens 0 windows")

const saved = new Map()
let subscriptionCalls = 0
const sdkContext = vm.createContext({
  console: quietConsole,
  localStorage: { getItem: (key) => saved.get(key) ?? null, setItem: (key, val) => saved.set(key, val), removeItem: (key) => saved.delete(key) },
  Notification: { requestPermission: async () => "granted" },
  isSupported: async () => true, getToken: async () => "SYNTHETIC_DEVICE_TOKEN", deleteToken: async () => {},
  fetch: async () => { subscriptionCalls++; return { status: 200, json: async () => ({message:{success:false,message:"Synthetic rejection"}}) } },
})
vm.runInContext(stripImports(read("frontend/public/frappe-push-notification.js")).replace("export default FrappePushNotification", "globalThis.SDK = FrappePushNotification"), sdkContext)
const first = new sdkContext.SDK("hrms")
first.fetchVapidPublicKey = async () => "synthetic-vapid"
const result = await first.enableNotification()
assert.equal(result.permission_granted, true)
assert.equal(first.isNotificationEnabled(), true)
assert.equal(subscriptionCalls, 1)
output.push("N-PUSH-ACK reproduced: HTTP 200 success:false still saves enabled state")

// Full page reload after logout creates a fresh SDK, but same browser storage.
const nextUser = new sdkContext.SDK("hrms")
nextUser.fetchVapidPublicKey = async () => "synthetic-vapid"
await nextUser.enableNotification()
assert.equal(subscriptionCalls, 1)
output.push("N-PUSH-IDENTITY reproduced: second account enable makes 0 new subscription calls")

// Installed frappe-ui list resource, with storage/transport stubs only.
const oldRows = [{name:"synthetic-A",message:"Synthetic prior-user notification"}]
const listContext = vm.createContext({
  reactive: (value) => value,
  getConfig: () => undefined,
  getCacheKey: (key) => key,
  saveLocal() {}, getLocal: async () => oldRows,
  createResource: (options) => ({ error: "Synthetic 403", loading:false, fetched:false, options }),
})
vm.runInContext(stripImports(read("frontend/node_modules/frappe-ui/src/resources/listResource.js")).replaceAll("export function", "function") + '\nglobalThis.makeList = createListResource', listContext)
const list = listContext.makeList({doctype:"PWA Notification", cache:"hrms:notifications",filters:{to_user:"synthetic-B@example.invalid"}, auto:false})
await Promise.resolve()
assert.equal(list.data[0].name, "synthetic-A")
assert.equal(list.error, undefined)
assert.equal(list.list.error, "Synthetic 403")
output.push("N-CACHE-IDENTITY reproduced: user B list hydrates user A cached notification")
output.push("N-FEED-ERROR reproduced: list.error undefined while list.list.error contains 403")

const route = notificationRoute({reference_document_type:"Remote Checkin Request",reference_document_name:"RCR-SYNTHETIC"}, "Approved", () => true)
assert.equal(route.name, "RemoteApprovals")
assert.equal(route.params, undefined)
output.push("N-REMOTE-ROUTE reproduced: employee decision notification lands on approver-only History, without request id")
for (const line of output) console.log(line)
console.log(`Confirmed ${output.length} synthetic observations; no network or application writes`)
