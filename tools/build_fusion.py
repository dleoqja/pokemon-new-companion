import importlib.util, json, os, sys, urllib.request
from PIL import Image, ImageDraw

# 합체 포켓몬(블랙·화이트큐레무, 황혼의갈기·새벽의날개 네크로즈마)의 배틀 도트·아이콘과 합체 도구 아이콘을 만든다.
#  - PokéAPI sprites의 Showdown GIF(앞/뒤, 일반/이로치)로 build_assets9.one()과 같은 묶음 형식을 만들어 bt/xf10.json, bt/xb10.json에 쓰고
#    index.html의 FIDX에 묶음 번호를 넣는다. 아이콘은 정지 도트(96px)를 ic/e{id}.png, ic/e{id}s.png로
#  - 유전자쐐기 아이콘은 PokéAPI 도구 도트, 네크로플러스솔·루나는 PokéAPI에 없어서 직접 그린다(it/n-solarizer.png, it/n-lunarizer.png)
#  - 종족값·타입·특성은 index.html의 FUSE·EXTRA에 직접 적혀 있다(PokéAPI pokemon_stats·types·abilities 그대로)
# 사용: python build_fusion.py <작업 폴더> <게임 폴더>  (그다음 git add 하고 build_offline.py)
WORK, GAME = sys.argv[1], sys.argv[2]
CHUNK = 10
IDS = [10022, 10023, 10155, 10156]
SPR = 'https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites'

def get(url, path):
    if os.path.exists(path): return True
    os.makedirs(os.path.dirname(path), exist_ok=True)
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=60) as r: data = r.read()
    except Exception:
        return False
    open(path, 'wb').write(data); return True

for i in IDS:
    get(f'{SPR}/pokemon/other/showdown/{i}.gif', f'{WORK}/sd/f/{i}.gif')
    get(f'{SPR}/pokemon/other/showdown/back/{i}.gif', f'{WORK}/sd/b/{i}.gif')
    get(f'{SPR}/pokemon/other/showdown/shiny/{i}.gif', f'{WORK}/sd/fs/{i}.gif')
    get(f'{SPR}/pokemon/other/showdown/back/shiny/{i}.gif', f'{WORK}/sd/bs/{i}.gif')
    get(f'{SPR}/pokemon/{i}.png', f'{WORK}/st/f/{i}.png')
    get(f'{SPR}/pokemon/shiny/{i}.png', f'{WORK}/st/fs/{i}.png')
    for src, dst in ((f'{WORK}/st/f/{i}.png', f'{GAME}/ic/e{i}.png'), (f'{WORK}/st/fs/{i}.png', f'{GAME}/ic/e{i}s.png')):
        Image.open(src).convert('RGBA').resize((96, 96), Image.NEAREST).save(dst, optimize=True)

sys.argv = ['x', WORK, os.path.join(WORK, 'out')]
spec = importlib.util.spec_from_file_location('b', os.path.join(os.path.dirname(os.path.abspath(__file__)), 'build_assets9.py'))
b = importlib.util.module_from_spec(spec); spec.loader.exec_module(b)
res = dict(b.one(i) for i in IDS)
for side in 'fb':
    json.dump({str(i): res[i][side] for i in IDS}, open(os.path.join(GAME, 'bt', f'x{side}{CHUNK}.json'), 'w'), separators=(',', ':'))

# FIDX에 묶음 번호
html = open(os.path.join(GAME, 'index.html'), encoding='utf-8').read()
fx = html.index('FIDX=') + len('FIDX=')
FIDX, fend = json.JSONDecoder().raw_decode(html, fx)
for i in IDS: FIDX[str(i)] = CHUNK
html = html[:fx] + json.dumps(FIDX, separators=(',', ':')) + html[fend:]
open(os.path.join(GAME, 'index.html'), 'w', encoding='utf-8', newline='\n').write(html)

# 합체 도구 아이콘
get(f'{SPR}/items/dna-splicers.png', f'{GAME}/it/dna-splicers.png')
def prism(path, core, glow, mark):
    """네크로즈마의 빛을 담은 프리즘 결정(30x30). mark: 'sun' 또는 'moon'"""
    S = 4; W = 30 * S
    im = Image.new('RGBA', (W, W), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.ellipse([3 * S, 3 * S, 27 * S, 27 * S], fill=glow + (90,))
    pts = [(15, 2), (24, 11), (19, 28), (11, 28), (6, 11)]
    d.polygon([(x * S, y * S) for x, y in pts], fill=(24, 22, 36, 255))
    inner = [(15, 4), (22, 11.5), (18, 26), (12, 26), (8, 11.5)]
    d.polygon([(x * S, y * S) for x, y in inner], fill=core + (255,))
    d.polygon([(15 * S, 4 * S), (22 * S, 11.5 * S), (15 * S, 13 * S)], fill=(255, 255, 255, 120))
    d.line([(8 * S, 11.5 * S), (22 * S, 11.5 * S)], fill=(24, 22, 36, 255), width=S)
    if mark == 'sun':
        d.ellipse([12 * S, 15 * S, 18 * S, 21 * S], fill=(255, 246, 190, 255))
        for dx, dy in ((0, -5), (0, 5), (-5, 0), (5, 0)):
            d.line([((15 + dx * .6) * S, (18 + dy * .6) * S), ((15 + dx) * S, (18 + dy) * S)], fill=(255, 246, 190, 255), width=S)
    else:
        d.ellipse([12 * S, 15 * S, 18 * S, 21 * S], fill=(236, 232, 255, 255))
        d.ellipse([13.6 * S, 14.2 * S, 19.6 * S, 20.2 * S], fill=core + (255,))
    im.resize((30, 30), Image.LANCZOS).save(path, optimize=True)
# 숲 걷기 도트(wk/fuse.png): PMD SpriteCollab의 큐레무 블랙(0646/0001)·화이트(0646/0002). build_walk9.py와 같은 칸(48px, 4프레임, 아래/왼/오/위)
# 네크로즈마 황혼의갈기·새벽의날개는 SpriteCollab에 걷기 도트가 없어서 게임이 솔가레오·루나아라 것을 쓴다(FUSE의 wk가 없으면 mate)
import re
PMD = 'https://raw.githubusercontent.com/PMDCollab/SpriteCollab/master/sprite'
WALK = [(10022, '0646/0001'), (10023, '0646/0002')]
CELL, NF, DIRS = 48, 4, [0, 6, 2, 4]
sheet = Image.new('RGBA', (len(WALK) * NF * CELL, 4 * CELL), (0, 0, 0, 0))
for j, (i, sub) in enumerate(WALK):
    get(f'{PMD}/{sub}/Walk-Anim.png', f'{WORK}/pmd/{i}/Walk-Anim.png'); get(f'{PMD}/{sub}/AnimData.xml', f'{WORK}/pmd/{i}/AnimData.xml')
    xml = open(f'{WORK}/pmd/{i}/AnimData.xml', encoding='utf-8').read()
    blk = re.search(r'<Name>Walk</Name>(.*?)</Anim>', xml, re.S).group(1)
    fw = int(re.search(r'<FrameWidth>(\d+)', blk).group(1)); fh = int(re.search(r'<FrameHeight>(\d+)', blk).group(1))
    n = len(re.findall(r'<Duration>', blk))
    im = Image.open(f'{WORK}/pmd/{i}/Walk-Anim.png').convert('RGBA')
    frames = [[im.crop(((kk * n // NF) * fw, dr * fh, (kk * n // NF) * fw + fw, dr * fh + fh)) for kk in range(NF)] for dr in DIRS]
    l, tp, r, btm = fw, fh, 0, 0
    for row in frames:
        for f in row:
            bb = f.getbbox()
            if bb: l, tp, r, btm = min(l, bb[0]), min(tp, bb[1]), max(r, bb[2]), max(btm, bb[3])
    cx = fw // 2; half = max(cx - l, r - cx)
    s = min(1.0, CELL / max(half * 2, btm - tp, 1))
    for di, row in enumerate(frames):
        for kk, f in enumerate(row):
            c = f.crop((cx - half, tp, cx + half, btm))
            if s < 1: c = c.resize((max(1, round(c.width * s)), max(1, round(c.height * s))), Image.NEAREST)
            sheet.paste(c, (j * NF * CELL + kk * CELL + (CELL - c.width) // 2, di * CELL + (CELL - c.height)), c)
sheet.save(f'{GAME}/wk/fuse.png', optimize=True)

prism(f'{GAME}/it/n-solarizer.png', (232, 150, 40), (255, 190, 60), 'sun')
prism(f'{GAME}/it/n-lunarizer.png', (98, 80, 200), (150, 120, 255), 'moon')
print('fusion', IDS, 'bundle bytes', sum(os.path.getsize(os.path.join(GAME, 'bt', f'x{s}{CHUNK}.json')) for s in 'fb'))
