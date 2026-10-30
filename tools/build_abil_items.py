# 특성캡슐·특성패치 아이콘 it/ability-capsule.png, it/ability-patch.png (64×64, 다른 도구 아이콘과 같은 크기)
# 공식 가방 아이콘을 받을 수 없어서 직접 그림: 캡슐은 보라·흰 알약, 패치는 바느질 테두리가 있는 천 조각에 금빛 별
import math
from PIL import Image

OUT = (30, 24, 40, 255)


def capsule():
    im = Image.new('RGBA', (64, 64), (0, 0, 0, 0)); px = im.load()
    cx, cy, L, R = 32, 32, 20, 10            # 가운데, 반 길이, 반지름
    a = math.radians(-35); ca, sa = math.cos(a), math.sin(a)
    for y in range(64):
        for x in range(64):
            u = (x + .5 - cx) * ca + (y + .5 - cy) * sa      # 알약 축 방향
            v = -(x + .5 - cx) * sa + (y + .5 - cy) * ca
            d = math.hypot(max(abs(u) - L, 0), v)
            if d > R + 1.5: continue
            if d > R: px[x, y] = OUT; continue
            light = 1.15 - .45 * (v + R) / (2 * R)          # 위쪽이 밝다
            base = (138, 92, 220) if u < 0 else (240, 236, 246)
            c = tuple(max(0, min(255, int(ch * light))) for ch in base)
            if abs(u) < .9: c = (90, 60, 140)                # 이음매
            px[x, y] = c + (255,)
    for (x, y) in [(22, 24), (23, 23), (24, 22), (21, 25)]: px[x, y] = (255, 255, 255, 255)   # 반짝임
    im.save('it/ability-capsule.png')


def patch():
    im = Image.new('RGBA', (64, 64), (0, 0, 0, 0)); px = im.load()
    x0, y0, x1, y1 = 12, 12, 52, 52
    for y in range(y0 - 1, y1 + 2):
        for x in range(x0 - 1, x1 + 2):
            if x in (x0 - 1, x1 + 1) or y in (y0 - 1, y1 + 1): px[x, y] = OUT; continue
            k = 1.1 - .3 * (y - y0) / (y1 - y0)
            px[x, y] = tuple(int(c * k) for c in (226, 196, 150)) + (255,)
    # 바느질 점선 테두리
    for t in range(x0 + 3, x1 - 2, 3):
        for (x, y) in [(t, y0 + 3), (t, y1 - 3), (x0 + 3, t), (x1 - 3, t)]: px[x, y] = (150, 104, 60, 255)
    # 가운데 금빛 별
    cx, cy = 32, 33
    pts = [(cx + (11 if i % 2 == 0 else 4.6) * math.cos(-math.pi / 2 + i * math.pi / 5), cy + (11 if i % 2 == 0 else 4.6) * math.sin(-math.pi / 2 + i * math.pi / 5)) for i in range(10)]

    def inside(x, y):
        c = False
        for i in range(10):
            (ax, ay), (bx, by) = pts[i], pts[(i + 1) % 10]
            if (ay > y) != (by > y) and x < (bx - ax) * (y - ay) / (by - ay) + ax: c = not c
        return c
    for y in range(64):
        for x in range(64):
            if inside(x + .5, y + .5):
                px[x, y] = (255, 214, 72, 255) if y < cy else (232, 170, 40, 255)
            elif any(inside(x + .5 + dx, y + .5 + dy) for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))):
                px[x, y] = (120, 80, 20, 255)
    im.save('it/ability-patch.png')


capsule(); patch()
print('it/ability-capsule.png, it/ability-patch.png')
