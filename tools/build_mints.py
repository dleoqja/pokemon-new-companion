# 민트 아이콘 it/mint-{성격 번호}.png (원작처럼 21종: 변화 없는 성격은 성실민트만) (64×64, 다른 도구 아이콘과 같은 크기)
# 공식 가방 아이콘을 받을 수 없어서 직접 그린 잎 세 장짜리 민트. 색은 올라가는 능력치마다:
#   공격 빨강 · 방어 주황 · 스피드 분홍 · 특수공격 파랑 · 특수방어 초록 · 변화 없음(성실 등) 흰색
# 성격 번호 i는 index.html의 NAT와 같다: NAT_K[i//5]가 오르고 NAT_K[i%5]가 내려간다 (NAT_K = atk, def, spe, spa, spd)
import math
from PIL import Image

COL = {'atk': (232, 80, 74), 'def': (232, 150, 48), 'spe': (226, 96, 176), 'spa': (74, 127, 224), 'spd': (76, 184, 96), 'none': (214, 222, 214)}
NAT_K = ['atk', 'def', 'spe', 'spa', 'spd']


def shade(c, k):
    return tuple(max(0, min(255, int(v * k))) for v in c) + (255,)


def leaf(px, cx, cy, ang, L, W, col):
    # 끝이 뾰족한 잎: 축을 따라 폭이 sin으로 변한다. 위쪽 절반은 밝게, 가운데 잎맥은 어둡게
    ca, sa = math.cos(ang), math.sin(ang)
    for y in range(64):
        for x in range(64):
            dx, dy = x + .5 - cx, y + .5 - cy
            u = dx * ca + dy * sa          # 축 방향 (0~L)
            v = -dx * sa + dy * ca         # 옆 방향
            if u < 0 or u > L: continue
            w = W * math.sin(math.pi * u / L) ** .8
            if abs(v) > w: continue
            e = abs(v) / max(w, .01)
            if e > .82: c = shade(col, .45)
            elif abs(v) < .9 and u > L * .12: c = shade(col, .62)
            elif v < 0: c = shade(col, 1.18)
            else: c = shade(col, .92)
            px[x, y] = c


for i in range(25):
    up, dn = NAT_K[i // 5], NAT_K[i % 5]
    if up == dn and i != 12: continue  # 변화 없는 성격의 민트는 성실민트(12)만
    col = COL['none' if up == dn else up]
    im = Image.new('RGBA', (64, 64), (0, 0, 0, 0))
    px = im.load()
    # 줄기
    for y in range(40, 56):
        for x in (31, 32):
            px[x, y] = (70, 110, 60, 255)
    leaf(px, 32, 44, math.radians(-150), 24, 8, col)
    leaf(px, 32, 44, math.radians(-30), 24, 8, col)
    leaf(px, 32, 46, math.radians(-90), 30, 9, col)
    # 반짝임
    for (x, y) in [(27, 20), (28, 19), (28, 21), (29, 20)]:
        px[x, y] = (255, 255, 255, 230)
    im.save(f'it/mint-{i}.png')
print('it/mint-*.png (21개)')
