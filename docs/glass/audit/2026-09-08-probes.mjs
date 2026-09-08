// Synthetic executions of actual Vue script declarations, without mounting Vue.
// Run: node docs/glass/audit/2026-09-08-probes.mjs
// Exit 1 identifies unmet properties. No API calls, GPS access or data writes.
import fs from "node:fs"
import vm from "node:vm"
import { createRequire } from "node:module"

const require = createRequire(new URL("../../../frontend/package.json", import.meta.url))
const { parse } = require("acorn")
let failures = 0
const translate = (s, args = []) => s.replace(/\{(\d+)\}/g, (_, i) => args[i])
const computed = (fn) => ({ get value() { return fn() } })

function declaration(file, name) {
  const source = fs.readFileSync(file, "utf8").split("<script setup>")[1].split("</script>")[0]
  const tree = parse(source, { ecmaVersion: "latest", sourceType: "module" })
  const node = tree.body.find((n) => n.id?.name === name || n.declarations?.some((d) => d.id.name === name))
  if (!node) throw new Error(`Declaration missing: ${name}`)
  return source.slice(node.start, node.end)
}

function check(label, actual, expected) {
  const ok = JSON.stringify(actual) === JSON.stringify(expected)
  console.log(`${ok ? "PASS" : "FAIL"} ${label}: actual=${JSON.stringify(actual)}; expected=${JSON.stringify(expected)}`)
  if (!ok) failures++
}

const panel = "frontend/src/components/CheckInPanel.vue"
const context = vm.createContext({
  geolocationBlockedReason: () => null, __: translate, console,
  locationStatus: { value: "" }, locationError: { value: "" },
  latitude: { value: 3.1 }, longitude: { value: 101.6 }, accuracyM: { value: 40 },
  hasSessionFix: true, coarseFallbackRequested: false, fixTimestamp: 100,
  geoWatchId: null, navigator: { geolocation: { watchPosition: () => 1 } },
  handleLocationSuccess: () => {}, handleLocationError: () => {},
})
vm.runInContext(`${declaration(panel, "fetchLocation")}\nfetchLocation()`, context)
check("opening sheet clears old coordinates", [context.latitude.value, context.longitude.value], [null, null])
check("opening sheet clears accuracy", context.accuracyM.value, null)

const verdict = vm.createContext({
  computed, __: translate, locationError: { value: "" },
  shiftLocation: { data: { checkin_radius: 100, label: "Test office", strict: false } },
  distanceToShift: { value: 120 }, accuracyM: { value: 40 },
  nextAction: { value: { action: "OUT" } },
})
vm.runInContext(`${declaration(panel, "isInsideRadius")}\n${declaration(panel, "locationVerdict")}`, verdict)
check("preview agrees with server accuracy allowance", vm.runInContext("isInsideRadius.value", verdict), true)
verdict.shiftLocation.data.checkin_radius = 1000
verdict.distanceToShift.value = 1300
verdict.accuracyM.value = 1500
console.log("INFO coarse-fix screen:", vm.runInContext("locationVerdict.value", verdict))

const field = vm.createContext({ computed, props: { readOnly: true, modelValue: 0, fieldtype: "Float", hidden: false }, isLayoutField: { value: false } })
vm.runInContext(declaration("frontend/src/components/FormField.vue", "showField"), field)
check("zero read-only claim remains visible", vm.runInContext("showField.value", field), true)

const form = vm.createContext({
  props: { fields: [
    { fieldname: "claimed_hours", label: "Claimed Hours", reqd: 1, error_message: "No punch-verified overtime for this date — nothing to claim" },
    { fieldname: "explanation", label: "Explanation", reqd: 1 },
  ] },
  formModel: { value: { claimed_hours: 0, explanation: "" } }, formErrorMessage: { value: "" },
})
vm.runInContext(`${declaration("frontend/src/components/FormView.vue", "validateMandatoryFields")}\nvalidateMandatoryFields()`, form)
console.log("INFO save error:", form.formErrorMessage.value)
check("reported mandatory error reproduced", form.formErrorMessage.value, "Claimed Hours, Explanation fields are mandatory")

const ticket = vm.createContext({
  errorMessage: { value: "" }, validate: () => true,
  form: { subject: "Audit", description: "Synthetic upload failure" },
  newTicket: { submit: async () => ({ name: "AUDIT-TICKET" }) },
  files: { value: [{ name: "synthetic.txt" }] }, uploading: { value: false },
  FileAttachment: class { async upload() { throw new Error("Synthetic upload failure") } },
  myTickets: { reload: () => {} }, router: { replace: () => { ticket.navigated = true } },
  console, __: translate, navigated: false,
})
await vm.runInContext(`${declaration("frontend/src/views/helpdesk/TicketNew.vue", "submit")}\nsubmit()`, ticket)
check("failed ticket attachment stays available for retry", ticket.navigated, false)
console.log(`RESULT ${failures} unmet acceptance properties in synthetic probes`)
process.exitCode = failures ? 1 : 0
