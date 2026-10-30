import json, os, re, sys, urllib.request
from PIL import Image

# 처음 걷기 시트(build_walk9.py)를 만들 때 SpriteCollab에 걷기 도트가 없던 포켓몬 중, 나중에 생기거나 다른 모습으로만 있는 것을
# 기존 wk/n{k}.png의 빈 칸(id 자리)에 넣고 index.html의 HAVE_N에 더한다. 이로치 걷기 도트는 없어서 이로치도 일반 색으로 걷는다.
# 사용: python build_walk_extra.py <작업 폴더> <게임 폴더>
WORK, GAME = sys.argv[1], sys.argv[2]
PMD = 'https://raw.githubusercontent.com/PMDCollab/SpriteCollab/master/sprite'
# id -> SpriteCollab 폴더 (기본 모습이 없으면 걸어 다니는 다른 모습)
EXTRA = {837: '0837', 870: '0870/0002', 999: '0999/0001', 1003: '1003/0001', 1008: '1008/0001'}
CELL, NF, PER_ROW, PER_SHEET = 48, 4, 8, 128
DIRS = [0, 6, 2, 4]  # 아래, 왼쪽, 오른쪽, 위

def get(url, path):
    if os.path.exists(path): return
    os.makedirs(os.path.dirname(path), exist_ok=True)
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req, timeout=60) as r: open(path, 'wb').write(r.read())

sheets = {}
for i, sub in EXTRA.items():
    d = f'{WORK}/pmd/{i}'
    get(f'{PMD}/{sub}/Walk-Anim.png', f'{d}/Walk-Anim.png'); get(f'{PMD}/{sub}/AnimData.xml', f'{d}/AnimData.xml')
    xml = open(f'{d}/AnimData.xml', encoding='utf-8').read()
    b = re.search(r'<Name>Walk</Name>(.*?)</Anim>', xml, re.S).group(1)
    fw = int(re.search(r'<FrameWidth>(\d+)', b).group(1)); fh = int(re.search(r'<FrameHeight>(\d+)', b).group(1))
    n = len(re.findall(r'<Duration>', b))
    im = Image.open(f'{d}/Walk-Anim.png').convert('RGBA')
    frames = [[im.crop(((kk * n // NF) * fw, dr * fh, (kk * n // NF) * fw + fw, dr * fh + fh)) for kk in range(NF)] for dr in DIRS]
    l, t, r, btm = fw, fh, 0, 0
    for row in frames:
        for f in row:
            bb = f.getbbox()
            if bb: l, t, r, btm = min(l, bb[0]), min(t, bb[1]), max(r, bb[2]), max(btm, bb[3])
    cx = fw // 2; half = max(cx - l, r - cx)
    s = min(1.0, CELL / max(half * 2, btm - t, 1))
    k = (i - 1) // PER_SHEET
    if k not in sheets: sheets[k] = Image.open(f'{GAME}/wk/n{k}.png').convert('RGBA')
    sheet = sheets[k]; j = (i - 1) % PER_SHEET; bx, by = j % PER_ROW, j // PER_ROW
    sheet.paste(Image.new('RGBA', (NF * CELL, 4 * CELL)), (bx * NF * CELL, by * 4 * CELL))  # 그 칸을 비우고
    for di, row in enumerate(frames):
        for kk, f in enumerate(row):
            c = f.crop((cx - half, t, cx + half, btm))
            if s < 1: c = c.resize((max(1, round(c.width * s)), max(1, round(c.height * s))), Image.NEAREST)
            sheet.paste(c, (bx * NF * CELL + kk * CELL + (CELL - c.width) // 2, (by * 4 + di) * CELL + (CELL - c.height)), c)
for k, sheet in sheets.items(): sheet.save(f'{GAME}/wk/n{k}.png', optimize=True)

html = open(f'{GAME}/index.html', encoding='utf-8').read()
m = re.search(r'HAVE_N=new Set\((\[[\d,]*\])\)', html)
have = sorted(set(json.loads(m.group(1))) | set(EXTRA))
html = html[:m.start(1)] + json.dumps(have, separators=(',', ':')) + html[m.end(1):]
open(f'{GAME}/index.html', 'w', encoding='utf-8', newline='\n').write(html)
print('walk extra', sorted(EXTRA), 'HAVE_N', len(have))
