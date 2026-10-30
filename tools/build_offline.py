# 오프라인용 파일 목록 offline.json을 만든다: 게임이 쓰는 파일 경로 → git 해시.
# sw.js가 이 목록을 보고 없거나 해시가 바뀐 파일만 받아 둔다. 그림·도트 파일을 더하거나 바꾸면 git add 한 뒤 다시 돌릴 것.
# 쓰는 법: 저장소 맨 위에서 python tools/build_offline.py
import json, subprocess

DIRS = ['bt', 'fx', 'ic', 'it', 'map', 'wk']
ROOT = ['favicon.svg', 'favicon.ico', 'favicon-48.png', 'favicon-192.png', 'favicon-512.png', 'manifest.webmanifest']

out = subprocess.run(['git', 'ls-files', '-s', '--', *DIRS, *ROOT], capture_output=True, text=True, encoding='utf-8', check=True).stdout
files = {}
for line in out.splitlines():
    meta, path = line.split('\t', 1)
    files[path] = meta.split()[1][:12]
json.dump({'v': 1, 'files': files}, open('offline.json', 'w', encoding='utf-8'), separators=(',', ':'), sort_keys=True)
print(len(files), 'files')
