import csv, json, os, sys
from collections import defaultdict
D, OUT = sys.argv[1], sys.argv[2]
def rows(n):
    with open(os.path.join(D, n + '.csv'), encoding='utf-8') as f: yield from csv.DictReader(f)
P = list(rows('pokemon'))
name_ko = {int(r['pokemon_species_id']): r['name'] for r in rows('pokemon_species_names') if r['local_language_id'] == '3'}
forms = {r['pokemon_id']: r['id'] for r in rows('pokemon_forms')}
fn = {r['pokemon_form_id']: r['form_name'] for r in rows('pokemon_form_names') if r['local_language_id'] == '3'}
stats = defaultdict(dict)
for r in rows('pokemon_stats'): stats[r['pokemon_id']][int(r['stat_id'])] = int(r['base_stat'])
types = defaultdict(list)
for r in sorted(rows('pokemon_types'), key=lambda r: int(r['slot'])): types[r['pokemon_id']].append(int(r['type_id']))
SKIP = {'rayquaza-mega'}  # 레쿠쟈는 메가스톤 대신 기술로 진화해서 제외
DUPE = ('tatsugiri-droopy-mega', 'tatsugiri-stretchy-mega', 'meowstic-female-mega', 'magearna-original-mega')
out = {}
for r in P:
    ide, pid, sid = r['identifier'], r['id'], int(r['species_id'])
    if sid > 1025: continue
    if ide in SKIP or ide in DUPE: continue
    if '-mega' in ide or ide.endswith('-primal'):
        kind = 'mega'
        suf = ide.split('-mega')[-1].replace('-', '').upper() if '-mega' in ide else ''
        base = name_ko[sid]
        if ide.endswith('-primal'):
            item = {'kyogre': '쪽빛구슬', 'groudon': '주홍구슬'}.get(ide.split('-')[0])
            nm = fn.get(forms.get(pid)) or f'원시{base}'
        else:
            item = f'{base}나이트{suf}'
            nm = fn.get(forms.get(pid)) or f'메가{base}{suf}'
    elif ide.endswith('-gmax'):
        kind = 'gmax'; item = '다이스프'; nm = f'거다이맥스 {name_ko[sid]}'
    else:
        continue
    s = stats[pid]
    if len(s) < 6 or not types[pid]: continue
    out[int(pid)] = {'n': nm, 'sp': sid, 'k': kind, 'item': item, 't': types[pid], 's': [s[i] for i in range(1, 7)]}
json.dump(out, open(os.path.join(OUT, 'forms.json'), 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
print(len(out), sum(1 for v in out.values() if v['k'] == 'mega'), 'mega', sum(1 for v in out.values() if v['k'] == 'gmax'), 'gmax')
print([(k, v['n'], v['item']) for k, v in list(out.items())[:5]], [(k, v['n'], v['item']) for k, v in list(out.items())[-4:]])
open(os.path.join(OUT, 'form_ids.txt'), 'w').write('\n'.join(map(str, out)))
