import importlib.util, json, tempfile, unittest
from pathlib import Path
from threading import Thread
from http.server import ThreadingHTTPServer
from urllib.request import Request, urlopen
from urllib.error import HTTPError
import os

class CrmTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp=tempfile.TemporaryDirectory()
        os.environ['DB_PATH']=str(Path(cls.tmp.name)/'test.db')
        spec=importlib.util.spec_from_file_location('crm',Path(__file__).parents[1]/'mock-crm'/'server.py')
        m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
        cls.server=ThreadingHTTPServer(('127.0.0.1',0),m.Handler)
        cls.port=cls.server.server_address[1]
        cls.thread=Thread(target=cls.server.serve_forever,daemon=True);cls.thread.start()
    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown();cls.server.server_close();cls.tmp.cleanup()
    def post(self,data):
        req=Request(f'http://127.0.0.1:{self.port}/tickets',data=json.dumps(data).encode(),headers={'Content-Type':'application/json'},method='POST')
        try:
            with urlopen(req) as r:return r.status,json.load(r)
        except HTTPError as e:return e.code,json.load(e)
    def ticket(self,id):
        return dict(request_id=id,customer='Test',message='Hello',category='general',priority='normal',status='queued',needs_human_review=False,summary='Hello',draft_reply='Thanks',mode='demo')
    def test_create_and_duplicate(self):
        code,out=self.post(self.ticket('a'));self.assertEqual(code,201);self.assertTrue(out['success'])
        code,out=self.post(self.ticket('a'));self.assertEqual(code,409)
    def test_invalid_category(self):
        d=self.ticket('b');d['category']='untrusted';self.assertEqual(self.post(d)[0],400)
    def test_list(self):
        with urlopen(f'http://127.0.0.1:{self.port}/tickets') as r:self.assertGreaterEqual(len(json.load(r)['tickets']),1)

if __name__=='__main__':unittest.main()
