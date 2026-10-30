import csv, json, os, re, sys
from collections import defaultdict

# 이 게임에서 효과를 구현한 변화기를 index.html의 기술 데이터(D.moves)와 배우는 기술(D.mons의 m, tm)에 넣는다.
# 공격 기술 쪽 데이터는 건드리지 않는다. build_all.py와 같은 버전 그룹을 골라서 변화기만 추가.
# 사용: python build_status.py <PokeAPI csv 폴더> <Showdown moves.json> <index.html>
# 넣은 뒤 build_effects.py를 다시 돌려야 MVX에 변화기 효과가 들어간다.
CSV, SD, HTML = sys.argv[1], sys.argv[2], sys.argv[3]
N = 1025
KO = '3'
# index.html의 useStatus()가 처리하는 변화기 (Showdown id)
STATUS = set('''
doubleteam swordsdance calmmind workup bulkup harden agility defensecurl amnesia irondefense rockpolish honeclaws
nastyplot growth withdraw dragondance minimize howl cosmicpower meditate acidarmor shellsmash barrier quiverdance
autotomize coil cottonguard tailglow shiftgear defendorder geomancy noretreat clangoroussoul sharpen shelter filletaway
charge takeheart tidyup acupressure bellydrum focusenergy
flash confide leer growl scaryface screech tailwhip sandattack charm smokescreen metalsound faketears sweetscent
stringshot featherdance cottonspore tickle babydolleyes playnice eerieimpulse nobleroar kinesis tearfullook toxicthread
tarshot spicyextract venomdrench strengthsap
toxic thunderwave willowisp hypnosis poisonpowder stunspore sleeppowder sing poisongas spore grasswhistle glare
lovelykiss darkvoid yawn
swagger confuseray supersonic sweetkiss flatter teeterdance
raindance sunnyday sandstorm hail snowscape grassyterrain mistyterrain electricterrain psychicterrain
lightscreen reflect auroraveil safeguard mist tailwind trickroom
protect detect spikyshield kingsshield banefulbunker obstruct silktrap burningbulwark endure
rest roost recover slackoff softboiled milkdrink healorder synthesis moonlight morningsun shoreup lifedew wish aquaring
ingrain junglehealing lunarblessing painsplit refresh healbell aromatherapy
leechseed curse taunt meanlook block spiderweb haze psychup teleport attract captivate
substitute sleeptalk roar whirlwind torment helpinghand stealthrock spikes toxicspikes stickyweb defog
skillswap roleplay entrainment worryseed simplebeam gastroacid doodle encore disable batonpass naturepower metronome
splash destinybond stockpile swallow lockon mindreader copycat mirrormove memento perishsong quickguard wideguard
craftyshield matblock healingwish lunardance gravity wonderroom healpulse floralhealing magnetrise telekinesis nightmare
healblock powerswap guardswap heartswap speedswap powersplit guardsplit powertrick soak trickortreat forestscurse
reflecttype conversion conversion2 camouflage magicpowder mefirst afteryou quash instruct grudge spite magiccoat
psychoshift followme ragepowder spotlight foresight odorsleuth miracleeye transform mimic sketch assist coaching
dragoncheer laserfocus magneticflux gearup flowershield rototiller aromaticmist decorate iondeluge electrify powder
partingshot topsyturvy fairylock purify courtchange octolock revivalblessing shedtail imprison watersport mudsport
luckychant snatch trick switcheroo bestow recycle embargo magicroom stuffcheeks teatime
'''.split())
# 위력이 정해져 있지 않거나(무게·HP·레벨 등으로 정해짐) 자신이 쓰러지는 공격 기술. index.html의 power()·fixedDmg()가 처리한다
VARDMG = set('''
return frustration grassknot lowkick heavyslam heatcrash dreameater explosion selfdestruct mistyexplosion gyroball
electroball bide endeavor flail reversal nightshade seismictoss counter mirrorcoat metalburst comeuppance psywave
fissure horndrill guillotine sheercold dragonrage sonicboom spitup wringout crushgrip hardpress magnitude superfang
naturesmadness ruination punishment beatup finalgambit trumpcard present fling naturalgift
'''.split())

def rows(name):
    with open(os.path.join(CSV, name + '.csv'), encoding='utf-8') as f:
        yield from csv.DictReader(f)

sd = json.load(open(SD, encoding='utf-8'))
sd_num = {v['num']: k for k, v in sd.items() if v.get('num', 0) > 0 and k in STATUS | VARDMG}
missing = (STATUS | VARDMG) - set(sd_num.values())
if missing: sys.exit(f'Showdown에 없는 id: {sorted(missing)}')

html = open(HTML, encoding='utf-8').read()
m = re.search(r'^const D=(\{.*\});$', html, re.M)
D = json.loads(m.group(1))

# build_all.py와 같은 공격 기술 기준으로 버전 그룹을 고른다
EXCLUDE = {120, 153, 138, 165, 802, 515}
move_ko = {r['move_id']: r['name'] for r in rows('move_names') if r['local_language_id'] == KO}
dmg, status = set(), {}
for r in rows('moves'):
    mid = int(r['id'])
    if mid >= 10000: continue
    if mid in sd_num and sd_num[mid] in VARDMG:
        bp = int(r['power']) if r['power'] and int(r['power']) > 1 else 0
        status[mid] = {'n': move_ko.get(r['id'], r['identifier']), 't': int(r['type_id']), 'p': bp,
                       'a': int(r['accuracy']) if r['accuracy'] else 100, 'c': 'p' if r['damage_class_id'] == '2' else 's', 'pr': int(r['priority'])}
    elif r['damage_class_id'] == '1':
        if mid in sd_num:
            status[mid] = {'n': move_ko.get(r['id'], r['identifier']), 't': int(r['type_id']), 'p': 0,
                           'a': int(r['accuracy']) if r['accuracy'] else 100, 'c': 'x', 'pr': int(r['priority'])}
    elif mid not in EXCLUDE and r['power'] and int(r['power']) > 1:
        dmg.add(mid)

ORDER = [25, 20, 18, 23, 17, 16, 15, 14, 11, 10, 9, 8, 7, 6, 5, 4, 3, 2, 1]
lvl_d, tm_d = defaultdict(set), defaultdict(set)
lvl_s = defaultdict(lambda: defaultdict(dict))
tm_s = defaultdict(lambda: defaultdict(set))
for r in rows('pokemon_moves'):
    pid = int(r['pokemon_id'])
    if pid > N: continue
    mid, vg, how = int(r['move_id']), int(r['version_group_id']), r['pokemon_move_method_id']
    if how not in ('1', '4'): continue
    if mid in dmg:
        (lvl_d if how == '1' else tm_d)[pid].add(vg)
    elif mid in status:
        if how == '1':
            d = lvl_s[pid][vg]; L = int(r['level'] or 0); d[mid] = min(L, d.get(mid, 999))
        else:
            tm_s[pid][vg].add(mid)

added_l = added_t = 0
used = set()
for mon in D['mons']:
    i = mon['id']
    vg = next((v for v in ORDER if v in lvl_d[i]), None)
    tvg = vg if vg and vg in tm_d[i] else next((v for v in ORDER if v in tm_d[i]), None)
    have = {x for x, _ in mon['m']}
    for mid, L in (lvl_s[i][vg].items() if vg else []):
        if mid not in have:
            mon['m'].append([mid, L]); added_l += 1; used.add(mid)
    mon['m'].sort(key=lambda x: x[1])
    lset = {x for x, _ in mon['m']}
    tset = {x for x, _ in mon['tm']}
    for mid in sorted(tm_s[i][tvg] if tvg else []):
        if mid not in lset and mid not in tset:
            mon['tm'].append([mid, 8]); added_t += 1; used.add(mid)
    mon['tm'].sort(key=lambda x: x[1])

# 루브도는 스케치만 배운다(공격 기술이 없어서 위에서 버전 그룹을 못 고른다): 원작처럼 1·11·21…91레벨에
sk = next((m for m, k in sd_num.items() if k == 'sketch'), None)
if sk:
    sm = D['mons'][234]
    sm['m'] = sorted([x for x in sm['m'] if x[0] != sk] + [[sk, l] for l in range(1, 100, 10)], key=lambda x: x[1])
    used.add(sk)

for mid in sorted(used):
    D['moves'][str(mid)] = status[mid]

line = 'const D=' + json.dumps(D, ensure_ascii=False, separators=(',', ':')) + ';'
html = html[:m.start()] + line + html[m.end():]
open(HTML, 'w', encoding='utf-8', newline='\n').write(html)
print('status moves', len(used), 'of', len(STATUS), 'level-up added', added_l, 'tm added', added_t)
print('not learnable:', sorted(sd_num[x] for x in set(sd_num) - used))
