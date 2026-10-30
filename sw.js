// 오프라인: 한 번 접속하면 인터넷 없이도 게임이 돌아가게 하는 서비스 워커.
// - index.html은 인터넷이 되면 늘 새로 받고(업데이트가 바로 보이게), 안 되면 저장해 둔 것을 쓴다.
// - 그림·도트 묶음 등 나머지 파일은 저장해 둔 것을 먼저 쓴다(주소의 ?v= 같은 뒷부분은 무시).
// - 페이지가 'fill'을 보내면 offline.json(파일 목록과 git 해시)을 보고 아직 없거나 바뀐 파일을 모두 받아 둔다(배틀 도트 약 88MB 포함).
//   해시를 저장해 두어서 다음에는 바뀐 파일만 다시 받는다. offline.json은 tools/build_offline.py가 만든다.
const CORE='fc-core-v1', ASSET='fc-asset-v1', FONT='fc-font-v1';
const SCOPE=new URL(self.registration.scope);
const at=p=>new URL(p,SCOPE).href;
const PAGE=at('index.html');
// index.html이 쓰는 글꼴 주소(바꾸면 여기도). 처음 접속 때는 서비스 워커가 아직 안 붙어 있어서 fill에서 따로 받아 둔다
const FONT_CSS='https://fonts.googleapis.com/css2?family=Do+Hyeon&family=Silkscreen:wght@400;700&display=swap';

self.addEventListener('install',e=>{
  e.waitUntil(caches.open(CORE).then(c=>c.addAll([PAGE,at('offline.json')])).then(()=>self.skipWaiting()));
});
self.addEventListener('activate',e=>{
  const keep=[CORE,ASSET,FONT];
  e.waitUntil(caches.keys().then(ks=>Promise.all(ks.filter(k=>k.startsWith('fc-')&&!keep.includes(k)).map(k=>caches.delete(k)))).then(()=>self.clients.claim()));
});

async function networkFirst(req,key){
  const c=await caches.open(CORE);
  try{ const r=await fetch(req); if(r.ok) await c.put(key,r.clone()); return r; }
  catch(e){ const hit=await c.match(key); if(hit) return hit; throw e; }
}
async function cacheFirst(name,req,key){
  const c=await caches.open(name), hit=await c.match(key);
  if(hit) return hit;
  const r=await fetch(req);
  if(r.ok&&(r.type==='basic'||r.type==='cors')) await c.put(key,r.clone());
  return r;
}

self.addEventListener('fetch',e=>{
  const req=e.request; if(req.method!=='GET') return;
  const u=new URL(req.url);
  if(u.origin===SCOPE.origin&&u.pathname.startsWith(SCOPE.pathname)){
    const p=u.pathname.slice(SCOPE.pathname.length);
    if(req.mode==='navigate'||p===''||p==='index.html') return e.respondWith(networkFirst(req,PAGE));
    if(p==='sw.js'||p==='offline.json') return;
    return e.respondWith(cacheFirst(ASSET,req,at(p)));
  }
  if(u.hostname==='fonts.googleapis.com'||u.hostname==='fonts.gstatic.com') e.respondWith(cacheFirst(FONT,req,req.url));
});

// 전부 받아 두기: 4개씩 나눠 받고, 진행 상황을 페이지에 알린다
let filling=null;
async function fill(){
  const list=(await (await fetch(at('offline.json'),{cache:'no-cache'})).json()).files;
  const c=await caches.open(ASSET), mr=await c.match('__meta'), meta=mr?await mr.json():{};
  const first=!mr, todo=[];
  for(const [p,h] of Object.entries(list)){
    if(meta[p]===h) continue;
    if(first&&await c.match(at(p))){ meta[p]=h; continue; }  // 처음 받을 때 방금 게임이 받아 둔 파일은 그대로 쓴다
    todo.push([p,h]);
  }
  const saveMeta=()=>c.put('__meta',new Response(JSON.stringify(meta)));
  const tell=async o=>{ for(const cl of await self.clients.matchAll()) cl.postMessage({t:'offline',...o}); };
  let done=0, fail=0;
  await tell({done,total:todo.length,fail});
  const run=async()=>{
    while(todo.length){
      const [p,h]=todo.shift();
      try{ const r=await fetch(at(p),{cache:'no-cache'}); if(!r.ok) throw 0; await c.put(at(p),r); meta[p]=h; }catch(_){ fail++; }
      done++; if(done%10===0){ await saveMeta(); await tell({done,total:done+todo.length,fail}); }
    }
  };
  const total=todo.length;
  await Promise.all([run(),run(),run(),run()]);
  try{  // 글꼴: CSS와 그 안의 글꼴 파일들
    const fc=await caches.open(FONT), css=await fetch(FONT_CSS); await fc.put(FONT_CSS,css.clone());
    for(const m of (await css.text()).matchAll(/url\((https:[^)]+)\)/g)) if(!await fc.match(m[1])){ const r=await fetch(m[1]); if(r.ok) await fc.put(m[1],r); }
  }catch(_){}
  await saveMeta(); await tell({done,total,fail,end:true});
}
self.addEventListener('message',e=>{
  if(e.data==='fill'&&!filling) filling=fill().catch(()=>{}).finally(()=>{ filling=null; });
});
