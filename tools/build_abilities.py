import csv, json, os, re, sys
from collections import defaultdict

# 특성 데이터를 index.html에 넣는다.
#  - D.mons[i].a = [특성1, 특성2, 숨겨진특성] (없으면 0)
#  - FORMS의 메가진화 폼에도 a (메가진화하면 특성이 바뀐다)
#  - const AB = {특성id: {k: 영문 id, n: 한국어 이름, d: 게임 속 설명}}
# 사용: python build_abilities.py <PokeAPI csv 폴더> <index.html>
CSV, HTML = sys.argv[1], sys.argv[2]
N = 1025
KO = '3'

def rows(name):
    with open(os.path.join(CSV, name + '.csv'), encoding='utf-8') as f:
        yield from csv.DictReader(f)

ident = {int(r['id']): r['identifier'] for r in rows('abilities')}
name_ko = {int(r['ability_id']): r['name'] for r in rows('ability_names') if r['local_language_id'] == KO}
flavor = {}
for r in rows('ability_flavor_text'):
    if r['language_id'] == KO:
        a, vg = int(r['ability_id']), int(r['version_group_id'])
        if vg >= flavor.get(a, (0, ''))[0]:
            flavor[a] = (vg, ' '.join(r['flavor_text'].split()))

slots = defaultdict(lambda: [0, 0, 0])
for r in rows('pokemon_abilities'):
    slots[int(r['pokemon_id'])][int(r['slot']) - 1] = int(r['ability_id'])

html = open(HTML, encoding='utf-8').read()
m = re.search(r'^const D=(\{.*\});$', html, re.M)
D = json.loads(m.group(1))
used = set()
for mon in D['mons']:
    mon['a'] = slots[mon['id']]
    used.update(x for x in mon['a'] if x)
html = html[:m.start()] + 'const D=' + json.dumps(D, ensure_ascii=False, separators=(',', ':')) + ';' + html[m.end():]

# FORMS 줄은 'const FORMS={...}, FIDX={...};' 꼴이라 앞쪽 JSON만 읽는다
start = html.index('\nconst FORMS=') + len('\nconst FORMS=')
F, end = json.JSONDecoder().raw_decode(html, start)
for k, f in F.items():
    if f['k'] == 'mega' and int(k) in slots:
        f['a'] = [slots[int(k)][0]]
        used.add(f['a'][0])
    elif f['k'] == 'alt':  # build_alt_forms.py가 넣은 폼은 특성 3칸 그대로
        used.update(x for x in f.get('a', []) if x)
html = html[:start] + json.dumps(F, ensure_ascii=False, separators=(',', ':')) + html[end:]
# 메가레쿠쟈는 index.html에서 따로 정의한다
ray = slots[10079][0]
used.add(ray)
html = re.sub(r"^(FORMS\[10079\]=\{.*?)(,a:\[\d+\])?\};$", lambda mm: mm.group(1) + f',a:[{ray}]' + '};', html, count=1, flags=re.M)

AB = {a: {'k': ident[a], 'n': name_ko.get(a, ident[a]), 'd': flavor.get(a, (0, ''))[1]} for a in sorted(used)}
line = 'const AB=' + json.dumps(AB, ensure_ascii=False, separators=(',', ':')) + ';'
if re.search(r'^const AB=.*;$', html, re.M):
    html = re.sub(r'^const AB=.*;$', lambda _: line, html, count=1, flags=re.M)
else:
    html = re.sub(r'^(const MVX=.*;)$', lambda mm: mm.group(1) + '\n' + line, html, count=1, flags=re.M)
open(HTML, 'w', encoding='utf-8', newline='\n').write(html)
print('abilities', len(AB), 'bytes', len(line), 'no korean text', [AB[a]['k'] for a in AB if not AB[a]['d']][:60])
