#!/usr/bin/env python3
"""Create a draft report directory without publishing it."""
import argparse
import json
import re
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser(description='新建研报草稿；HTML 完成后将 published 改为 true')
parser.add_argument('slug', help='英文小写标识，例如 ubs-us-semiconductor-20261019')
parser.add_argument('--date', required=True, help='原报告日期 YYYY-MM-DD')
parser.add_argument('--title', required=True)
parser.add_argument('--institution', required=True)
args = parser.parse_args()
if not re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*', args.slug):
    parser.error('slug 只允许小写英文、数字及单个短横线分隔')
try:
    report_date = date.fromisoformat(args.date)
except ValueError:
    parser.error('日期格式应为 YYYY-MM-DD')
folder = ROOT / 'reports' / str(report_date.year) / args.slug
if folder.exists():
    parser.error(f'目录已存在，不会覆盖：{folder}')
folder.mkdir(parents=True)
metadata = dict(title=args.title, institution=args.institution, date=args.date, category='行业研究', region='待补充', tags=[], summary='待补充', published=False, original='')
(folder / 'meta.json').write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print(f'已创建草稿：{folder}\n请补充 meta.json，生成 index.html 后将 published 改为 true。')
