// Installed native Desk ControlFloat + native number formatter; no copied
// decimal parser. The ControlData base has no DOM in this focused parse probe.
import assert from 'node:assert/strict'
import fs from 'node:fs'
import path from 'node:path'
import vm from 'node:vm'
import { fileURLToPath } from 'node:url'

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../../..')
const native = '/home/nabil/verify-bench/apps/frappe/frappe/public/js/frappe'
const context = {
  frappe: { ui: { form: { ControlData: class {} } }, boot: { sysdefaults: {} } },
  lstrip: (value) => value.replace(/^0+/, ''),
}
context.window = context
vm.createContext(context)
for (const file of ['utils/datatype.js', 'utils/number_format.js', 'form/controls/int.js', 'form/controls/float.js']) {
  vm.runInContext(fs.readFileSync(path.join(native, file), 'utf8').replace('import "./datatype";', ''), context, { filename: file })
}
const metadata = JSON.parse(fs.readFileSync(path.join(root, 'hrms/hr/doctype/ot_request/ot_request.json')))
const field = metadata.fields.find(row => row.fieldname === 'claimed_hours')
const control = new context.frappe.ui.form.ControlFloat()
control.df = field
for (const cap of [0.016666667, 3.233333333]) {
  assert.equal(control.parse(String(cap)), cap)
  assert.equal(control.parse(control.parse(String(cap))), cap)
  const doc = { claimed_hours: control.parse(String(cap)), explanation: 'Synthetic initial note' }
  doc.explanation = 'Synthetic edited note'
  assert.equal(JSON.parse(JSON.stringify(doc)).claimed_hours, cap)
}
// Counterfactual proves why the metadata change matters for Desk editing.
control.df = { ...field, precision: '2' }
assert.equal(control.parse('0.016666667'), 0.02)
assert.equal(control.parse('3.233333333'), 3.23)
console.log('PASS: native Desk parse/reparse and numeric payload retain both exact9dp caps; old2dp metadata demonstrably loses them')
