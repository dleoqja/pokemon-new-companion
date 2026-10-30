import csv, json, sys, os
from collections import defaultdict

D, OUT = sys.argv[1], sys.argv[2]
N = 1025
KO = '3'
def rows(name):
    with open(os.path.join(D, name + '.csv'), encoding='utf-8') as f:
        yield from csv.DictReader(f)

# ---------- 기술 ----------
EXCLUDE = {120, 153, 138, 165, 802, 515}  # 자폭, 대폭발, 꿈먹기, 발버둥, 미스트버스트, 목숨걸기
# 반동·모으기 기술(파괴광선, 솔라빔 등)은 원작 위력 그대로. 쉬는 턴·모으는 턴은 index.html에서 처리
move_ko = {r['move_id']: r['name'] for r in rows('move_names') if r['local_language_id'] == KO}
moves = {}
for r in rows('moves'):
    mid = int(r['id'])
    if mid >= 10000 or mid in EXCLUDE or not r['power'] or r['damage_class_id'] == '1':
        continue
    p = int(r['power'])
    if p <= 1:
        continue
    moves[mid] = {'n': move_ko.get(r['id'], r['identifier']), 't': int(r['type_id']), 'p': p,
                  'a': int(r['accuracy']) if r['accuracy'] else 100,
                  'c': 'p' if r['damage_class_id'] == '2' else 's', 'pr': int(r['priority'])}

# ---------- 종 ----------
name_ko = {int(r['pokemon_species_id']): r['name'] for r in rows('pokemon_species_names')
           if r['local_language_id'] == KO and int(r['pokemon_species_id']) <= N}
stats = defaultdict(dict)
for r in rows('pokemon_stats'):
    pid = int(r['pokemon_id'])
    if pid <= N: stats[pid][int(r['stat_id'])] = int(r['base_stat'])
types = defaultdict(list)
for r in sorted(rows('pokemon_types'), key=lambda r: int(r['slot'])):
    pid = int(r['pokemon_id'])
    if pid <= N: types[pid].append(int(r['type_id']))
spec = {int(r['id']): r for r in rows('pokemon_species') if int(r['id']) <= N}
# 무게(0.1kg 단위): 안다리걸기·풀묶기·헤비봄버 등
weight = {int(r['species_id']): int(r['weight']) for r in rows('pokemon') if r['is_default'] == '1' and int(r['species_id']) <= N}

# ---------- 진화 ----------
# 요즘 PokéAPI CSV는 기본 모습 진화에도 폼 번호(= 종 번호, 10000 미만)가 붙는다. 10000 이상이 다른 폼(지역폼 등)
base_form = lambda v: not v or int(v) < 10000
by_target = defaultdict(list)
for r in rows('pokemon_evolution'):
    to = int(r['evolved_species_id'])
    if to <= N: by_target[to].append(r)
evos = defaultdict(list)
for to, rs in by_target.items():
    fr = spec[to]['evolves_from_species_id']
    if not fr: continue
    ok = [r for r in rs if base_form(r['evolved_pokemon_form_id']) and base_form(r['required_pokemon_form_id'])]
    # 지역폼에서만 진화하는 포켓몬(가라르 나옹→나이킹 등): 이 게임엔 지역폼이 없어서 기본 모습에서 진화한다
    if not ok: ok = rs
    lvr = [r for r in ok if r['minimum_level']]
    if lvr:
        lv = min(int(r['minimum_level']) for r in lvr)
    elif any(r['evolution_trigger_id'] == '2' for r in ok):
        lv = 36   # 통신교환
    elif any(r['evolution_trigger_id'] == '3' for r in ok):
        lv = 30   # 진화의 돌
    else:
        lv = 28   # 친밀도·기술·시간 등 조건 진화
    mv = next((int(r['known_move_id']) for r in ok if r['known_move_id']), None)
    gd = all(r['gender_id'] for r in ok)
    evos[int(fr)].append([to, lv, bool(lvr), mv, gd])

# ---------- 기술 배치: 최신 버전 우선 ----------
ORDER = [25, 20, 18, 23, 17, 16, 15, 14, 11, 10, 9, 8, 7, 6, 5, 4, 3, 2, 1]
lvl = defaultdict(lambda: defaultdict(dict))
tmm = defaultdict(lambda: defaultdict(dict))
for r in rows('pokemon_moves'):
    pid = int(r['pokemon_id'])
    if pid > N: continue
    mid = int(r['move_id'])
    if mid not in moves: continue
    vg = int(r['version_group_id'])
    if r['pokemon_move_method_id'] == '1':
        L = int(r['level'] or 0)
        d = lvl[pid][vg]; d[mid] = min(L, d.get(mid, 999))
    elif r['pokemon_move_method_id'] == '4':
        tmm[pid][vg][mid] = max(8, round(moves[mid]['p'] * 0.4))

mons, srcvg = [], {}
for i in range(1, N + 1):
    vg = next((v for v in ORDER if lvl[i].get(v)), None)
    srcvg[i] = vg
    lm = sorted([[m, l] for m, l in (lvl[i][vg].items() if vg else [])], key=lambda x: x[1])
    # 레벨 1에 기술이 너무 많으면(최신작 특징) 위력 낮은 2개만 시작 기술로
    l1 = [x for x in lm if x[1] == 1]
    if len(l1) > 2:
        keep = sorted(l1, key=lambda x: moves[x[0]]['p'])[:2]
        rest = [x for x in l1 if x not in keep]
        for k, x in enumerate(sorted(rest, key=lambda x: moves[x[0]]['p'])):
            x[1] = 4 + k * 3  # 나머지는 조금씩 늦게
        lm = sorted(lm, key=lambda x: x[1])
    if not any(0 < l <= 5 for _, l in lm):
        lm.insert(0, [33, 1])
    tvg = vg if vg and tmm[i].get(vg) else next((v for v in ORDER if tmm[i].get(v)), None)
    lset = {m for m, _ in lm}
    tm = sorted([[m, l] for m, l in (tmm[i][tvg].items() if tvg else []) if m not in lset], key=lambda x: x[1])
    s = stats[i]; sp = spec[i]
    mons.append({'id': i, 'n': name_ko[i], 't': types[i], 's': [s[1], s[2], s[3], s[4], s[5], s[6]],
                 'L': sp['is_legendary'] == '1' or sp['is_mythical'] == '1', 'g': int(sp['generation_id']),
                 'f': int(sp['evolves_from_species_id']) if sp['evolves_from_species_id'] else 0,
                 'e': evos.get(i, []), 'm': lm, 'tm': tm, 'w': weight.get(i, 100)})
    if sp['is_mythical'] == '1': mons[-1]['my'] = 1  # 환상의 포켓몬 (10층부터 보스는 전설만)

# ---------- 진화 레벨 꼬임 바로잡기 ----------
# 레벨이 없는 조건 진화(통신교환·돌·친밀도·기술 등)는 임시 레벨을 쓰는데, 그게 앞 단계 진화 레벨보다 낮거나 같으면
# 진화하자마자 또 진화해 버린다(예: 꾸꾸리 33 → 메꾸리, 메꾸리 28 → 맘모꾸리).
#  - 다음 단계가 조건 진화면: 그 기술을 배우는 레벨(앞 단계보다 높을 때), 아니면 앞 단계 + 10
#  - 아기 포켓몬처럼 앞 단계가 조건 진화고 다음 단계가 진짜 레벨이면: 앞 단계를 다음 단계 - 8로
by_id = {m['id']: m for m in mons}
for m in mons:
    for e1 in m['e']:
        for e2 in by_id[e1[0]]['e']:
            if e2[1] > e1[1]: continue
            if not e2[2]:
                learn = next((l for x, l in by_id[e1[0]]['m'] if x == e2[3]), 0) if e2[3] else 0
                e2[1] = learn if learn > e1[1] else e1[1] + 10
            elif not e1[2]:
                e1[1] = max(1, e2[1] - 8)
# 갈래 진화에서 조건 진화가 레벨 진화보다 먼저면 늘 그쪽으로만 진화한다(야돈 → 야도킹 36 / 야도란 37) → 같은 레벨로 맞춰 무작위로
for m in mons:
    real = [e[1] for e in m['e'] if e[2]]
    for e in m['e']:
        if real and not e[2] and not e[4] and e[1] < max(real): e[1] = max(real)
# 갈래가 모두 조건 진화면(이브이·슈륙챙이·스라크) 가장 빠른 레벨에 맞춰서, 진화할 때 한 번에 고를 수 있게
for m in mons:
    if len(m['e']) > 1 and not any(e[2] for e in m['e']) and not any(e[4] for e in m['e']):
        lo = min(e[1] for e in m['e'])
        for e in m['e']: e[1] = lo
for m in mons:
    m['e'] = [e[:2] for e in m['e']]

eff = [[1.0] * 19 for _ in range(19)]
for r in rows('type_efficacy'):
    a, b = int(r['damage_type_id']), int(r['target_type_id'])
    if a <= 18 and b <= 18: eff[a][b] = int(r['damage_factor']) / 100
used = {m for mon in mons for m, _ in mon['m'] + mon['tm']}
data = {'mons': mons, 'moves': {k: v for k, v in moves.items() if k in used}, 'eff': eff}
os.makedirs(OUT, exist_ok=True)
with open(os.path.join(OUT, 'data.json'), 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, separators=(',', ':'))
print('mons', len(mons), 'moves', len(data['moves']), 'size', os.path.getsize(os.path.join(OUT, 'data.json')))
print('no learnset', [i for i in range(1, N + 1) if not srcvg[i]])
for i in (1, 152, 906, 909, 912, 1000, 133, 52):
    m = mons[i - 1]; print(m['n'], m['e'], [(data['moves'][x]['n'], l) for x, l in m['m']][:8], len(m['tm']))
