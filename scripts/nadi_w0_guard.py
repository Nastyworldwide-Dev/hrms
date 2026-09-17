"""Process-local communication isolation for the authorised fresh.local W0 run.

Import and install in BOTH fixture and dedicated HTTP processes before writes.
Never load this module through application hooks. Background work is intercepted,
so its results must be verified separately; it is not part of journey evidence.
"""
import logging
import sys

logger = logging.getLogger(__name__)
COUNTS = {"email": 0, "enqueue": 0, "blocked_socket": 0}


def check_connection(address):
    """Permit only this bench's local DB/cache transports, not local relays."""
    logger.debug("[nadi-w0] checking transport boundary")
    if address in ("/run/mysqld/mysqld.sock", "/var/run/mysqld/mysqld.sock"):
        return
    if isinstance(address, tuple) and address[:2] in (
        ("127.0.0.1", 3306), ("127.0.0.1", 13000), ("127.0.0.1", 11000),
    ):
        return
    raise PermissionError("W0 external or unapproved local transport denied")


def audit(event, args):
    if event in ("subprocess.Popen", "os.system", "os.posix_spawn", "os.exec", "socket.sendmsg"):
        raise PermissionError("W0 process or datagram transport denied")
    if event == "socket.sendto":
        check_connection(args[-1])
    if event == "socket.connect":
        logger.debug("[nadi-w0] checking socket connection")
        try:
            check_connection(args[1])
        except PermissionError:
            COUNTS["blocked_socket"] += 1
            raise


def capture_email(*args, **kwargs):
    COUNTS["email"] += 1
    logger.info("[nadi-w0] intercepted email; recipients not logged")


def capture_job(*args, **kwargs):
    COUNTS["enqueue"] += 1
    logger.info("[nadi-w0] intercepted background job; payload not logged")


def install():
    """Install once in a disposable process, before site/controller imports."""
    logger.info("[nadi-w0] installing process communication guard")
    sys.addaudithook(audit)
    from rq import Queue

    import frappe
    import frappe.utils.background_jobs as jobs

    # Patch the shared queue boundary too: pre-bound enqueue aliases cannot
    # put a task into a queue consumed by an unguarded existing worker.
    frappe.sendmail = capture_email
    frappe.enqueue = capture_job
    jobs.enqueue = capture_job
    Queue.enqueue_call = capture_job
    Queue.enqueue_many = capture_job
    Queue.enqueue_job = capture_job
