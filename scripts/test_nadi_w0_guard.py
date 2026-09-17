"""Run with python -m unittest discover -s scripts -p test_nadi_w0_guard.py."""
import unittest

from nadi_w0_guard import check_connection


class GuardTests(unittest.TestCase):
    def test_local_database_and_cache_allowed(self):
        for address in [('127.0.0.1', 3306), ('127.0.0.1', 13000), '/run/mysqld/mysqld.sock']:
            check_connection(address)

    def test_external_and_local_relays_denied(self):
        for address in [('8.8.8.8', 443), ('example.com', 443), ('127.0.0.1', 25),
                        ('127.0.0.1', 8080), '/tmp/unknown.sock']:
            with self.assertRaises(PermissionError):
                check_connection(address)


if __name__ == '__main__':
    unittest.main()

class InstalledGuardTests(unittest.TestCase):
    def test_installed_guard_covers_transport_and_queue_aliases(self):
        import subprocess
        from pathlib import Path
        interpreter = Path.home() / 'verify-bench/env/bin/python'
        code = '''
import socket, subprocess, os, sys
sys.path.insert(0, 'scripts')
import frappe
from frappe.utils.background_jobs import enqueue as previously_bound
from rq import Queue
from nadi_w0_guard import install, COUNTS
install()
for action in [
    lambda: socket.socket().connect(('203.0.113.1', 443)),
    lambda: socket.socket(socket.AF_INET, socket.SOCK_DGRAM).sendto(b'probe', ('127.0.0.1', 9)),
    lambda: subprocess.run(['true']),
    lambda: os.system('true'),
]:
    try:
        action()
    except PermissionError:
        pass
    else:
        raise AssertionError('isolation failed')
frappe.sendmail(recipients=['w0@example.invalid'])
# The pre-bound alias resolves its original globals at call time. Patch the
# queue factory to a genuine Queue; no Redis connection should be needed.
import frappe.utils.background_jobs as jobs
jobs.get_queue = lambda *args, **kwargs: Queue(connection=type('LocalQueueRead', (), {'llen': lambda self, key: 0})())
frappe.init(site='fresh.local', sites_path=str(__import__('pathlib').Path.home() / 'verify-bench/sites'))
previously_bound('unused.test.method')
Queue.enqueue_call(None, func='unused')
Queue.enqueue_many(None, [])
Queue.enqueue_job(None, None)
assert COUNTS['email'] == 1
assert COUNTS['enqueue'] == 4, COUNTS
'''
        result = subprocess.run([str(interpreter), '-c', code], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
