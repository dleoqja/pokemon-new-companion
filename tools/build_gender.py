import csv, json, os, re, sys
from collections import defaultdict

# 성별 데이터를 index.html의 D.mons에 넣는다.
#  - gr: 암컷 비율(8분의 몇). -1이면 성별 없음 (PokéAPI pokemon_species.gender_rate)
#  - e(진화)의 세 번째 값: 성별 조건 'F' 또는 'M' (예: 킬리아→엘레이드는 수컷만)
# 사용: python build_gender.py <PokeAPI csv 폴더> <index.html>
CSV, HTML = sys.argv[1], sys.argv[2]

def rows(name):
    with open(os.path.join(CSV, name + '.csv'), encoding='utf-8') as f:
        yield from csv.DictReader(f)

rate = {int(r['id']): int(r['gender_rate']) for r in rows('pokemon_species')}
need = defaultdict(set)  # 진화 후 종 -> 요구 성별들 ('' = 조건 없음)
for r in rows('pokemon_evolution'):
    to = int(r['evolved_species_id'])
    need[to].add({'1': 'F', '2': 'M'}.get(r['gender_id'], ''))

html = open(HTML, encoding='utf-8').read()
m = re.search(r'^const D=(\{.*\});$', html, re.M)
D = json.loads(m.group(1))
locked = 0
for mon in D['mons']:
    mon['gr'] = rate.get(mon['id'], -1)
    for e in mon['e']:
        g = need.get(e[0], {''})
        e[2:] = [next(iter(g))] if len(g) == 1 and '' not in g else []
        locked += len(e) > 2
html = html[:m.start()] + 'const D=' + json.dumps(D, ensure_ascii=False, separators=(',', ':')) + ';' + html[m.end():]
open(HTML, 'w', encoding='utf-8', newline='\n').write(html)
print('gender rates', len(D['mons']), 'genderless', sum(1 for x in D['mons'] if x['gr'] < 0), 'gender-locked evolutions', locked)
