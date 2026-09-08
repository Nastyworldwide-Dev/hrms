// Read-only probes of actual Vue declarations. No browser/API/document writes.
// Run from repo root: node docs/glass/audit/2026-09-08-pwa-deep-probes.mjs
import fs from "node:fs"
import vm from "node:vm"
import { createRequire } from "node:module"
const require = createRequire(new URL("../../../frontend/package.json", import.meta.url))
const { parse } = require("acorn")
let failures = 0

function code(file, name) {
  const source = fs.readFileSync(file, "utf8").split("<script setup>")[1].split("</script>")[0]
  const nodes = parse(source, { ecmaVersion: "latest", sourceType: "module" }).body
  const node = nodes.find((n) => n.id?.name === name || n.declarations?.some((d) => d.id.name === name))
  if (!node) throw new Error(`Missing ${name}`)
  return source.slice(node.start, node.end)
}
function check(label, actual, expected) {
  const ok = JSON.stringify(actual) === JSON.stringify(expected)
  console.log(`${ok ? "PASS" : "FAIL"} ${label}: actual=${JSON.stringify(actual)} expected=${JSON.stringify(expected)}`)
  if (!ok) failures++
}

const sheet = "frontend/src/components/RequestActionSheet.vue"
// The local verification site's Permission Type table has no custom approval
// permission for these doctypes. These are its standard get_rights() keys.
const permissions = Object.fromEntries(["select", "read", "write", "create", "delete", "submit", "cancel", "amend", "print", "email", "report", "import", "export", "share"].map((k) => [k, 1]))
for (const dt of ["Leave Application", "Expense Claim", "Shift Request", "Attendance Request", "OT Request", "Replacement Leave Claim"]) {
  const context = vm.createContext({ props: { modelValue: { doctype: dt } }, document: { doc: { employee: "AUDIT-STAFF" } }, sessionEmployee: { data: { name: "AUDIT-MANAGER" } }, settings: { data: {} }, permittedWriteFields: { data: ["status", "approval_status"] }, approvalField: { value: dt === "Expense Claim" ? "approval_status" : "status" }, docPermissions: { data: { permissions } } })
  vm.runInContext(code(sheet, "hasPermission"), context)
  check(`${dt}: approval action for fully permitted non-self reviewer`, Boolean(vm.runInContext("hasPermission('approval')", context)), true)
}

const computed = (fn) => ({ get value() { return fn() } })
const form = "frontend/src/components/FormView.vue"
// Expense Claim approval_status actually has permlevel 1. An Employee-only
// named expense approver can satisfy server routing without that field right.
const manager = vm.createContext({ props: { id: "AUDIT-EXPENSE", doctype: "Expense Claim" }, isFormDirty: { value: false }, workflow: { value: null }, REQUEST_SUMMARY_FIELDS: { "Expense Claim": [] }, formModel: { value: { docstatus: 0, approval_status: "Draft", employee: "AUDIT-STAFF" } }, employee: { data: { name: "AUDIT-MANAGER" } }, permittedWriteFields: { data: ["remark"] }, computed })
vm.runInContext(`${code(form, "REVIEW_DECISION_FIELD")}\n${code(form, "canReview")}`, manager)
check("routed manager without status permlevel gets review entry", vm.runInContext("canReview.value", manager), true)

const source = fs.readFileSync(form, "utf8").split("<script setup>")[1].split("</script>")[0]
const tree = parse(source, { ecmaVersion: "latest", sourceType: "module" })
const watch = tree.body.find((n) => n.type === "ExpressionStatement" && n.expression.callee?.name === "watch" && source.slice(n.start, n.end).includes("if (!props.id) return"))
const dirty = vm.createContext({ props: { id: undefined }, isFormReady: { value: true }, isFormUpdated: { value: false }, isFormDirty: { value: false } })
const callback = watch.expression.arguments[1]
vm.runInContext(`(${source.slice(callback.start, callback.end)})()`, dirty)
check("new form changes arm discard protection", dirty.isFormDirty.value, true)

const upload = vm.createContext({ isFileUploading: { value: false }, props: { id: undefined }, fileAttachments: { value: [] }, FileAttachment: class { async upload() { throw new Error("synthetic rejected upload") } } })
let rejected = false
try { await vm.runInContext(`${code(form, "uploadAllAttachments")}\nuploadAllAttachments('Expense Claim','AUDIT-CLAIM',[{}])`, upload) } catch { rejected = true }
check("shared form reports failed attachment batch to caller", rejected, true)

// Execute installed frappe-ui resource implementation with controlled network
// completion order, then the unchanged OT summary callback from the Vue file.
const resourceSource = fs.readFileSync("frontend/node_modules/frappe-ui/src/resources/resources.js", "utf8")
const resourceTree = parse(resourceSource, { ecmaVersion: "latest", sourceType: "module" })
const resourceFns = resourceTree.body.filter((n) => n.type === "ExportNamedDeclaration" && ["createResource", "getCacheKey"].includes(n.declaration?.id?.name)).map((n) => resourceSource.slice(n.declaration.start, n.declaration.end)).join("\n")
const pending = {}
const race = vm.createContext({
  cached: {}, reactive: (x) => x, Event, saveLocal: () => {}, getConfig: () => undefined,
  request: ({ params }) => new Promise((resolve) => { pending[params.date] = resolve }),
  otRequest: { value: { ot_date: "2026-09-03" } },
  formFields: { data: [{ fieldname: "claimed_hours" }] },
  validateClaimedHours: () => {}, __: (s) => s, console,
})
vm.runInContext(`${resourceFns}\n${code("frontend/src/views/ot/OTRequestForm.vue", "otSummary")}`, race)
const first = vm.runInContext("otSummary.fetch({date:'2026-09-03'})", race)
race.otRequest.value.ot_date = "2026-09-04"
const second = vm.runInContext("otSummary.fetch({date:'2026-09-04'})", race)
pending["2026-09-04"]({ punch_ot_hours: 4, shift: "AUDIT-SHIFT", compensation: "Overtime Pay" })
await second
pending["2026-09-03"]({ punch_ot_hours: 1.5, shift: "AUDIT-SHIFT", compensation: "Overtime Pay" })
await first
check("rapid date selection keeps hours for current date", [race.otRequest.value.ot_date, race.otRequest.value.claimed_hours], ["2026-09-04", 4])

// Family hunt: the same unscoped persistence affects ordinary request resources,
// not only the notification list. Run actual OT resource + transform declarations.
const otModule = fs.readFileSync("frontend/src/data/overtime.js", "utf8")
const otTree = parse(otModule, { ecmaVersion: "latest", sourceType: "module" })
const otDeclarations = ["getOTDate", "transformOTRequests", "own", "myOTRequests"].map((name) => {
  const node = otTree.body.map((n) => n.type === "ExportNamedDeclaration" ? n.declaration : n).find((n) => n.declarations?.some((d) => d.id.name === name))
  return otModule.slice(node.start, node.end)
}).join("\n")
const cache = vm.createContext({
  cached: {}, reactive: (x) => x, Event, saveLocal: () => {}, getConfig: () => undefined,
  request: () => new Promise(() => {}),
  getLocal: async () => [{ name: "AUDIT-A-OT", employee: "AUDIT-ACCOUNT-A", ot_date: null }],
  employeeResource: { data: { name: "AUDIT-ACCOUNT-B" } },
})
vm.runInContext(`${resourceFns}\n${otDeclarations}`, cache)
await Promise.resolve()
check("account B OT list does not restore account A cached request", vm.runInContext("[myOTRequests.params.employee, myOTRequests.data?.[0]?.employee ?? null]", cache), ["AUDIT-ACCOUNT-B", null])
console.log(`RESULT ${failures} unmet properties; no application mutations`)
process.exitCode = failures ? 1 : 0
