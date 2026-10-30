import csv, json, os, re, sys, urllib.request

# 도구 데이터(ITEMS)와 아이콘(it/*.png)을 만든다.
#  - 이름: PokéAPI item_names(한국어). 메가스톤은 index.html FORMS의 item 이름으로 짝지어 폼 번호(f)를 붙인다
#  - 아이콘: PokéAPI sprites의 items/{identifier}.png → it/{identifier}.png
#  - 효과 설명·실제 효과는 index.html(ITEM_TXT, 배틀 코드)에 있다. 여기서는 이름·분류·아이콘만
# 사용: python build_items.py <PokeAPI csv 폴더> <게임 폴더>
CSV, GAME = sys.argv[1], sys.argv[2]
ICON = 'https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/items/{}.png'

# 분류 c: b=열매(바닥에서 줍는다), w=전투 도구(보스 보상 가운데 상자), x=포켓몬 전용(보스 보상 왼쪽 상자, 5층부터), r=이상한사탕
BERRY = '''oran-berry sitrus-berry lum-berry cheri-berry chesto-berry pecha-berry rawst-berry aspear-berry persim-berry leppa-berry
figy-berry wiki-berry mago-berry aguav-berry iapapa-berry liechi-berry ganlon-berry salac-berry petaya-berry apicot-berry
lansat-berry starf-berry micle-berry custap-berry jaboca-berry rowap-berry kee-berry maranga-berry enigma-berry
occa-berry passho-berry wacan-berry rindo-berry yache-berry chople-berry kebia-berry shuca-berry coba-berry payapa-berry
tanga-berry charti-berry kasib-berry haban-berry colbur-berry babiri-berry roseli-berry chilan-berry'''.split()
BATTLE = '''life-orb choice-band choice-specs choice-scarf leftovers black-sludge focus-sash focus-band weakness-policy rocky-helmet
assault-vest eviolite expert-belt shell-bell light-clay flame-orb toxic-orb big-root wide-lens zoom-lens scope-lens razor-claw
kings-rock quick-claw bright-powder white-herb mental-herb power-herb mirror-herb eject-button red-card eject-pack air-balloon
damp-rock heat-rock smooth-rock icy-rock terrain-extender metronome safety-goggles heavy-duty-boots booster-energy clear-amulet
covert-cloak punching-glove protective-pads loaded-dice throat-spray room-service blunder-policy binding-band grip-claw shed-shell
sticky-barb iron-ball lagging-tail ring-target float-stone muscle-band wise-glasses absorb-bulb cell-battery luminous-moss snowball
destiny-knot smoke-ball ability-shield utility-umbrella
silk-scarf black-belt sharp-beak poison-barb soft-sand hard-stone silver-powder spell-tag metal-coat charcoal mystic-water
miracle-seed magnet twisted-spoon never-melt-ice dragon-fang black-glasses fairy-feather'''.split()
EXCL = '''rusted-sword rusted-shield light-ball thick-club lucky-punch deep-sea-tooth deep-sea-scale metal-powder quick-powder
stick soul-dew adamant-orb lustrous-orb griseous-orb
flame-plate splash-plate zap-plate meadow-plate icicle-plate fist-plate toxic-plate earth-plate sky-plate mind-plate insect-plate
stone-plate spooky-plate draco-plate dread-plate iron-plate pixie-plate
fire-memory water-memory electric-memory grass-memory ice-memory fighting-memory poison-memory ground-memory flying-memory
psychic-memory bug-memory rock-memory ghost-memory dragon-memory dark-memory steel-memory fairy-memory
douse-drive shock-drive burn-drive chill-drive'''.split()
OTHER = {'rare-candy': 'r'}


def rows(name):
    with open(os.path.join(CSV, name + '.csv'), encoding='utf-8') as f:
        yield from csv.DictReader(f)


ident = {r['id']: r['identifier'] for r in rows('items')}
ko = {ident[r['item_id']]: r['name'] for r in rows('item_names') if r['local_language_id'] == '3' and r['item_id'] in ident}
by_ko = {v: k for k, v in ko.items()}

html_path = os.path.join(GAME, 'index.html')
html = open(html_path, encoding='utf-8').read()
start = html.index('\nconst FORMS=') + len('\nconst FORMS=')
FORMS, _ = json.JSONDecoder().raw_decode(html, start)

items, missing = {}, []
for lst, c in ((BERRY, 'b'), (BATTLE, 'w'), (EXCL, 'x')):
    for k in lst:
        if k not in ko: missing.append(k); continue
        items[k] = {'n': ko[k], 'c': c}
for k, c in OTHER.items(): items[k] = {'n': ko[k], 'c': c}
# 메가스톤·원시회귀 구슬: FORMS의 item 이름(한국어)으로 찾고, FORMS 쪽 이름도 공식 이름으로 맞춘다
ALIAS = {'후딘나이트': 'alakazite', '플라엣테나이트': 'floettite', '마기아나나이트': 'magearnite'}
for f, F in FORMS.items():
    if F.get('k') != 'mega' or not F.get('item') or F['item'] == '운석': continue
    k = by_ko.get(F['item']) or ALIAS.get(F['item'])
    if not k: missing.append('mega:' + F['item']); continue
    F['item'] = ko[k]
    items[k] = {'n': ko[k], 'c': 'x', 'f': int(f)}
end = json.JSONDecoder().raw_decode(html, start)[1]
html = html[:start] + json.dumps(FORMS, ensure_ascii=False, separators=(',', ':')) + html[end:]

os.makedirs(os.path.join(GAME, 'it'), exist_ok=True)
# ITEMS에 없는 보스 보상(index.html의 band·soup·meteor) 아이콘. 다이스프는 가방 아이콘이 원래 없어서 재료인 다이버섯으로
SPECIAL = {'band': 'dynamax-band', 'soup': 'max-mushrooms', 'meteor': 'meteorite'}
noicon = []
for k in [*items, *SPECIAL]:
    path = os.path.join(GAME, 'it', k + '.png')
    if os.path.exists(path): continue
    try:
        with urllib.request.urlopen(ICON.format(SPECIAL.get(k, k)), timeout=60) as r: open(path, 'wb').write(r.read())
    except Exception:
        noicon.append(k)

line = 'const ITEMS=' + json.dumps(items, ensure_ascii=False, separators=(',', ':')) + ';'
if re.search(r'^const ITEMS=.*;$', html, re.M):
    html = re.sub(r'^const ITEMS=.*;$', lambda _: line, html, count=1, flags=re.M)
else:
    html = re.sub(r'^(const MVX=.*;)$', lambda m: m.group(1) + '\n' + line, html, count=1, flags=re.M)
open(html_path, 'w', encoding='utf-8', newline='\n').write(html)
print('items', len(items), 'missing', missing, 'no icon', noicon)
