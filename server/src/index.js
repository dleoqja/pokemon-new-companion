// 멀티플레이 방 서버 (Cloudflare Worker + Durable Object)
// 방 코드 하나 = Room 객체 하나. 서버는 게임 규칙을 모르고 메시지만 전달한다.
// 게임 진행(맵·야생 포켓몬·회복약)은 방장 브라우저가 맡고, 방장이 나가면 가장 먼저 들어온 사람이 넘겨받는다.
// 같은 Worker에 계정 서버(Accounts, /api/...)도 있다.
const MAX_PLAYERS = 4;
const MAX_MSG = 64 * 1024;
const IDLE_MS = 90 * 1000;  // 이만큼 아무 메시지도 없으면 끊긴 연결로 보고 뺀다 (close가 안 오는 경우)
const acctStub = env => env.ACCOUNTS.get(env.ACCOUNTS.idFromName('main'));

export class Room {
  constructor(state, env) {
    this.state = state;
    this.env = env;
    this.peers = new Map();  // id -> {ws, name, sid, seen, acct}
    this.host = null;
    this.swept = 0;
  }

  async fetch(req) {
    if (req.headers.get('Upgrade') !== 'websocket') return new Response('websocket only', { status: 426 });
    const q = new URL(req.url).searchParams;
    const sid = (q.get('sid') || '').slice(0, 32);
    // 로그인한 사람(tk)은 이름이 계정 닉네임이 된다(서버가 확인). 손님이 계정 닉네임과 같은 이름을 쓰면 뒤에 '(손님)'을 붙인다
    let name = (q.get('name') || '트레이너').slice(0, 12), acct = false;
    const tk = q.get('tk') || '';
    try {
      const j = tk ? await this.acctMe(tk) : await (await acctStub(this.env).fetch(new Request('https://acct/api/exists?id=' + encodeURIComponent(name)))).json();
      if (tk && j && j.id) { name = j.nick; acct = true; }
      else if (!tk && j && j.exists) name = name.slice(0, 8) + '(손님)';
    } catch (_) {}
    // 같은 사람(같은 탭)이 다시 들어오면 남아 있던 옛 연결을 먼저 뺀다
    if (sid) for (const [oid, p] of this.peers) if (p.sid === sid) this.drop(oid, 4002, 'replaced');
    this.sweep(true);
    if (this.peers.size >= MAX_PLAYERS) return new Response('room full', { status: 403 });
    const [client, ws] = Object.values(new WebSocketPair());
    ws.accept();
    const id = crypto.randomUUID().slice(0, 8);
    this.peers.set(id, { ws, name, sid, seen: Date.now(), acct, tk: acct ? tk : '' });
    if (!this.host) this.host = id;
    this.send(ws, { t: 'hello', id, name, host: this.host, peers: this.list() });
    this.broadcast({ t: 'join', id, name, host: this.host, peers: this.list() }, id);
    ws.addEventListener('message', ev => this.onMessage(id, ev.data));
    const bye = () => this.leave(id);
    ws.addEventListener('close', bye);
    ws.addEventListener('error', bye);
    return new Response(null, { status: 101, webSocket: client });
  }

  async acctMe(tk) {
    const r = await acctStub(this.env).fetch(new Request('https://acct/api/me', { headers: { Authorization: 'Bearer ' + tk } }));
    return r.ok ? r.json() : null;
  }
  list() { return [...this.peers].map(([id, p]) => ({ id, name: p.name, acct: p.acct || undefined })); }
  send(ws, msg) { try { ws.send(typeof msg === 'string' ? msg : JSON.stringify(msg)); } catch (_) {} }
  broadcast(msg, except) {
    const s = JSON.stringify(msg);
    for (const [id, p] of this.peers) if (id !== except) this.send(p.ws, s);
  }

  // 오래 조용한 연결 정리
  sweep(now) {
    const t = Date.now();
    if (!now && t - this.swept < 5000) return;
    this.swept = t;
    for (const [id, p] of this.peers) if (t - p.seen > IDLE_MS) this.drop(id, 4003, 'idle');
  }
  drop(id, code, why) {
    const p = this.peers.get(id);
    if (!p) return;
    try { p.ws.close(code, why); } catch (_) {}
    this.leave(id);
  }

  async onMessage(from, data) {
    const me = this.peers.get(from);
    if (!me) return;
    me.seen = Date.now();
    this.sweep();
    if (typeof data !== 'string' || data.length > MAX_MSG) return;
    let m;
    try { m = JSON.parse(data); } catch (_) { return; }
    if (!m || typeof m !== 'object' || typeof m.t !== 'string') return;
    if (m.t === 'ping') return;  // 살아 있다는 표시만
    m.from = from;
    // 방장만 다른 사람을 내보낼 수 있다
    if (m.t === 'kick') {
      const p = this.peers.get(m.to);
      if (from !== this.host || !p || m.to === from) return;
      this.send(p.ws, { t: 'kicked' });
      this.drop(m.to, 4001, 'kicked');
      return;
    }
    // 이름 바꾸기: 목록의 이름도 바꿔서 나중에 들어온 사람에게도 새 이름 (계정은 서버의 닉네임으로만)
    if (m.t === 'rename') {
      if (me.acct) { try { const j = await this.acctMe(me.tk); if (!j || !j.nick) return; me.name = j.nick; } catch (_) { return; } }
      else me.name = String(m.name || '').slice(0, 12) || me.name;
      this.broadcast({ t: 'rename', id: from, name: me.name, peers: this.list() }, from);
      return;
    }
    // to가 있으면 그 사람에게만, 없으면 보낸 사람 빼고 모두에게
    if (m.to) { const p = this.peers.get(m.to); if (p) this.send(p.ws, m); }
    else this.broadcast(m, from);
  }

  leave(id) {
    if (!this.peers.delete(id)) return;
    if (this.host === id) this.host = this.peers.keys().next().value || null;  // Map은 들어온 순서를 기억한다
    this.broadcast({ t: 'left', id, host: this.host, peers: this.list() });
  }
}

// ================= 계정 (Durable Object 하나 'main', SQLite) =================
// 아이디·비밀번호 로그인, 저장 칸 5개, 최고 기록·클리어 횟수 랭킹.
// 비밀번호는 브라우저가 PBKDF2로 늘린 값(key, 64자 hex)만 받고, 여기서 무작위 salt와 함께 SHA-256을 한 번 더 해 저장한다(원래 비밀번호는 서버에 오지 않는다).
// 로그인하면 무작위 토큰을 주고, 서버는 토큰의 SHA-256만 기억한다(30일, 쓰면 연장).
const ID_RE = /^[a-z0-9_]{3,12}$/, KEY_RE = /^[0-9a-f]{64}$/;
const SESSION_MS = 30 * 864e5, LOCK_N = 10, LOCK_MS = 15 * 60e3, SIGNUP_PER_HOUR = 5, MAX_SAVE = 256 * 1024, SLOTS = 5;
const hex = b => [...new Uint8Array(b)].map(x => x.toString(16).padStart(2, '0')).join('');
const sha = async s => hex(await crypto.subtle.digest('SHA-256', new TextEncoder().encode(s)));
const rand = n => hex(crypto.getRandomValues(new Uint8Array(n)));
const json = (o, status = 200) => new Response(JSON.stringify(o), { status, headers: { 'Content-Type': 'application/json' } });
// 닉네임: 앞뒤 공백·꺾쇠·따옴표·제어 문자를 빼고 1~8자
const cleanNick = s => String(s || '').replace(/[<>"&'`\u0000-\u001f\u007f]/g, '').replace(/\s+/g, ' ').trim().slice(0, 8);
const bearer = req => (req.headers.get('Authorization') || '').replace(/^Bearer /, '');

export class Accounts {
  constructor(state, env) {
    this.sql = state.storage.sql;
    this.sql.exec(`CREATE TABLE IF NOT EXISTS users(id TEXT PRIMARY KEY, salt TEXT, hash TEXT, created INTEGER, best INTEGER DEFAULT 0, best_t INTEGER DEFAULT 0, clears INTEGER DEFAULT 0);
      CREATE TABLE IF NOT EXISTS sessions(th TEXT PRIMARY KEY, id TEXT, exp INTEGER);
      CREATE TABLE IF NOT EXISTS saves(id TEXT, slot INTEGER, t INTEGER, data TEXT, PRIMARY KEY(id, slot));
      CREATE TABLE IF NOT EXISTS fails(id TEXT PRIMARY KEY, n INTEGER, until INTEGER);
      CREATE TABLE IF NOT EXISTS signups(ip TEXT, t INTEGER);`);
    // 닉네임(대소문자 무시하고 겹치지 않게). 예전 계정은 닉네임이 없으면 아이디를 쓴다
    // 기록 때의 파티: best_party(최고 층에 처음 왔을 때), clear_party(마지막 클리어)
    const cols = this.sql.exec('PRAGMA table_info(users)').toArray().map(c => c.name);
    for (const c of ['nick', 'best_party', 'clear_party']) if (!cols.includes(c)) this.sql.exec(`ALTER TABLE users ADD COLUMN ${c} TEXT`);
    this.sql.exec('CREATE UNIQUE INDEX IF NOT EXISTS users_nick ON users(nick COLLATE NOCASE)');
  }
  nickTaken(nick, except) { const u = this.row('SELECT id FROM users WHERE (nick = ? COLLATE NOCASE OR (nick IS NULL AND id = ?)) AND id != ?', nick, nick.toLowerCase(), except || ''); return !!u; }
  row(q, ...a) { return this.sql.exec(q, ...a).toArray()[0] || null; }
  async session(id) {
    const tk = rand(32), now = Date.now();
    this.sql.exec('DELETE FROM sessions WHERE exp < ?', now);
    this.sql.exec('INSERT INTO sessions VALUES (?, ?, ?)', await sha(tk), id, now + SESSION_MS);
    return tk;
  }
  async who(req) {
    const tk = bearer(req);
    if (!tk) return null;
    const th = await sha(tk), s = this.row('SELECT id, exp FROM sessions WHERE th = ?', th);
    if (!s || s.exp < Date.now()) return null;
    if (s.exp - Date.now() < SESSION_MS / 2) this.sql.exec('UPDATE sessions SET exp = ? WHERE th = ?', Date.now() + SESSION_MS, th);
    return s.id;
  }
  me(id) { const u = this.row('SELECT id, nick, best, clears FROM users WHERE id = ?', id); return u && { id: u.id, nick: u.nick || u.id, best: u.best, clears: u.clears }; }

  async fetch(req) {
    const url = new URL(req.url), path = url.pathname.replace(/^\/api\//, ''), M = req.method, now = Date.now();
    const body = M === 'POST' || M === 'PUT' ? await req.json().catch(() => ({})) : {};
    // 손님 이름이 계정 아이디와 겹치는지 (방 서버만 묻는다)
    if (path === 'exists') return json({ exists: this.nickTaken(url.searchParams.get('id') || '') });
    if (path === 'rank') {
      // 아이디는 밖으로 내보내지 않는다(로그인에만 쓴다). 랭킹·기록 보기는 닉네임으로
      const top = this.sql.exec('SELECT COALESCE(nick, id) AS nick, best, clears FROM users WHERE best > 0 ORDER BY best DESC, clears DESC, best_t ASC LIMIT 50').toArray();
      const id = await this.who(req);
      let mine = null;
      if (id) {
        const u = this.row('SELECT best, clears, best_t FROM users WHERE id = ?', id);
        if (u && u.best > 0) mine = { nick: this.me(id).nick, best: u.best, clears: u.clears, rank: 1 + this.row(
          'SELECT COUNT(*) AS n FROM users WHERE best > ? OR (best = ? AND (clears > ? OR (clears = ? AND best_t < ?)))', u.best, u.best, u.clears, u.clears, u.best_t).n };
      }
      return json({ top, mine });
    }
    // 랭킹에서 누른 사람: 닉네임·기록·기록 때의 파티
    if (path === 'user') {
      const n = url.searchParams.get('nick') || '';
      const u = this.row('SELECT COALESCE(nick, id) AS nick, best, clears, best_party, clear_party FROM users WHERE nick = ? COLLATE NOCASE OR (nick IS NULL AND id = ?)', n, n.toLowerCase());
      if (!u) return json({ err: 'nf' }, 404);
      const pj = s => { try { return s ? JSON.parse(s) : null; } catch (_) { return null; } };
      return json({ nick: u.nick, best: u.best, clears: u.clears, bestParty: pj(u.best_party), clearParty: pj(u.clear_party) });
    }
    if (path === 'signup' && M === 'POST') {
      const id = String(body.id || ''), key = String(body.key || ''), nick = cleanNick(body.nick), ip = req.headers.get('X-IP') || '';
      if (!ID_RE.test(id) || !KEY_RE.test(key) || !nick) return json({ err: 'bad' }, 400);
      if (this.row('SELECT 1 AS x FROM users WHERE id = ?', id)) return json({ err: 'taken' }, 409);
      if (this.nickTaken(nick)) return json({ err: 'nick' }, 409);
      this.sql.exec('DELETE FROM signups WHERE t < ?', now - 3600e3);
      if (ip && this.row('SELECT COUNT(*) AS n FROM signups WHERE ip = ?', ip).n >= SIGNUP_PER_HOUR) return json({ err: 'slow' }, 429);
      const salt = rand(16);
      this.sql.exec('INSERT INTO users(id, salt, hash, created, nick) VALUES (?, ?, ?, ?, ?)', id, salt, await sha(salt + key), now, nick);
      if (ip) this.sql.exec('INSERT INTO signups VALUES (?, ?)', ip, now);
      return json({ token: await this.session(id), ...this.me(id) });
    }
    if (path === 'login' && M === 'POST') {
      const id = String(body.id || ''), key = String(body.key || '');
      if (!ID_RE.test(id) || !KEY_RE.test(key)) return json({ err: 'wrong' }, 401);
      // 비밀번호를 10번 틀리면 15분 잠근다
      const f = this.row('SELECT n, until FROM fails WHERE id = ?', id);
      if (f && f.until > now) return json({ err: 'locked', wait: Math.ceil((f.until - now) / 60e3) }, 429);
      const u = this.row('SELECT salt, hash FROM users WHERE id = ?', id);
      if (!u || await sha(u.salt + key) !== u.hash) {
        const n = (f && !f.until ? f.n : 0) + 1;
        this.sql.exec('INSERT OR REPLACE INTO fails VALUES (?, ?, ?)', id, n >= LOCK_N ? 0 : n, n >= LOCK_N ? now + LOCK_MS : 0);
        return json({ err: 'wrong' }, 401);
      }
      this.sql.exec('DELETE FROM fails WHERE id = ?', id);
      return json({ token: await this.session(id), ...this.me(id) });
    }
    // 여기부터는 로그인해야 한다
    const id = await this.who(req);
    if (!id) return json({ err: 'auth' }, 401);
    if (path === 'me') return json(this.me(id));
    if (path === 'nick' && M === 'POST') {
      const nick = cleanNick(body.nick);
      if (!nick) return json({ err: 'bad' }, 400);
      if (this.nickTaken(nick, id)) return json({ err: 'nick' }, 409);
      this.sql.exec('UPDATE users SET nick = ? WHERE id = ?', nick, id);
      return json(this.me(id));
    }
    if (path === 'logout' && M === 'POST') {
      this.sql.exec('DELETE FROM sessions WHERE th = ?', await sha(bearer(req)));
      return json({ ok: true });
    }
    // 저장 칸: 시간(t)이 더 새로운 쪽이 이긴다. 지운 칸은 data 없이 시간만 남긴다(다른 기기의 옛 저장이 되살아나지 않게)
    if (path === 'saves' && M === 'GET') return json({ slots: this.sql.exec('SELECT slot, t, data FROM saves WHERE id = ?', id).toArray() });
    const sm = path.match(/^saves\/(\d)$/);
    if (sm && (M === 'PUT' || M === 'DELETE')) {
      const slot = +sm[1], t = Math.min(+(M === 'PUT' ? body.t : url.searchParams.get('t')) || 0, now + 60e3);
      if (slot >= SLOTS || !t) return json({ err: 'bad' }, 400);
      const data = M === 'PUT' ? String(body.data || '') : null;
      if (data !== null && (!data || data.length > MAX_SAVE)) return json({ err: 'size' }, 413);
      const cur = this.row('SELECT t FROM saves WHERE id = ? AND slot = ?', id, slot);
      if (cur && cur.t > t) return json({ err: 'newer', t: cur.t }, 409);
      this.sql.exec('INSERT OR REPLACE INTO saves VALUES (?, ?, ?, ?)', id, slot, t, data);
      return json({ ok: true });
    }
    // 기록: 최고 층은 더 높을 때만, 클리어는 한 판에 한 번(브라우저가 정해서 보낸다)
    if (path === 'record' && M === 'POST') {
      const fl = Math.min(Math.max(Math.floor(+body.best) || 0, 0), 999);
      const party = x => Array.isArray(x) && x.length && x.length <= 6 ? JSON.stringify(x).slice(0, 16384) : null;  // 너무 크면 버린다
      const bp = party(body.bestParty), cp = party(body.clearParty), ok = s => s && s.length < 16384;
      const u = this.row('SELECT best FROM users WHERE id = ?', id);
      if (u && fl > u.best) this.sql.exec('UPDATE users SET best = ?, best_t = ?, best_party = ? WHERE id = ?', fl, now, ok(bp) ? bp : null, id);
      if (body.clear) this.sql.exec('UPDATE users SET clears = clears + 1, clear_party = COALESCE(?, clear_party) WHERE id = ?', ok(cp) ? cp : null, id);
      return json(this.me(id));
    }
    return json({ err: 'nf' }, 404);
  }
}

// 게임 사이트에서만 계정 API를 부를 수 있다 (로컬 테스트 주소 포함)
const ORIGIN_OK = o => o === 'https://forest-companion.github.io' || /^http:\/\/(localhost|127\.0\.0\.1)(:\d+)?$/.test(o || '');
function cors(req, res) {
  const o = req.headers.get('Origin'), h = new Headers(res.headers);
  if (ORIGIN_OK(o)) { h.set('Access-Control-Allow-Origin', o); h.set('Vary', 'Origin'); }
  return new Response(res.body, { status: res.status, headers: h });
}

export default {
  async fetch(req, env) {
    const path = new URL(req.url).pathname;
    if (path.startsWith('/api/')) {
      if (req.method === 'OPTIONS') return cors(req, new Response(null, { status: 204, headers: {
        'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE', 'Access-Control-Allow-Headers': 'Content-Type, Authorization', 'Access-Control-Max-Age': '86400' } }));
      if (path === '/api/exists') return new Response('nf', { status: 404 });  // 방 서버 안에서만 쓴다
      const r = new Request(req);
      r.headers.set('X-IP', req.headers.get('CF-Connecting-IP') || '');
      return cors(req, await acctStub(env).fetch(r));
    }
    const m = path.match(/^\/room\/([A-Z0-9]{4,8})$/);
    if (!m) return new Response('pokemon-new-companion room server');
    return env.ROOMS.get(env.ROOMS.idFromName(m[1])).fetch(req);
  },
};
