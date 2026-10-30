import json, re, sys

# 기술 추가 효과 표(MVX)를 Pokémon Showdown 데이터에서 뽑아 index.html에 넣는다.
# 사용: python build_effects.py <showdown moves.json> <index.html>
# moves.json은 https://play.pokemonshowdown.com/data/moves.json
SD, HTML = sys.argv[1], sys.argv[2]
STATS = {'atk', 'def', 'spa', 'spd', 'spe', 'accuracy', 'evasion'}

sd = json.load(open(SD, encoding='utf-8'))
bynum = {}
for k, v in sd.items():
    n = v.get('num', 0)
    if n > 0 and (n not in bynum or not v.get('isNonstandard')):
        bynum[n] = (k, v)

html = open(HTML, encoding='utf-8').read()
D = json.loads(re.search(r'^const D=(\{.*\});$', html, re.M).group(1))
ids = sorted({int(k) for k in D['moves']} | {620, 744, 795})

def boosts(b):
    return {k: v for k, v in (b or {}).items() if k in STATS and v}

def sec(s):
    o = {'c': s.get('chance', 100)}
    if s.get('status'): o['s'] = s['status']
    if s.get('volatileStatus'): o['v'] = s['volatileStatus']
    if boosts(s.get('boosts')): o['b'] = boosts(s['boosts'])
    if s.get('self') and boosts(s['self'].get('boosts')): o['sb'] = boosts(s['self']['boosts'])
    return o if len(o) > 1 else None

out = {}
for i in ids:
    k, v = bynum[i]
    o = {'id': k, 'pp': v.get('pp', 10)}
    secs = [sec(s) for s in (v.get('secondaries') or ([v['secondary']] if v.get('secondary') else []))]
    if any(secs): o['sec'] = [s for s in secs if s]
    sf = v.get('self') or {}
    if boosts(sf.get('boosts')): o['sb'] = boosts(sf['boosts'])
    if sf.get('volatileStatus'): o['sv'] = sf['volatileStatus']
    if v.get('selfBoost'): o['sbo'] = boosts(v['selfBoost'].get('boosts'))
    if v.get('volatileStatus'): o['vs'] = v['volatileStatus']
    if v.get('status'): o['st'] = v['status']
    if v.get('multihit'): o['hit'] = v['multihit']
    if v.get('drain'): o['dr'] = round(v['drain'][0] / v['drain'][1], 3)
    if v.get('recoil'): o['rc'] = round(v['recoil'][0] / v['recoil'][1], 3)
    if v.get('critRatio', 1) > 1: o['cr'] = v['critRatio'] - 1
    if v.get('willCrit'): o['wc'] = 1
    if v.get('accuracy') is True: o['ah'] = 1
    if v.get('multiaccuracy'): o['ma'] = 1
    if v.get('flags', {}).get('defrost'): o['df'] = 1
    if v.get('thawsTarget'): o['tt'] = 1
    if v.get('flags', {}).get('sound'): o['snd'] = 1
    if v.get('flags', {}).get('contact'): o['ct'] = 1
    if v.get('flags', {}).get('charge'): o['chg'] = 1  # 1턴째에 모으고 2턴째에 쓰는 기술
    # 2대2에서 맞는 대상: af=상대 모두, aa=자신 빼고 모두(아군 포함), r=무작위 상대 (없으면 고른 상대 하나)
    ta = {'allAdjacentFoes': 'af', 'allAdjacent': 'aa', 'randomNormal': 'r'}.get(v.get('target'))
    if ta: o['ta'] = ta
    # 특성이 보는 기술 분류: 펀치(철주먹), 물기(옹골찬턱), 파동(메가런처), 베기(예리함), 구슬·폭탄(방탄), 바람(바람타기), 회복(힐링시프트)
    for flag, key in (('punch', 'pu'), ('bite', 'bi'), ('pulse', 'pl'), ('slicing', 'sl'), ('bullet', 'bu'), ('wind', 'wi'), ('heal', 'hl')):
        if v.get('flags', {}).get(flag): o[key] = 1
    if v.get('category') == 'Status':
        # 변화기: 대상(자신/상대), 랭크 변화, 상태이상, 날씨·필드, 회복량
        o['tg'] = 's' if v.get('target') in ('self', 'allies', 'allySide', 'adjacentAllyOrSelf', 'allyTeam', 'all') else 'f'
        if boosts(v.get('boosts')): o['b'] = boosts(v['boosts'])
        if v.get('weather'): o['wx'] = {'raindance': 'rain', 'sunnyday': 'sun', 'sandstorm': 'sand', 'hail': 'hail', 'snowscape': 'snow'}[v['weather'].lower()]
        if v.get('terrain'): o['ter'] = v['terrain'].replace('terrain', '')
        if v.get('sideCondition'): o['side'] = v['sideCondition']
        if v.get('pseudoWeather'): o['fld'] = v['pseudoWeather']
        if v.get('heal'): o['heal'] = round(v['heal'][0] / v['heal'][1], 3)
        if v.get('flags', {}).get('powder'): o['pw'] = 1
        if v.get('ignoreImmunity') is False: o['imm'] = 1
        if v.get('stallingMove'): o['stall'] = 1
    out[i] = o

line = 'const MVX=' + json.dumps(out, ensure_ascii=False, separators=(',', ':')) + ';'
if re.search(r'^const MVX=.*;$', html, re.M):
    html = re.sub(r'^const MVX=.*;$', lambda _: line, html, count=1, flags=re.M)
else:
    html = re.sub(r'^(const D=.*;)$', lambda m: m.group(1) + '\n' + line, html, count=1, flags=re.M)
open(HTML, 'w', encoding='utf-8', newline='\n').write(html)
print('moves', len(out), 'with effects', sum(1 for o in out.values() if len(o) > 1), 'bytes', len(line))
