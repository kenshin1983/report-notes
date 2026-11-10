"""Exercise the remote deployment helper against a temporary local site only."""
import base64
import importlib.util
import json
from pathlib import Path
import stat
import subprocess
import sys
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / 'skills/research-report-publish/scripts/deploy.py'
spec = importlib.util.spec_from_file_location('deploy', SCRIPT)
deploy = importlib.util.module_from_spec(spec)
spec.loader.exec_module(deploy)


class DeploymentTest(unittest.TestCase):
    def test_transaction_and_upload_boundaries(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            site = root / 'live'
            site.mkdir()
            (site / 'assets').mkdir()
            (site / 'index.html').write_text('UNCHANGED')
            (site / 'assets/app.js').write_text('UNCHANGED')
            (site / 'reports.json').write_text('[]\n')
            project = root / 'project'
            dist = project / 'dist'
            dist.mkdir(parents=True)
            row = dict(id='2026/new-report', url='reports/2026/new-report/index.html', title='报告', date='2026-10-28', institution='机构', category='行业', region='全球', summary='摘要', tags=['主题'])
            (dist / 'reports.json').write_text(json.dumps([row], ensure_ascii=False, indent=2) + '\n')
            report = dist / 'reports/2026/new-report'
            (report / 'assets').mkdir(parents=True)
            (report / 'index.html').write_text('<html>new</html>')
            (report / 'assets/a.css').write_text('body{}')
            config = {'remote_root': str(site)}
            token = base64.b64encode(json.dumps(config).encode()).decode()

            def remote(mode, payload=None):
                return subprocess.run([sys.executable, '-c', 'import os;os.umask(0o077)\n' + deploy.REMOTE, token, mode], input=payload, capture_output=True)

            result = remote('inspect')
            self.assertEqual(result.returncode, 0, result.stderr)
            snapshot = json.loads(result.stdout)
            manifest, payload = deploy.make_package(project, config, snapshot)
            self.assertEqual(set(manifest['files']), {'reports.json', 'reports/2026/new-report/index.html', 'reports/2026/new-report/assets/a.css'})
            # Resume a prior interrupted upload with restrictive permissions.
            dest = site / 'reports/2026/new-report'
            (dest / 'assets').mkdir(parents=True)
            (dest / 'index.html').write_bytes((report / 'index.html').read_bytes())
            (dest / 'assets/a.css').write_bytes((report / 'assets/a.css').read_bytes())
            dest.chmod(0o700)
            result = remote('apply', payload)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads((site / 'reports.json').read_text()), [row])
            for p in [dest, dest / 'assets']:
                self.assertEqual(stat.S_IMODE(p.stat().st_mode), 0o755)
            for p in [dest / 'index.html', dest / 'assets/a.css', site / 'reports.json']:
                self.assertEqual(stat.S_IMODE(p.stat().st_mode), 0o644)
            self.assertEqual((site / 'index.html').read_text(), 'UNCHANGED')
            self.assertEqual((site / 'assets/app.js').read_text(), 'UNCHANGED')
            # A stale plan cannot replace the newer catalog.
            result = remote('apply', payload)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn(b'Remote JSON changed', result.stderr)
            synced = json.loads(remote('inspect').stdout)
            plan, _ = deploy.make_package(project, config, synced)
            self.assertFalse(plan['files'])
            synced['reports'].append(dict(row, id='2026/remote-only'))
            with self.assertRaises(ValueError):
                deploy.make_package(project, config, synced)
            (report / 'meta.json').write_text('private')
            with self.assertRaises(ValueError):
                deploy.make_package(project, config, snapshot)
            (report / 'meta.json').unlink()
            # Reject non-identical existing report directories before JSON commit.
            (site / 'reports.json').write_text('[]\n')
            snapshot = json.loads(remote('inspect').stdout)
            manifest, payload = deploy.make_package(project, config, snapshot)
            (dest / 'index.html').write_text('different')
            result = remote('apply', payload)
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual((site / 'reports.json').read_text(), '[]\n')
            self.assertEqual((dest / 'index.html').read_text(), 'different')


if __name__ == '__main__':
    unittest.main()
