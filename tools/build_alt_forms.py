import csv, importlib.util, json, os, re, sys, urllib.request
from collections import defaultdict

# 배틀 중 모습이 바뀌는 특성용 폼(달마모드·블레이드폼·어군 등)의 도트와 데이터를 넣는다.
#  - PokéAPI sprites에서 Showdown GIF(앞/뒤, 일반/이로치)와 정지 도트를 받아
#    build_assets9.one()으로 기존과 같은 묶음 형식으로 만든 뒤 bt/xf9.json, bt/xb9.json에 쓴다
#  - index.html의 FORMS에 {k:'alt'} 항목을, FIDX에 묶음 번호를 넣는다
# 사용: python build_alt_forms.py <PokeAPI csv 폴더> <작업 폴더> <게임 폴더>
CSV, WORK, GAME = sys.argv[1], sys.argv[2], sys.argv[3]
CHUNK = 9
# 폼 pokemon id -> 화면에 쓸 폼 이름
ALT = {10017: '달마모드', 10026: '블레이드폼', 10127: '군집의 모습', 10136: '빨간색 코어', 10182: '그대로 삼킨 모습',
       10183: '통째로 삼킨 모습', 10185: '나이스페이스', 10187: '배고픈 모양', 10256: '마이티폼', 10276: '테라스탈폼',
       10188: '검왕', 10189: '방패왕', 10007: '오리진폼', 10245: '오리진폼', 10246: '오리진폼'}  # 지닌 도구로 바뀌는 폼(녹슨검·녹슨방패·백금옥·금강옥·백옥)
SPR = 'https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon'

def rows(name):
    with open(os.path.join(CSV, name + '.csv'), encoding='utf-8') as f:
        yield from csv.DictReader(f)

def get(url, path):
    if os.path.exists(path): return True
    os.makedirs(os.path.dirname(path), exist_ok=True)
    try:
        with urllib.request.urlopen(url, timeout=60) as r: data = r.read()
    except Exception:
        return False
    open(path, 'wb').write(data); return True

for i in ALT:
    get(f'{SPR}/other/showdown/{i}.gif', f'{WORK}/sd/f/{i}.gif')
    get(f'{SPR}/other/showdown/back/{i}.gif', f'{WORK}/sd/b/{i}.gif')
    get(f'{SPR}/other/showdown/shiny/{i}.gif', f'{WORK}/sd/fs/{i}.gif')
    get(f'{SPR}/other/showdown/back/shiny/{i}.gif', f'{WORK}/sd/bs/{i}.gif')
    get(f'{SPR}/{i}.png', f'{WORK}/st/f/{i}.png')
    get(f'{SPR}/shiny/{i}.png', f'{WORK}/st/fs/{i}.png')
    # 정지 도트가 없으면 GIF 첫 프레임으로 대신한다
    from PIL import Image
    for a, b in (('sd/f', 'st/f'), ('sd/fs', 'st/fs')):
        if not os.path.exists(f'{WORK}/{b}/{i}.png') and os.path.exists(f'{WORK}/{a}/{i}.gif'):
            Image.open(f'{WORK}/{a}/{i}.gif').convert('RGBA').save(f'{WORK}/{b}/{i}.png')
    if not os.path.exists(f'{WORK}/st/fs/{i}.png') and os.path.exists(f'{WORK}/st/f/{i}.png'):
        Image.open(f'{WORK}/st/f/{i}.png').save(f'{WORK}/st/fs/{i}.png')

sys.argv = ['x', WORK, os.path.join(WORK, 'out')]
spec = importlib.util.spec_from_file_location('b', os.path.join(os.path.dirname(os.path.abspath(__file__)), 'build_assets9.py'))
b = importlib.util.module_from_spec(spec); spec.loader.exec_module(b)
ok = [i for i in ALT if os.path.exists(f'{WORK}/st/f/{i}.png')]
res = dict(b.one(i) for i in ok)
for side in 'fb':
    json.dump({str(i): res[i][side] for i in ok}, open(os.path.join(GAME, 'bt', f'x{side}{CHUNK}.json'), 'w'), separators=(',', ':'))

# 폼 데이터: 능력치·타입·특성
stats = defaultdict(dict)
for r in rows('pokemon_stats'): stats[int(r['pokemon_id'])][int(r['stat_id'])] = int(r['base_stat'])
types = defaultdict(list)
for r in sorted(rows('pokemon_types'), key=lambda r: int(r['slot'])): types[int(r['pokemon_id'])].append(int(r['type_id']))
abil = defaultdict(lambda: [0, 0, 0])
for r in rows('pokemon_abilities'): abil[int(r['pokemon_id'])][int(r['slot']) - 1] = int(r['ability_id'])
species = {int(r['id']): int(r['species_id']) for r in rows('pokemon')}
name_ko = {int(r['pokemon_species_id']): r['name'] for r in rows('pokemon_species_names') if r['local_language_id'] == '3'} if os.path.exists(os.path.join(CSV, 'pokemon_species_names.csv')) else {}

html = open(os.path.join(GAME, 'index.html'), encoding='utf-8').read()
start = html.index('\nconst FORMS=') + len('\nconst FORMS=')
dec = json.JSONDecoder()
F, end = dec.raw_decode(html, start)
fx = html.index('FIDX=', end) + len('FIDX=')
FIDX, fend = dec.raw_decode(html, fx)
for i in ok:
    sid = species[i]; s = stats[i]
    F[str(i)] = {'n': name_ko.get(sid, ''), 'fn': ALT[i], 'sp': sid, 'k': 'alt', 't': types[i], 's': [s[k] for k in range(1, 7)], 'a': abil[i]}
    FIDX[str(i)] = CHUNK
html = html[:start] + json.dumps(F, ensure_ascii=False, separators=(',', ':')) + html[end:fx] + json.dumps(FIDX, separators=(',', ':')) + html[fend:]
open(os.path.join(GAME, 'index.html'), 'w', encoding='utf-8', newline='\n').write(html)
print('alt forms', ok, 'missing', [i for i in ALT if i not in ok], 'bundle bytes', sum(os.path.getsize(os.path.join(GAME, 'bt', f'x{s}{CHUNK}.json')) for s in 'fb'))
