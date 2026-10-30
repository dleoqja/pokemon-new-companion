import sys, os, json, importlib.util
sys.argv=['x','/root/all','build9']
spec=importlib.util.spec_from_file_location('b','build_assets9.py'); b=importlib.util.module_from_spec(spec); spec.loader.exec_module(b)
from multiprocessing import Pool
ids=[int(x) for x in open('build9/form_ids.txt').read().split()]
ok=[i for i in ids if os.path.exists(f'/root/all/st/f/{i}.png') or os.path.exists(f'/root/all/sd/f/{i}.gif')]
def safe(i):
    # 정지 도트가 없으면 애니메이션만, 둘 다 있으면 기존 방식
    if not os.path.exists(f'/root/all/st/f/{i}.png'):
        import shutil
        from PIL import Image
        im=Image.open(f'/root/all/sd/f/{i}.gif').convert('RGBA'); im.save(f'/root/all/st/f/{i}.png')
        if os.path.exists(f'/root/all/sd/fs/{i}.gif'): Image.open(f'/root/all/sd/fs/{i}.gif').convert('RGBA').save(f'/root/all/st/fs/{i}.png')
        else: im.save(f'/root/all/st/fs/{i}.png')
    if not os.path.exists(f'/root/all/st/fs/{i}.png'):
        import shutil; shutil.copy(f'/root/all/st/f/{i}.png', f'/root/all/st/fs/{i}.png')
    return b.one(i)
if __name__=='__main__':
    with Pool(os.cpu_count()) as p: res=dict(p.map(safe, ok, chunksize=4))
    idx={}; tot=0
    for j,i in enumerate(ok): idx[i]=j//16
    for side in 'fb':
        for k in range((len(ok)+15)//16):
            d={str(i):res[i][side] for i in ok if idx[i]==k}
            pth=f'build9/bt/x{side}{k}.json'; json.dump(d,open(pth,'w'),separators=(',',':')); tot+=os.path.getsize(pth)
    json.dump(idx,open('build9/form_idx.json','w'),separators=(',',':'))
    print('forms bundled',len(ok),'chunks',(len(ok)+15)//16,'bytes',tot)
