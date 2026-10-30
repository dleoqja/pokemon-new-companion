# 작은 숲의 다이맥스 굴 그림
#   map/den.png  (72×64, 3×2칸) 바위로 둘러싼 둥근 구덩이
#   map/gden.png (96×64, 4×2칸) 거다이맥스 굴: 검붉은 바위·붉게 갈라진 틈·뒤쪽에 솟은 붉은 결정. 더 크고 어둡다
# 분홍/붉은 빛·빛기둥은 게임이 캔버스에 따로 그린다(굴을 비우면 사라지게)
import math, random
from PIL import Image


def make(path, W, cx, cy, rx, ry, hx, hy, nrocks, dark):
    random.seed(7)
    H = 64
    im = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    px = im.load()

    def put(x, y, c):
        if 0 <= x < W and 0 <= y < H: px[x, y] = c

    # 거다이맥스 굴: 바위 테 뒤쪽에 솟은 붉은 결정 (바위보다 먼저 그려서 바위 뒤에 선다)
    if dark:
        for i in range(8):
            a = math.pi + (i + .5) / 8 * math.pi + random.uniform(-.1, .1)
            bx = cx + math.cos(a) * (rx - 7)
            by = cy + math.sin(a) * (ry - 4)
            h = random.randint(16, 27) * (1.15 - abs(math.cos(a)) * .45)
            w = random.uniform(4.2, 6)
            lean = math.cos(a) * 4
            for y in range(int(by - h), int(by) + 1):
                t = (by - y) / h          # 0(밑)~1(끝)
                half = w * (1 - t)
                xm = bx + lean * t
                for x in range(int(xm - half - 1), int(xm + half + 2)):
                    if abs(x - xm) > half: continue
                    e = abs(x - xm) / max(half, .01)
                    if e > .7: c = (60, 0, 18, 255)
                    elif x < xm: c = (255, 70 + int(60 * t), 110, 255)
                    else: c = (178, 16, 52, 255)
                    put(x, y, c)
    # 바닥 흙 (바위 테 안쪽)
    for y in range(H):
        for x in range(W):
            d = ((x - cx) / rx) ** 2 + ((y - cy) / ry) ** 2
            if d <= 1:
                n = random.randint(-4, 4)
                put(x, y, (58 + n, 34 + n, 42 + n, 255) if dark else (104 + n, 84 + n, 70 + n, 255))
    # 구멍: 가장자리는 어둡고 안쪽은 더 어둡게
    for y in range(H):
        for x in range(W):
            d = ((x - cx) / hx) ** 2 + ((y - (cy - 1)) / hy) ** 2
            if d <= 1:
                k = 1 - d
                if dark: put(x, y, (int(30 - 22 * k), int(6 - 6 * k), int(14 - 12 * k), 255))
                else: put(x, y, (int(52 - 28 * k), int(36 - 22 * k), int(48 - 22 * k), 255))
    # 구멍 아래쪽 벽
    for x in range(cx - hx, cx + hx + 1):
        t = (x - cx) / hx
        if abs(t) >= 1: continue
        yb = int(round(cy - 1 + hy * math.sqrt(1 - t * t)))
        for k in range(2):
            if dark: put(x, yb - k, (150, 20, 50, 255) if k == 0 else (70, 10, 26, 255))
            else: put(x, yb - k, (130, 104, 86, 255) if k == 0 else (92, 70, 62, 255))
    # 바위: 테 둘레에 크고 작은 돌 (뒤쪽이 작고 앞쪽이 크다)
    rocks = []
    for i in range(nrocks):
        a = i / nrocks * 2 * math.pi + random.uniform(-.08, .08)
        x = cx + math.cos(a) * (rx - 5)
        y = cy + math.sin(a) * (ry - 3)
        s = 4 + (math.sin(a) + 1) * 2.2 + random.uniform(-.6, 1) + (1 if dark else 0)
        rocks.append((y, x, s))
    rocks.sort()
    for y0, x0, s in rocks:
        sw, sh = s, s * .75
        for y in range(int(y0 - sh - 1), int(y0 + sh + 2)):
            for x in range(int(x0 - sw - 1), int(x0 + sw + 2)):
                d = ((x - x0) / sw) ** 2 + ((y - y0) / sh) ** 2
                if d > 1: continue
                l = -((x - x0) / sw) * .5 - ((y - y0) / sh) * .8   # 위쪽 왼편이 밝다
                if dark:
                    v = int(62 + 26 * l + random.randint(-4, 4))
                    c = (v + 8, v - 14, v - 8, 255)
                    if d > .72: c = (20, 6, 12, 255)
                else:
                    v = int(118 + 34 * l + random.randint(-5, 5))
                    c = (v, v - 6, v + 4, 255)
                    if d > .72: c = (58, 50, 60, 255)
                put(x, y, c)
        # 붉게 빛나는 틈 (다이맥스 힘이 스민 돌). 거다이맥스 굴은 모든 돌이 갈라져 있다
        if dark:
            x1, y1 = int(x0 - sw * .35), int(y0 - sh * .45)
            for k in range(max(3, int(sw * .8))):
                put(x1 + k, y1 + k * 2 // 3, (255, 60 + k * 20, 90, 255))
        elif random.random() < .45:
            put(int(x0), int(y0 - sh * .2), (255, 96, 150, 255))
            put(int(x0) + 1, int(y0 - sh * .2), (210, 60, 120, 255))
    im.save(path)
    print(path)


make('map/den.png', 72, 36, 38, 31, 19, 18, 10, 17, False)
make('map/gden.png', 96, 48, 40, 42, 20, 26, 11, 22, True)
