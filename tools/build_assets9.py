import io, os, re, sys, json, base64
from collections import Counter, defaultdict
from multiprocessing import Pool
import numpy as np
from PIL import Image, ImageSequence, ImageOps, ImageFile
ImageFile.LOAD_TRUNCATED_IMAGES = True

R, OUT = sys.argv[1], sys.argv[2]   # R=/root/all
N, CH = 1025, 16
os.makedirs(OUT + '/bt', exist_ok=True); os.makedirs(OUT + '/ic', exist_ok=True); os.makedirs(OUT + '/wk', exist_ok=True)

def frames_of(path):
    im = Image.open(path); fr, du = [], []
    for f in ImageSequence.Iterator(im):
        fr.append(f.convert('RGBA')); du.append(max(20, f.info.get('duration', 100) or 100))
    return fr, du

def static(path, mirror=False):
    im = Image.open(path).convert('RGBA')
    if mirror: im = ImageOps.mirror(im)
    return [im], [1000]

def color_map(nf, sf):
    votes = defaultdict(Counter)
    for a, b in zip(nf, sf):
        if a.size != b.size: continue
        A = np.asarray(a).reshape(-1, 4); B = np.asarray(b).reshape(-1, 4)
        m = (A[:, 3] > 0) & (B[:, 3] > 0)
        if not m.any(): continue
        ka = (A[m, 0].astype(np.int64) << 16) | (A[m, 1].astype(np.int64) << 8) | A[m, 2]
        kb = (B[m, 0].astype(np.int64) << 16) | (B[m, 1].astype(np.int64) << 8) | B[m, 2]
        pairs, cnt = np.unique(np.stack([ka, kb], 1), axis=0, return_counts=True)
        for (x, y), c in zip(pairs, cnt): votes[int(x)][int(y)] += int(c)
    out = {}
    for x, c in votes.items():
        y = c.most_common(1)[0][0]
        if y != x: out[x] = y
    return out

def palettize(arr):
    flat = arr.reshape(-1, 4); op = flat[:, 3] > 0
    keys = (flat[:, 0].astype(np.int64) << 16) | (flat[:, 1].astype(np.int64) << 8) | flat[:, 2]
    uk = np.unique(keys[op])
    if len(uk) <= 255:
        idx = (np.searchsorted(uk, keys) + 1).astype(np.uint8)
        pal = np.stack([(uk >> 16) & 255, (uk >> 8) & 255, uk & 255], 1)
    else:
        rgb = Image.fromarray(arr[:, :, :3].copy(), 'RGB')
        q = rgb.quantize(colors=255, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE)
        idx = (np.asarray(q).reshape(-1).astype(np.int32) + 1).astype(np.uint8)
        pl = q.getpalette()[:255 * 3]; pal = np.array(pl + [0] * (255 * 3 - len(pl))).reshape(-1, 3)
    idx[~op] = 0
    return idx.reshape(arr.shape[:2]), pal

def build(nf, du, sf, smap):
    sel, D = [], []
    for k, f in enumerate(nf):
        if sel and f.tobytes() == nf[sel[-1]].tobytes(): D[-1] += du[k]
        else: sel.append(k); D.append(du[k])
    if len(sel) > 16:  # 프레임 절반만 (용량)
        sel = sel[::2]; D = [sum(D[j:j + 2]) for j in range(0, len(D), 2)]
    bb = None
    for k in sel:
        b = nf[k].getbbox()
        if b: bb = b if bb is None else (min(bb[0], b[0]), min(bb[1], b[1]), max(bb[2], b[2]), max(bb[3], b[3]))
    if bb is None: bb = (0, 0, 1, 1)
    w, h = bb[2] - bb[0], bb[3] - bb[1]; n = len(sel); cols = min(8, n); rows = (n + cols - 1) // cols
    aligned = sf is not None and len(sf) == len(nf) and sf[0].size == nf[0].size
    A = Image.new('RGBA', (w * cols, h * rows), (0, 0, 0, 0)); S = Image.new('RGBA', A.size, (0, 0, 0, 0))
    for j, k in enumerate(sel):
        pos = ((j % cols) * w, (j // cols) * h)
        A.paste(nf[k].crop(bb), pos)
        if aligned: S.paste(sf[k].crop(bb), pos)
    arr = np.asarray(A).copy(); arr[:, :, 3] = np.where(arr[:, :, 3] >= 128, 255, 0)
    P, pal = palettize(arr)
    smp = {}
    if aligned:
        sa = np.asarray(S)
        for p in range(1, len(pal) + 1):
            m = (P == p) & (sa[:, :, 3] > 0)
            if m.any():
                px = sa[m][:, :3].astype(np.int64); k = (px[:, 0] << 16) | (px[:, 1] << 8) | px[:, 2]
                v, c = np.unique(k, return_counts=True); smp[p] = int(v[c.argmax()])
    if smap:
        ks = np.array(list(smap.keys())); kr = np.stack([(ks >> 16) & 255, (ks >> 8) & 255, ks & 255], 1)
        for p in range(1, len(pal) + 1):
            if p in smp: continue
            c = pal[p - 1]; d = ((kr - c) ** 2).sum(1); j = d.argmin()
            if d[j] < 900: smp[p] = smap[int(ks[j])]
    pairs = []
    for p, sc in smp.items():
        c = pal[p - 1]; nc = (int(c[0]) << 16) | (int(c[1]) << 8) | int(c[2])
        if nc != sc: pairs.append(f'{nc:06x}{sc:06x}')
    im = Image.fromarray(P, 'P'); flatp = [0, 0, 0] + [int(v) for c in pal for v in c]
    im.putpalette(flatp + [0] * (768 - len(flatp)))
    buf = io.BytesIO(); im.save(buf, 'PNG', optimize=True, transparency=0)
    d = D[0] if len(set(D)) == 1 else D
    return {'p': base64.b64encode(buf.getvalue()).decode(), 'w': w, 'h': h, 'c': cols, 'n': n, 'd': d, 's': ','.join(pairs)}

def matched_map(nf, sf, thr=0.97):
    # 이로치 GIF는 애니메이션 시작 프레임이 다를 수 있어서, 모양이 똑같은 프레임끼리 짝지어 색을 비교
    sm = [np.asarray(f)[:, :, 3] > 127 for f in sf]
    pairs = []
    for k in sorted(set(int(x) for x in np.linspace(0, len(nf) - 1, min(10, len(nf))))):
        a = np.asarray(nf[k]); ma = a[:, :, 3] > 127
        best, bj = 0, -1
        for j, mb in enumerate(sm):
            if mb.shape != ma.shape: continue
            iou = (ma & mb).sum() / max(1, (ma | mb).sum())
            if iou > best: best, bj = iou, j
        if best >= thr: pairs.append((nf[k], sf[bj]))
    if not pairs: return {}
    return color_map([p[0] for p in pairs], [p[1] for p in pairs])

def _hist(cols):
    q = (cols // 32).astype(np.int64); h = np.bincount(q[:, 0] * 64 + q[:, 1] * 8 + q[:, 2], minlength=512).astype(float)
    return h / max(1, h.sum())
def _cols(frames):
    out = []
    for f in frames[::max(1, len(frames) // 10)][:10]:
        a = np.asarray(f).reshape(-1, 4); out.append(a[a[:, 3] > 127][:, :3])
    return np.concatenate(out) if out else np.zeros((0, 3), np.uint8)
def score_map(nf, sf, mp):
    nc = _cols(nf).astype(np.int64)
    if len(nc) == 0: return 9
    if mp:
        ks = np.array(list(mp.keys()), np.int64); vs = np.array(list(mp.values()), np.int64)
        keys = (nc[:, 0] << 16) | (nc[:, 1] << 8) | nc[:, 2]
        order = np.argsort(ks); ks, vs = ks[order], vs[order]
        pos = np.clip(np.searchsorted(ks, keys), 0, len(ks) - 1); hit = ks[pos] == keys
        keys = np.where(hit, vs[pos], keys); nc = np.stack([(keys >> 16) & 255, (keys >> 8) & 255, keys & 255], 1)
    return np.abs(_hist(nc) - _hist(_cols(sf).astype(np.int64))).sum()
def nearest_fill(mp, src, nf):
    # src 맵에서 가까운 색으로 mp에 없는 색 채우기
    if not src: return mp
    ks = np.array(list(src.keys()), np.int64); kr = np.stack([(ks >> 16) & 255, (ks >> 8) & 255, ks & 255], 1)
    out = dict(mp)
    for c in np.unique(_cols(nf), axis=0):
        k = (int(c[0]) << 16) | (int(c[1]) << 8) | int(c[2])
        if k in out: continue
        d = ((kr - c.astype(np.int64)) ** 2).sum(1); j = d.argmin()
        if d[j] < 900: out[k] = src[int(ks[j])]
    return out

def one(i):
    res = {}; front_map = {}
    for side in 'fb':
        g, gs = f'{R}/sd/{side}/{i}.gif', f'{R}/sd/{side}s/{i}.gif'
        nf = sf = None
        if os.path.exists(g):
            try:
                nf, du = frames_of(g)
                sf = frames_of(gs)[0] if os.path.exists(gs) else None
            except Exception:
                nf = None
        if nf is None:
            nf, du = static(f'{R}/st/f/{i}.png', side == 'b')
            sf = static(f'{R}/st/fs/{i}.png', side == 'b')[0]
        stat = color_map(static(f'{R}/st/f/{i}.png', side == 'b')[0], static(f'{R}/st/fs/{i}.png', side == 'b')[0])
        cands = [stat, nearest_fill({}, stat, nf)]
        if sf is not None:
            m1 = matched_map(nf, sf); m2 = matched_map(nf, sf, 0.85)
            cands += [m1, m2, nearest_fill(m1, stat, nf)]
            if front_map: cands += [nearest_fill(m1, front_map, nf), nearest_fill({}, front_map, nf)]
            smap = min(cands, key=lambda mp: score_map(nf, sf, mp))
        else:
            smap = cands[1]
        if side == 'f': front_map = smap
        sf = None
        res[side] = build(nf, du, sf, smap)
    return i, res

if __name__ == '__main__':
    with Pool(os.cpu_count()) as pool:
        allr = dict(pool.map(one, range(1, N + 1), chunksize=8))
    tot = 0
    for side in 'fb':
        for k in range((N + CH - 1) // CH):
            d = {str(i): allr[i][side] for i in range(k * CH + 1, min(N, k * CH + CH) + 1)}
            p = f'{OUT}/bt/{side}{k}.json'
            json.dump(d, open(p, 'w'), separators=(',', ':')); tot += os.path.getsize(p)
    print('battle bundles', tot, 'files', len(os.listdir(OUT + '/bt')))
    # 아이콘 시트 (256마리씩)
    for kind, src in (('f', 'st/f'), ('s', 'st/fs')):
        for k in range((N + 255) // 256):
            sh = Image.new('RGBA', (1536, 1536), (0, 0, 0, 0))
            for i in range(k * 256 + 1, min(N, k * 256 + 256) + 1):
                j = (i - 1) % 256
                sh.paste(Image.open(f'{R}/{src}/{i}.png').convert('RGBA'), ((j % 16) * 96, (j // 16) * 96))
            sh.save(f'{OUT}/ic/{kind}{k}.png', optimize=True)
    print('icons', sum(os.path.getsize(f'{OUT}/ic/' + f) for f in os.listdir(OUT + '/ic')))
