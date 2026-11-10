#!/usr/bin/env python3
"""Plan or apply an incremental report deployment. No homepage/assets upload."""
import argparse
import base64
import hashlib
import io
import json
from pathlib import Path
import re
import shlex
import subprocess
import sys
import urllib.request
import zipfile

DEFAULT_PROJECT = Path.cwd()
ID = re.compile(r'\d{4}/[a-z0-9]+(?:-[a-z0-9]+)*')
REMOTE = r'''
import base64,fcntl,hashlib,io,json,os,pathlib,shutil,stat,sys,tempfile,zipfile
cfg=json.loads(base64.b64decode(sys.argv[1])); mode=sys.argv[2]
root=pathlib.Path(cfg['remote_root'])
def digest(b): return hashlib.sha256(b).hexdigest()
def ensure_path(p):
    for part in [p,*p.parents]:
        if part.is_symlink(): raise RuntimeError('Refuse symlink: '+str(part))
def current():
    p=root/'reports.json';ensure_path(p)
    raw=p.read_bytes()
    return raw,json.loads(raw)
ensure_path(root)
if not root.is_dir() or not (root/'index.html').is_file() or not (root/'assets/app.js').is_file():
    raise RuntimeError('Site is not initialized; deploy the initial site separately')
if mode=='inspect':
    raw,rows=current()
    print(json.dumps({'sha256':digest(raw),'reports':rows,'writable':os.access(root,os.W_OK)}))
elif mode=='apply':
    archive=zipfile.ZipFile(io.BytesIO(sys.stdin.buffer.read()))
    manifest=json.loads(archive.read('_manifest.json'))
    new=manifest['new_ids']; wanted=manifest['files']
    names=archive.namelist()
    if len(names)!=len(set(names)) or set(names)!=set(wanted)|{'_manifest.json'}:
        raise RuntimeError('Unexpected package members')
    for name,sha in wanted.items():
        p=pathlib.PurePosixPath(name)
        if p.is_absolute() or '..' in p.parts or str(p)!=name: raise RuntimeError('Unsafe member')
        if name!='reports.json' and not any(name.startswith('reports/'+i+'/') for i in new):
            raise RuntimeError('Outside upload scope')
        if digest(archive.read(name))!=sha: raise RuntimeError('Invalid package hash')
    for i in new:
        import re
        if not re.fullmatch(r'\d{4}/[a-z0-9]+(?:-[a-z0-9]+)*',i): raise RuntimeError('Invalid report ID')
    lockpath=pathlib.Path(tempfile.gettempdir())/('research-deploy-'+digest(str(root).encode())[:20]+'.lock')
    lockfd=os.open(str(lockpath),os.O_CREAT|os.O_RDWR|getattr(os,'O_NOFOLLOW',0),0o600)
    with os.fdopen(lockfd,'a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        old,rows=current()
        if digest(old)!=manifest['expected_remote_sha256']: raise RuntimeError('Remote JSON changed; re-plan first')
        newrows=json.loads(archive.read('reports.json'))
        oldmap={r['id']:r for r in rows}; newmap={r['id']:r for r in newrows}
        if len(newmap)!=len(newrows) or set(newmap)!=set(oldmap)|set(new): raise RuntimeError('Unexpected catalog IDs')
        if any(newmap.get(k)!=v for k,v in oldmap.items()): raise RuntimeError('Existing metadata changed')
        for report_id in new:
            dest=root/'reports'/report_id;ensure_path(dest)
            if dest.exists():
                actual={str(p.relative_to(root)):digest(p.read_bytes()) for p in dest.rglob('*') if p.is_file() and not p.is_symlink()}
                expected={n:s for n,s in wanted.items() if n.startswith('reports/'+report_id+'/')}
                if any(p.is_symlink() for p in dest.rglob('*')) or actual!=expected:
                    raise RuntimeError('Existing directory differs: '+report_id)
        # Stage outside the served tree. Set public modes explicitly; do not rely on umask.
        with tempfile.TemporaryDirectory(prefix='.report-stage-',dir=root.parent) as tmp:
            stage=pathlib.Path(tmp)
            for name in wanted:
                p=stage/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(archive.read(name));p.chmod(0o644)
            for p in stage.rglob('*'):
                if p.is_dir():p.chmod(0o755)
            for report_id in new:
                dest=root/'reports'/report_id
                if not dest.exists():
                    dest.parent.mkdir(parents=True,exist_ok=True)
                    # Only report/year directories in this site's public tree.
                    ensure_path(dest.parent);(root/'reports').chmod(0o755);dest.parent.chmod(0o755)
                    os.rename(stage/'reports'/report_id,dest)
                for p in [dest,*dest.rglob('*')]:p.chmod(0o755 if p.is_dir() else 0o644)
            # The catalog is the final commit point; reports are already readable.
            os.replace(stage/'reports.json',root/'reports.json')
        for name,sha in wanted.items():
            p=root/name
            if digest(p.read_bytes())!=sha:raise RuntimeError('Post-upload hash mismatch: '+name)
            expected=0o644
            if stat.S_IMODE(p.stat().st_mode)!=expected:raise RuntimeError('Incorrect file mode: '+name)
        print(json.dumps({'status':'published','new_ids':new,'files':list(wanted),'catalog_sha256':digest((root/'reports.json').read_bytes()),'permissions':'directories 755; files 644'}))
else:raise RuntimeError('Unknown mode')
'''


def sha(data):
    return hashlib.sha256(data).hexdigest()


def ssh(config, mode, payload=None):
    token = base64.b64encode(json.dumps(config).encode()).decode()
    command = shlex.join(['python3', '-c', REMOTE, token, mode])
    args = ['ssh', '-o', 'BatchMode=yes', '-o', 'StrictHostKeyChecking=yes', '-o', 'IdentitiesOnly=yes', '-o', 'ConnectTimeout=12', '-p', str(config['port']), '-i', str(Path(config['identity_file']).expanduser()), config['user'] + '@' + config['host'], command]
    result = subprocess.run(args, input=payload, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=180)
    if result.returncode:
        raise RuntimeError(result.stderr.decode(errors='replace').strip())
    return json.loads(result.stdout)


def make_package(project, config, remote):
    dist = project / 'dist'
    raw = (dist / 'reports.json').read_bytes()
    rows = json.loads(raw)
    local = {r['id']: r for r in rows}
    old = {r['id']: r for r in remote['reports']}
    if len(local) != len(rows) or len(old) != len(remote['reports']):
        raise ValueError('Duplicate report IDs')
    if any(not ID.fullmatch(k) for k in local):
        raise ValueError('Invalid report ID')
    missing = set(old) - set(local)
    changed = [k for k in old if k in local and old[k] != local[k]]
    if missing or changed:
        raise ValueError(f'Refuse to remove or replace existing records: missing={sorted(missing)}, changed={changed}. Reconcile first.')
    new = [r['id'] for r in rows if r['id'] not in old]
    files = {}
    allowed = {'.html', '.css', '.js', '.png', '.jpg', '.jpeg', '.webp', '.gif', '.svg', '.ico', '.woff', '.woff2', '.ttf', '.avif'}
    for report_id in new:
        folder = dist / 'reports' / report_id
        if not (folder / 'index.html').is_file():
            raise ValueError('Missing HTML: ' + report_id)
        for p in [folder, *folder.rglob('*')]:
            if p.is_symlink():raise ValueError('Symlink in output: ' + str(p))
            if p.is_file():
                rel = p.relative_to(folder)
                if (rel.as_posix() != 'index.html' and rel.parts[0] != 'assets') or p.suffix.lower() not in allowed:
                    raise ValueError('Unexpected public file: ' + str(p))
                files[p.relative_to(dist).as_posix()] = p.read_bytes()
    if new or raw != json.dumps(remote['reports'], ensure_ascii=False, indent=2).encode() + b'\n':
        files['reports.json'] = raw
    # No catalog-only writes for equivalent records (e.g. indentation/order differences).
    if not new:
        files = {}
    manifest = {'new_ids': new, 'expected_remote_sha256': remote['sha256'], 'files': {name: sha(content) for name, content in files.items()}}
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as archive:
        for name, content in files.items():archive.writestr(name, content)
        archive.writestr('_manifest.json', json.dumps(manifest))
    return manifest, buf.getvalue()


def verify_http(config, manifest):
    base = config.get('base_url', '').rstrip('/')
    if not base:return {'http': 'not configured'}
    paths = ['reports.json', *[f'reports/{i}/index.html' for i in manifest['new_ids']]]
    for path in paths:
        request = urllib.request.Request(base + '/' + path, headers={'Cache-Control': 'no-cache'})
        with urllib.request.urlopen(request, timeout=20) as response:
            if sha(response.read()) != manifest['files'][path]:raise RuntimeError('HTTP content mismatch: ' + path)
    return {'http': 'verified', 'urls': [base + '/' + p for p in paths]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project', type=Path, default=DEFAULT_PROJECT)
    parser.add_argument('--config', type=Path)
    parser.add_argument('--report', action='append', default=[], help='Limit authorized new report IDs; refuse other pending reports')
    parser.add_argument('--apply', action='store_true', help='Publish the planned new reports; otherwise inspect only')
    args = parser.parse_args()
    project = args.project.resolve()
    config = json.loads((args.config or project / 'deploy.local.json').read_text())
    required = ('host', 'user', 'identity_file', 'remote_root')
    if not all(isinstance(config.get(k), str) and config[k] for k in required):raise ValueError('Incomplete deployment configuration')
    if not re.fullmatch(r'[a-zA-Z0-9.-]+', config['host']) or not re.fullmatch(r'[a-z_][a-z0-9_-]*', config['user']):raise ValueError('Invalid host/user')
    if not config['remote_root'].startswith('/') or config['remote_root']=='/' or '..' in Path(config['remote_root']).parts:raise ValueError('Invalid remote root')
    config.setdefault('port', 22)
    remote = ssh(config, 'inspect')
    if not remote['writable']:raise ValueError('Remote directory is not writable')
    manifest, payload = make_package(project, config, remote)
    if args.apply and set(manifest['new_ids']) != set(args.report):
        raise ValueError('Apply requires --report for every new ID in the plan; unrelated pending reports must be reconciled before publication')
    print(json.dumps({'mode': 'apply' if args.apply else 'plan', 'host': config['host'], 'remote_root': config['remote_root'], 'new_ids': manifest['new_ids'], 'files': list(manifest['files']), 'permissions': 'directories 755; files 644'}, ensure_ascii=False, indent=2), flush=True)
    if args.apply and manifest['files']:
        result = ssh(config, 'apply', payload)
        print(json.dumps(result, ensure_ascii=False))
        print(json.dumps(verify_http(config, manifest), ensure_ascii=False))
    elif args.apply:print('Already synchronized; no uploads.')


if __name__ == '__main__':
    try:main()
    except (ValueError, OSError, RuntimeError, subprocess.SubprocessError) as error:
        sys.exit('Deployment stopped: ' + str(error))
