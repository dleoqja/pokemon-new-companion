import re, sys, os, json
from PIL import Image

SRC, OUT, PREFIX = sys.argv[1], sys.argv[2], sys.argv[3]
CELL, NF, PER_ROW, PER_SHEET, N = 48, 4, 8, 128, 1025
DIRS = [0, 6, 2, 4]  # 아래, 왼쪽, 오른쪽, 위
os.makedirs(OUT, exist_ok=True)
have = []
for k in range((N + PER_SHEET - 1) // PER_SHEET):
    sheet = Image.new('RGBA', (PER_ROW * NF * CELL, (PER_SHEET // PER_ROW) * 4 * CELL), (0, 0, 0, 0))
    for i in range(k * PER_SHEET + 1, min(N, k * PER_SHEET + PER_SHEET) + 1):
        d = os.path.join(SRC, f'{i:04d}')
        try:
            xml = open(os.path.join(d, 'AnimData.xml'), encoding='utf-8').read()
            b = re.search(r'<Name>Walk</Name>(.*?)</Anim>', xml, re.S).group(1)
            fw = int(re.search(r'<FrameWidth>(\d+)', b).group(1)); fh = int(re.search(r'<FrameHeight>(\d+)', b).group(1))
            n = len(re.findall(r'<Duration>', b))
            im = Image.open(os.path.join(d, 'Walk-Anim.png')).convert('RGBA')
            if im.height < fh * 8: continue
        except Exception:
            continue
        frames = [[im.crop(((kk * n // NF) * fw, dr * fh, (kk * n // NF) * fw + fw, dr * fh + fh)) for kk in range(NF)] for dr in DIRS]
        l, t, r, btm = fw, fh, 0, 0
        for row in frames:
            for f in row:
                bb = f.getbbox()
                if bb: l, t, r, btm = min(l, bb[0]), min(t, bb[1]), max(r, bb[2]), max(btm, bb[3])
        if r <= l: continue
        cx = fw // 2; half = max(cx - l, r - cx); bw, bh = half * 2, btm - t
        s = min(1.0, CELL / max(bw, bh, 1))
        j = (i - 1) % PER_SHEET; bx, by = j % PER_ROW, j // PER_ROW
        for di, row in enumerate(frames):
            for kk, f in enumerate(row):
                c = f.crop((cx - half, t, cx + half, btm))
                if s < 1: c = c.resize((max(1, round(c.width * s)), max(1, round(c.height * s))), Image.NEAREST)
                sheet.paste(c, (bx * NF * CELL + kk * CELL + (CELL - c.width) // 2, (by * 4 + di) * CELL + (CELL - c.height)), c)
        have.append(i)
    sheet.save(os.path.join(OUT, f'{PREFIX}{k}.png'), optimize=True)
json.dump(have, open(os.path.join(OUT, f'{PREFIX}_have.json'), 'w'), separators=(',', ':'))
print(PREFIX, len(have), sum(os.path.getsize(os.path.join(OUT, f)) for f in os.listdir(OUT) if f.startswith(PREFIX) and f.endswith('.png')))
