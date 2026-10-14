import json, os, sqlite3
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from datetime import datetime, timezone

DB = os.environ.get('DB_PATH','/data/tickets.db')
os.makedirs(os.path.dirname(DB), exist_ok=True)

def connect():
    c=sqlite3.connect(DB,timeout=10)
    c.execute('''CREATE TABLE IF NOT EXISTS tickets (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      request_id TEXT UNIQUE NOT NULL, customer TEXT NOT NULL, message TEXT NOT NULL,
      category TEXT NOT NULL, priority TEXT NOT NULL, status TEXT NOT NULL,
      needs_human_review INTEGER NOT NULL, summary TEXT NOT NULL, draft_reply TEXT NOT NULL,
      mode TEXT NOT NULL, created_at TEXT NOT NULL)''')
    return c
with connect() as c: pass

class Handler(BaseHTTPRequestHandler):
    def send(self,code,data):
        raw=json.dumps(data,ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header('Content-Type','application/json; charset=utf-8')
        self.send_header('Content-Length',str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)
    def do_GET(self):
        if self.path=='/health': return self.send(200,{'ok':True})
        if self.path.startswith('/tickets'):
            with connect() as c:
                c.row_factory=sqlite3.Row
                rows=c.execute('SELECT * FROM tickets ORDER BY id DESC LIMIT 100').fetchall()
            return self.send(200,{'tickets':[dict(r) for r in rows]})
        self.send(404,{'error':'not_found'})
    def do_POST(self):
        if self.path!='/tickets': return self.send(404,{'error':'not_found'})
        try:
            size=int(self.headers.get('Content-Length','0'))
            if not 0<size<=16384: return self.send(413,{'error':'invalid_body_size'})
            data=json.loads(self.rfile.read(size))
            required=['request_id','customer','message','category','priority','status','summary','draft_reply','mode']
            if any(not isinstance(data.get(k),str) or not data[k].strip() for k in required):
                return self.send(400,{'error':'missing_fields'})
            if data['category'] not in ('shipping','billing','security','general') or data['priority'] not in ('normal','high') or data['status'] not in ('queued','pending_review'):
                return self.send(400,{'error':'invalid_enum'})
            with connect() as c:
                try:
                    cur=c.execute('INSERT INTO tickets (request_id,customer,message,category,priority,status,needs_human_review,summary,draft_reply,mode,created_at) VALUES (?,?,?,?,?,?,?,?,?,?,?)',(
                        *[data[k] for k in ('request_id','customer','message','category','priority','status')],
                        int(bool(data.get('needs_human_review'))),data['summary'],data['draft_reply'],data['mode'],datetime.now(timezone.utc).isoformat()))
                    ticket_id=cur.lastrowid
                except sqlite3.IntegrityError:
                    return self.send(409,{'error':'duplicate_request_id','request_id':data['request_id']})
            return self.send(201,{'success':True,'ticket_id':ticket_id,'request_id':data['request_id'],'category':data['category'],'priority':data['priority'],'status':data['status'],'needs_human_review':bool(data.get('needs_human_review')),'draft_reply':data['draft_reply'],'mode':data['mode'],'auto_reply_sent':False})
        except (ValueError,json.JSONDecodeError):
            return self.send(400,{'error':'invalid_json'})

if __name__=='__main__':
    ThreadingHTTPServer(('0.0.0.0',8000),Handler).serve_forever()
