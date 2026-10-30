// 멀티플레이 방 서버 (Cloudflare Worker + Durable Object)
// 방 코드 하나 = Room 객체 하나. 서버는 게임 규칙을 모르고 메시지만 전달한다.
// 게임 진행(맵·야생 포켓몬·회복약)은 방장 브라우저가 맡고, 방장이 나가면 가장 먼저 들어온 사람이 넘겨받는다.
const MAX_PLAYERS = 4;
const MAX_MSG = 64 * 1024;
const IDLE_MS = 90 * 1000;  // 이만큼 아무 메시지도 없으면 끊긴 연결로 보고 뺀다 (close가 안 오는 경우)

export class Room {
  constructor(state, env) {
    this.state = state;
    this.peers = new Map();  // id -> {ws, name, sid, seen}
    this.host = null;
    this.swept = 0;
  }

  async fetch(req) {
    if (req.headers.get('Upgrade') !== 'websocket') return new Response('websocket only', { status: 426 });
    const q = new URL(req.url).searchParams;
    const sid = (q.get('sid') || '').slice(0, 32);
    // 같은 사람(같은 탭)이 다시 들어오면 남아 있던 옛 연결을 먼저 뺀다
    if (sid) for (const [oid, p] of this.peers) if (p.sid === sid) this.drop(oid, 4002, 'replaced');
    this.sweep(true);
    if (this.peers.size >= MAX_PLAYERS) return new Response('room full', { status: 403 });
    const [client, ws] = Object.values(new WebSocketPair());
    ws.accept();
    const id = crypto.randomUUID().slice(0, 8);
    const name = (q.get('name') || '트레이너').slice(0, 12);
    this.peers.set(id, { ws, name, sid, seen: Date.now() });
    if (!this.host) this.host = id;
    this.send(ws, { t: 'hello', id, host: this.host, peers: this.list() });
    this.broadcast({ t: 'join', id, name, host: this.host, peers: this.list() }, id);
    ws.addEventListener('message', ev => this.onMessage(id, ev.data));
    const bye = () => this.leave(id);
    ws.addEventListener('close', bye);
    ws.addEventListener('error', bye);
    return new Response(null, { status: 101, webSocket: client });
  }

  list() { return [...this.peers].map(([id, p]) => ({ id, name: p.name })); }
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

  onMessage(from, data) {
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
    // 이름 바꾸기: 목록의 이름도 바꿔서 나중에 들어온 사람에게도 새 이름
    if (m.t === 'rename') {
      me.name = String(m.name || '').slice(0, 12) || me.name;
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

export default {
  async fetch(req, env) {
    const m = new URL(req.url).pathname.match(/^\/room\/([A-Z0-9]{4,8})$/);
    if (!m) return new Response('pokemon-new-companion room server');
    return env.ROOMS.get(env.ROOMS.idFromName(m[1])).fetch(req);
  },
};
