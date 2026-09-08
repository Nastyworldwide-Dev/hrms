// Read-only synthetic replay of the shipped Desk approval helper.
import fs from 'node:fs';
import vm from 'node:vm';
import assert from 'node:assert/strict';
import test from 'node:test';

const code = fs.readFileSync('hrms/public/js/utils/request_approval.js', 'utf8');

test('a delayed can_decide response must preserve Save after an HR edit', () => {
  const hrms = { approval: {} };
  let pending;
  let dirty = false;
  let primary = 'Submit';
  const frappe = {
    provide() {},
    ui: { form: { on() {} } },
    call(args) { pending = args.callback; },
  };
  vm.runInNewContext(code, { hrms, frappe, __: text => text });
  const frm = {
    doctype: 'OT Request', doc: { name: 'OT-SYNTHETIC', docstatus: 0 },
    is_new: () => false, is_dirty: () => dirty,
    page: {
      clear_primary_action() { primary = null; },
      set_primary_action(label) { primary = label; },
    },
    add_custom_button() {},
  };
  hrms.approval.add_buttons(frm);
  // Frappe toolbar's dirty handler restores Save while the request is in flight.
  dirty = true;
  primary = 'Save';
  pending({ message: true });
  assert.equal(primary, 'Save', 'Late response replaces Save with Approve for unsaved values');
});
