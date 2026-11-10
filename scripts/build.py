#!/usr/bin/env python3
"""Build the public research library with Python's standard library."""
import argparse
import json
import re
import shutil
import tempfile
import zipfile
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ALLOWED_ASSETS = {'.css', '.js', '.png', '.jpg', '.jpeg', '.webp', '.gif', '.svg', '.ico', '.woff', '.woff2', '.ttf', '.avif'}


def load_reports():
    reports = []
    for path in sorted((ROOT / 'reports').glob('*/*/meta.json')):
        data = json.loads(path.read_text(encoding='utf-8'))
        if not isinstance(data, dict) or type(data.get('published')) is not bool:
            raise ValueError(f'{path}: published 必须为 true 或 false')
        if not data['published']:
            continue
        for key in ('title', 'institution', 'date', 'category', 'region', 'summary'):
            if not isinstance(data.get(key), str) or not data[key].strip():
                raise ValueError(f'{path}: 缺少有效字段 {key}')
        date.fromisoformat(data['date'])
        if not re.fullmatch(r'\d{4}', path.parent.parent.name) or not re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*', path.parent.name):
            raise ValueError(f'{path}: 目录应为 reports/YYYY/英文小写短横线标识/')
        if not isinstance(data.get('tags'), list) or not all(isinstance(t, str) and t.strip() for t in data['tags']):
            raise ValueError(f'{path}: tags 必须为非空字符串组成的数组')
        if not (path.parent / 'index.html').is_file():
            raise ValueError(f'{path}: 缺少 index.html')
        public = {key: data[key] for key in ('title', 'institution', 'date', 'category', 'region', 'summary', 'tags')}
        public['id'] = f'{path.parent.parent.name}/{path.parent.name}'
        public['url'] = f'reports/{public["id"]}/index.html'
        reports.append((public, path.parent))
    return sorted(reports, key=lambda item: item[0]['date'], reverse=True)


def build(package=False):
    reports = load_reports()
    with tempfile.TemporaryDirectory(prefix='.build-', dir=ROOT) as temporary:
        output = Path(temporary) / 'dist'
        shutil.copytree(ROOT / 'site', output)
        for report, folder in reports:
            target = output / 'reports' / report['id']
            target.mkdir(parents=True)
            if (folder / 'index.html').is_symlink():
                raise ValueError(f'{folder}: 不支持符号链接')
            shutil.copyfile(folder / 'index.html', target / 'index.html')
            assets = folder / 'assets'
            if assets.exists():
                if assets.is_symlink():
                    raise ValueError(f'{assets}: 不支持符号链接')
                for source in assets.rglob('*'):
                    if source.is_symlink():
                        raise ValueError(f'{source}: 不支持符号链接')
                    if source.is_dir():
                        continue
                    if source.suffix.lower() not in ALLOWED_ASSETS:
                        raise ValueError(f'{source}: 非公开素材类型，请移至 originals/')
                    dest = target / 'assets' / source.relative_to(assets)
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copyfile(source, dest)
        (output / 'reports.json').write_text(
            json.dumps([report for report, _ in reports], ensure_ascii=False, indent=2) + '\n',
            encoding='utf-8',
        )
        dist = ROOT / 'dist'
        if dist.exists():
            shutil.rmtree(dist)
        shutil.move(str(output), str(dist))
    if package:
        with zipfile.ZipFile(ROOT / 'release.zip', 'w', zipfile.ZIP_DEFLATED) as archive:
            for path in sorted(dist.rglob('*')):
                if path.is_file():
                    archive.write(path, path.relative_to(dist).as_posix())
    print(f'已生成 {len(reports)} 篇研报 → {dist}')
    if package:
        print(f'上传包 → {ROOT / "release.zip"}（解压后即为网站根目录）')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--zip', action='store_true', help='同时生成 release.zip 上传包')
    args = parser.parse_args()
    try:
        build(args.zip)
    except (ValueError, OSError) as error:
        parser.exit(1, f'构建失败：{error}\n')
