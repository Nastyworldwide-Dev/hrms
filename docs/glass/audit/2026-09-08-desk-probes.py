"""Read-only synthetic audit probes. Expected to fail until reported defects are fixed."""
import ast
import datetime
import logging
import unittest
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[3]
FRAPPE_REPORT = Path('/home/nabil/verify-bench/apps/frappe/frappe/desk/query_report.py')


def functions(path, names, namespace):
    tree = ast.parse(path.read_text())
    selected = [node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef) and node.name in names]
    for node in selected:
        node.decorator_list = []
    module = ast.Module(body=[ast.ImportFrom(module='__future__', names=[ast.alias(name='annotations')], level=0), *selected], type_ignores=[])
    exec(compile(ast.fix_missing_locations(module), str(path), 'exec'), namespace)
    return namespace


class AttrDict(dict):
    __getattr__ = dict.get


class DeskAudit(unittest.TestCase):
    def test_half_day_attendance_contributes_to_chart(self):
        env = functions(ROOT / 'hrms/hr/report/monthly_attendance_sheet/monthly_attendance_sheet.py', {'get_chart_data'}, {
            '_': lambda text: text,
            'get_columns_for_days': lambda filters: [{'label': '7', 'fieldname': '07-09-2026'}],
            'getdate': lambda text, **kwargs: datetime.datetime.strptime(text, '%d-%m-%Y').date(),
        })
        day = datetime.date(2026, 9, 7)
        for status in ('Half Day/Other Half Present', 'Half Day/Other Half Absent'):
            with self.subTest(status=status):
                result = env['get_chart_data']({'EMP-SYNTHETIC': {'Day': {day: status}}}, {})
                self.assertGreater(sum(row['values'][0] for row in result['data']['datasets']), 0,
                                   'Half Day disappears from all chart datasets')

    def test_row_filter_does_not_leave_unscoped_chart(self):
        columns = [{'fieldname': 'employee', 'fieldtype': 'Link', 'options': 'Employee'}]
        rows = [{'employee': 'EMP-ALLOWED'}, {'employee': 'EMP-HIDDEN'}]
        chart = {'data': {'datasets': [{'name': 'Present', 'values': [2]}]}}
        env = functions(FRAPPE_REPORT, {'generate_report_result'}, {
            'frappe': SimpleNamespace(session=SimpleNamespace(user='hr.synthetic@example.invalid'), cache=SimpleNamespace(hget=lambda *a: None)),
            'get_report_result': lambda *a: (columns, rows, None, chart),
            'ljust_list': lambda items, n: list(items) + [None] * (n-len(items)),
            'get_column_as_dict': lambda col: col,
            'normalize_result': lambda result, columns: result,
            # Faithful seam: framework UP filtering removes an out-of-scope result row.
            'get_filtered_data': lambda *a: rows[:1],
            'cint': lambda value: int(value or 0),
        })
        report = AttrDict(ref_doctype='Attendance', name='Synthetic Report', add_total_row=0)
        result = env['generate_report_result'](report, filters={})
        self.assertEqual(len(result['result']), 1)
        self.assertEqual(result['chart']['data']['datasets'][0]['values'][0], 1,
                         'Report rows are filtered but chart still includes the hidden row')

    def test_report_up_filter_keeps_company_fence_scoped_to_another_doctype(self):
        # App-level allowed_companies deliberately honors this UP regardless of applicable_for.
        # Frappe report postfilter asks build_match_conditions(as_condition=False), which does not.
        env = functions(FRAPPE_REPORT.parents[1] / 'database/query.py', {'build_match_conditions'}, {
            'frappe': SimpleNamespace(permissions=SimpleNamespace(get_user_permissions=lambda user: {
                'Company': [{'doc': 'COMPANY-ALLOWED', 'applicable_for': 'Leave Application'}],
            })),
        })
        engine = SimpleNamespace(ignore_user_permissions=False, user='hr.synthetic@example.invalid',
                                 doctype='Employee', reference_doctype=None,
                                 get_doctype_link_fields=lambda doctype: [AttrDict(fieldname='company', options='Company')])
        match_filters = env['build_match_conditions'](engine, as_condition=False)
        self.assertTrue(match_filters, 'Company fence disappears from report postfilter when UP applicable_for is another doctype')

    def test_releasing_stamp_protects_local_rl_topup_from_repull(self):
        row = {'synced_from_instance': None, 'new_leaves_allocated': 3.0, 'total_leaves_allocated': 3.0}
        db = SimpleNamespace(exists=lambda *a: True, get_value=lambda dt, name, field: row.get(field),
                             set_value=lambda dt, name, fields, **kw: row.update(fields))
        env = functions(ROOT / 'hrms/sync/runner.py', {'plan_cross_instance_write', '_write_row'}, {
            'frappe': SimpleNamespace(db=db),
            '_narrow_to_local_schema': lambda doctype, payload: (payload, {}),
            'CREATE_ONLY_DOCTYPES': (), 'STAMPED_DOCTYPES': ('Leave Allocation',),
            'PROVENANCE_FIELD': 'synced_from_instance', '_log': lambda: logging.getLogger('desk-audit'),
        })
        env['_write_row'].dropped_fields = {}
        env['_write_row']('Leave Allocation', 'ALLOC-SYNTHETIC', {
            'synced_from_instance': 'SOURCE-SYNTHETIC', 'new_leaves_allocated': 2.0, 'total_leaves_allocated': 2.0,
        })
        self.assertEqual(row['total_leaves_allocated'], 3.0,
                         'Source reclaims released allocation and erases its local RL topup')


if __name__ == '__main__':
    unittest.main(verbosity=2)
