"""Read-only production-function probes. Exit 1 = acceptance violations found.

No site connection or document writes. Real functions run against named synthetic
DB seams; AST extraction runs unchanged method bodies, not full transactions.
"""
import ast
import logging
import sys
from datetime import date, datetime, time, timedelta
from pathlib import Path
from types import SimpleNamespace as NS
from unittest.mock import MagicMock, patch

ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT), str(ROOT / 'hrms/tests')]
import _frappe_stub

_frappe_stub.install()
import frappe

from hrms.utils import ot_calculation as ot
from hrms.utils.filing_window import earliest_filable_date, is_within_ot_filing_window

logging.disable(logging.CRITICAL)
failures = []

def check(label, actual, expected):
    passed = actual == expected
    print(f"{'PASS' if passed else 'FAIL'} {label}: actual={actual!r}; expected={expected!r}")
    if not passed:
        failures.append(label)

def method(path, name, env):
    path = Path(path)
    if not path.is_absolute():
        path = ROOT / path
    node = next(n for n in ast.walk(ast.parse(path.read_text())) if isinstance(n, ast.FunctionDef) and n.name == name)
    node.decorator_list = []
    exec(compile(ast.Module(body=[node], type_ignores=[]), str(path), 'exec'), env)
    return env[name]

config = dict(start_time='09:00:00', end_time='18:00:00', min_minutes=60,
              days_per_month=26, hours_per_day=8, daily_cap=0, monthly_cap=4,
              bands={'normal': [(0, 24, 1.5)]})
logs = [dict(name=f'AUDIT-{i}', time=f'2026-09-03 {clock}:00', log_type=kind, shift='SHIFT',
             shift_actual_start='2026-09-03 08:00:00', shift_actual_end='2026-09-03 22:00:00',
             remote_approval_status='Pending')
        for i, (clock, kind) in enumerate([('09:00', 'IN'), ('21:00', 'OUT')])]
with patch.object(ot, '_get_shift_ot_config', return_value=config), patch.object(ot, 'get_time', side_effect=time.fromisoformat), patch.object(ot, '_classify_day', return_value='normal'), patch.object(frappe, 'get_all', return_value=logs):
    check('Pending IN/OUT excluded from verified OT', ot.get_day_ot_breakdown('AUDIT', '2026-09-03')['ot_hours'], 0)

# Both payroll subranges refer to the same calendar month and 4-hour monthly cap.
hours = {date(2026, 9, 3): 3.0, date(2026, 9, 18): 3.0}
shifts = {day: 'SHIFT' for day in hours}
with patch.object(ot, '_get_shift_ot_config', return_value=config), patch.object(ot, '_classify_day', return_value='normal'), patch.object(ot, '_per_day_ot_hours', return_value=(hours, shifts)):
    whole = sum(row['ot_hours'] for row in ot._iter_day_ot('AUDIT', date(2026, 9, 1), date(2026, 9, 30), 0, 'normal'))
    separate = sum(row['ot_hours'] for day in hours for row in ot._iter_day_ot('AUDIT', day, day, 0, 'normal'))
    check('Calendar-month cap independent of query range', (whole, separate), (4, 4))

# Claim filing policy runs for every validate, but returns before examining edited dates.
filing = method('hrms/hr/doctype/ot_request/ot_request.py', 'validate_filing_window', {
    'getdate': lambda value=None: date.fromisoformat(str(value)) if value else date(2026, 9, 8),
    'is_within_ot_filing_window': is_within_ot_filing_window, 'earliest_filable_date': earliest_filable_date,
    'frappe': frappe, '_': lambda value: value, 'logger': logging.getLogger('audit')})
for label, is_new, amended_from in [('existing draft', False, None), ('amended draft with changed work date', True, 'CANCELLED-ORIGINAL')]:
    doc = NS(is_new=lambda: is_new, amended_from=amended_from, ot_date='2026-01-01', employee='AUDIT')
    try:
        filing(doc)
        outcome = 'allowed'
    except frappe.ValidationError:
        outcome = 'refused'
    check(f'Old date rejected on {label}', outcome, 'refused')

# Execute the unchanged propagation hook with an in-memory checkin dictionary.
propagate = method('hrms/overrides/remote_checkin_request_hooks.py', 'propagate_approval_decision', {
    'frappe': frappe, 'cint': lambda value: int(value or 0), 'now_datetime': lambda: datetime(2026, 9, 8),
    '_notify_employee': lambda *args: None, 'reprocess_late_checkout_attendance': lambda *args: None,
    'logger': logging.getLogger('audit')})
state = {'requires_remote_approval': 0, 'remote_approval_status': 'Rejected', 'skip_auto_attendance': 1}
def set_value(doctype, name, values):
    state.update(values)
doc = NS(name='AUDIT-RCR', status='Approved', checkin='AUDIT-OUT', approved_at=datetime(2026, 9, 7),
         get=lambda field: 0, get_doc_before_save=lambda: NS(status='Rejected'))
with patch.object(frappe.db, 'set_value', side_effect=set_value):
    propagate(doc)
check('Desk Rejected to Approved restores processing', state['skip_auto_attendance'], 0)
doc.status = 'Pending'
doc.get_doc_before_save = lambda: NS(status='Approved')
with patch.object(frappe.db, 'set_value', side_effect=set_value):
    propagate(doc)
check('Desk reset Pending matches checkin approval state', state['remote_approval_status'], 'Pending')

# Simulate an automation-owned attendance covering both sessions; cancel unlinks
# all four rows, then the real hook selects only the second session for rebuild.
reprocess = method('hrms/overrides/remote_checkin_request_hooks.py', 'reprocess_late_checkout_attendance', {
    'frappe': frappe, 'cint': lambda value: int(value or 0), 'get_datetime': ot.get_datetime,
    'logger': logging.getLogger('audit')})
all_logs = [frappe._dict(name=f'AUDIT-{i}', employee='AUDIT', time=datetime(2026, 9, 3, hour), log_type=kind,
                        shift='SHIFT', skip_auto_attendance=0, attendance=None, synced_from_instance=None)
            for i, (hour, kind) in enumerate([(9, 'IN'), (12, 'OUT'), (13, 'IN'), (21, 'OUT')])]
in_row = frappe._dict(name='AUDIT-2', employee='AUDIT', time=all_logs[2].time, shift='SHIFT',
                       shift_start=datetime(2026, 9, 3, 9), attendance='AUDIT-ATT')
attendance = NS(auto_attendance=1, docstatus=1, flags=NS(), name='AUDIT-ATT', status='Half Day', cancel=MagicMock())
shift = NS(mark_attendance_for_shift_logs=MagicMock(return_value=NS(name='AUDIT-REBUILT')))
def get_value(doctype, name, *args, **kwargs):
    return all_logs[-1] if name == 'AUDIT-3' else in_row

def get_all(doctype, *, filters, **kwargs):
    low, high = filters['time'][1]
    return [row for row in all_logs if low <= row.time <= high]
with patch.object(frappe.db, 'get_value', side_effect=get_value), patch.object(frappe, 'get_doc', side_effect=lambda dt, name: attendance if dt == 'Attendance' else shift), patch.object(frappe, 'get_all', side_effect=get_all):
    reprocess('AUDIT-3')
rebuilt_names = [row.name for row in shift.mark_attendance_for_shift_logs.call_args.args[2]]
check('Late OUT rebuild retains earlier same-shift sessions', rebuilt_names, [row.name for row in all_logs])

# Framework method bodies establish gate invocation more faithfully than forcing
# has_value_changed=True. Infrastructure methods are still simulated, no insert.
framework = '/home/nabil/verify-bench/apps/frappe/frappe/model/document.py'
gate = method('hrms/hr/doctype/remote_checkin_request/remote_checkin_request.py', 'before_save', {
    'frappe': frappe, '_': lambda value: value, 'HR_MANAGER_ROLE': 'HR Manager', 'logger': logging.getLogger('audit')})
changed = method(framework, 'has_value_changed', {})
run_before = method(framework, 'run_before_save_methods', {})
request = NS(status='Approved', name='AUDIT-DERIVED', approver='approver@example.invalid', _action='save',
             flags=NS(ignore_validate=False, ignore_permissions=True), reset_seen=lambda: None,
             set_title_field=lambda: None, get_doc_before_save=lambda: None)
request.has_value_changed = lambda field: changed(request, field)
request.run_method = lambda name: gate(request) if name == 'before_save' else None
with patch.object(frappe.session, 'user', 'employee@example.invalid'), patch.object(frappe, 'get_roles', return_value=['Employee']):
    try:
        run_before(request)
        outcome = 'allowed'
    except frappe.ValidationError:
        outcome = 'refused'
check('Framework save hooks allow inherited approval insert', outcome, 'allowed')
# A fixed lunch and an unrelated punch gap must each reduce worked duration.
from hrms.utils import break_calculation as breaks

deduct = method('hrms/hr/doctype/shift_type/shift_type.py', '_deduct_unpaid_breaks', {
    'get_datetime': ot.get_datetime})
break_rows = [dict(day_of_week='Thursday', period='Normal only', break_type='Fixed',
                   start_time='12:00:00', end_time='13:00:00')]
start, end = datetime(2026, 9, 3, 9), datetime(2026, 9, 3, 19)
shift = NS(name='SHIFT', breaks=break_rows)
with patch.object(breaks, 'get_shift_break_minutes', side_effect=lambda name, low, high, **kw: breaks.get_break_minutes(low, high, break_rows)):
    # 09:00-10:00 + 11:00-19:00 = 9 actual punch hours; lunch remains inside work.
    actual = deduct(shift, 9, start, end, company='AUDIT')
check('Unrelated 10:00-11:00 gap does not erase fixed 12:00-13:00 break', actual, 8)

print(f'RESULT {len(failures)} acceptance violations. Synthetic production functions; no live transactions.')
sys.exit(bool(failures))
