"""Offline regression tests for this worktree; no production credentials or DB.

Detailed logs and temporary databases remain in ignored .validation_runtime.
Only a credential-free aggregate report is written into docs.
"""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
BOOTSTRAP = r"""
import ipaddress, json, pathlib, socket, sys, unittest
root = pathlib.Path(sys.argv[1]).resolve()
# Some embedded interpreters contain an older workspace in ._pth. Remove any
# other source checkout before importing the application under test.
sys.path[:] = [entry for entry in sys.path if not any(
    (pathlib.Path(entry) / package).is_dir() for package in ('backend', 'collection_engine', 'crawler_engine'))]
sys.path.insert(0, str(root))
import backend, collection_engine, crawler_engine
origins = {}
for module in (backend, collection_engine, crawler_engine):
    path = pathlib.Path(module.__file__).resolve()
    assert path.is_relative_to(root), 'Wrong worktree imported'
    origins[module.__name__] = path.relative_to(root).as_posix()
def loopback(host):
    if isinstance(host, bytes): host = host.decode('ascii')
    if host in ('localhost', None, ''): return True
    try: return ipaddress.ip_address(host).is_loopback
    except ValueError: return False
original_connect, original_connect_ex = socket.socket.connect, socket.socket.connect_ex
original_getaddrinfo = socket.getaddrinfo
def connect(sock, address):
    if isinstance(address, tuple) and not loopback(address[0]):
        raise OSError('External networking disabled for publication tests')
    return original_connect(sock, address)
def connect_ex(sock, address):
    if isinstance(address, tuple) and not loopback(address[0]):
        raise OSError('External networking disabled for publication tests')
    return original_connect_ex(sock, address)
def getaddrinfo(host, *args, **kwargs):
    if not loopback(host): raise OSError('External DNS disabled for publication tests')
    return original_getaddrinfo(host, *args, **kwargs)
socket.socket.connect, socket.socket.connect_ex = connect, connect_ex
socket.getaddrinfo = getaddrinfo
suite = unittest.defaultTestLoader.discover(str(root / 'tests'))
result = unittest.TextTestRunner(verbosity=2).run(suite)
payload = {'test_count': result.testsRun, 'failures': len(result.failures),
           'errors': len(result.errors), 'skipped': len(result.skipped),
           'unexpected_successes': len(result.unexpectedSuccesses),
           'passed': result.testsRun - len(result.failures) - len(result.errors) - len(result.skipped) - len(result.unexpectedSuccesses),
           'successful': result.wasSuccessful(), 'module_origins': origins,
           'external_network_disabled': True}
pathlib.Path(sys.argv[2]).write_text(json.dumps(payload), encoding='utf-8')
raise SystemExit(0 if result.wasSuccessful() else 1)
"""


def main():
    runtime = ROOT / '.validation_runtime'
    runtime.mkdir(exist_ok=True)
    environment = os.environ.copy()
    site_prefixes = ('EBAY_', 'ELEVENST_', 'YES24_', 'YAHOO_', 'RAKUTEN_', 'BESTBUY_', 'ETSY_',
                     'NAVER_', 'KAKAO_', 'YOUTUBE_', 'META_', 'APPROVED_HTML_', 'AWIN_', 'CJ_', 'IMPACT_')
    for key in list(environment):
        if key.startswith(site_prefixes) or key in ('SHOPPING_SOURCES_CONFIG', 'PYTHONPATH', 'PYTHONHOME') or any(
                word in key.upper() for word in ('SECRET', 'TOKEN', 'PASSWORD', 'API_KEY', 'COOKIE', 'CLIENT_ID', 'ACCESS_KEY')):
            environment.pop(key, None)
    environment.update(PYTHON_DOTENV_DISABLED='1', PYTHONDONTWRITEBYTECODE='1', PYTHONIOENCODING='utf-8',
                       TEMP=str(runtime), TMP=str(runtime), TMPDIR=str(runtime))
    public_db = ROOT / 'backend/data/products.db'
    before = hashlib.sha256(public_db.read_bytes()).hexdigest() if public_db.exists() else None
    with tempfile.TemporaryDirectory(prefix='isolated-', dir=runtime) as directory:
        result_path = Path(directory) / 'result.json'
        environment['SHOPPING_DB_PATH'] = str(Path(directory) / 'isolated.db')
        run = subprocess.run([sys.executable, '-B', '-c', BOOTSTRAP, str(ROOT), str(result_path)],
                             cwd=ROOT, env=environment, capture_output=True, encoding='utf-8', errors='replace')
        result = json.loads(result_path.read_text(encoding='utf-8')) if result_path.exists() else {
            'successful': False, 'test_count': None, 'error_category': 'test_bootstrap_failed'}
        log = run.stdout + run.stderr
    after = hashlib.sha256(public_db.read_bytes()).hexdigest() if public_db.exists() else None
    (runtime / 'tests.log').write_text(log, encoding='utf-8')
    result.update(exit_code=run.returncode, production_credentials_removed=True, dotenv_disabled=True,
                  default_db_isolated=True, default_db_hash_unchanged=before == after,
                  detailed_log_publication_excluded=True, tests_are_not_live_evidence=True)
    (ROOT / 'docs/publication_test_results.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(result))
    return run.returncode


if __name__ == '__main__':
    raise SystemExit(main())
