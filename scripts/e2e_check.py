#!/usr/bin/env python3
"""Local e2e QA checks: synthetic tickets only; Python standard library."""
import copy
import json
import os
import sys
import uuid
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
WEBHOOK = os.getenv('WEBHOOK_URL', 'http://localhost:5678/webhook/ai-support-live')
CRM = os.getenv('CRM_URL', 'http://localhost:8000/tickets')
PREFIX = 'qa-' + uuid.uuid4().hex[:12]
results = []

def api(url, payload=None):
    raw = None if payload is None else json.dumps(payload, ensure_ascii=False).encode('utf-8')
    request = Request(url, data=raw, headers={'Content-Type': 'application/json'} if raw else {}, method='POST' if raw else 'GET')
    try:
        with urlopen(request, timeout=55) as response:
            status, body = response.status, response.read().decode('utf-8')
    except HTTPError as err:
        status, body = err.code, err.read().decode('utf-8')
    try:
        return status, json.loads(body)
    except json.JSONDecodeError:
        return status, {'_raw': body[:500]}

def tickets_for(request_id):
    status, body = api(CRM)
    if status != 200 or not isinstance(body.get('tickets'), list):
        raise RuntimeError(f'CRM GET /tickets returned {status}: {str(body)[:200]}')
    return [row for row in body['tickets'] if row.get('request_id') == request_id]

def sample(filename, ident):
    payload = json.loads((ROOT / 'samples' / filename).read_text(encoding='utf-8-sig'))
    payload['request_id'] = ident
    return payload

def check(name, passed, detail):
    results.append((name, bool(passed), detail))
    print(f"{'PASS' if passed else 'FAIL'} {name} – {detail}", flush=True)

def positive(name, filename, expected, ident):
    before = len(tickets_for(ident))
    status, body = api(WEBHOOK, sample(filename, ident))
    after = tickets_for(ident)
    row = after[0] if len(after) == 1 else {}
    matching = all(row.get(k) == v for k, v in expected.items())
    # CRM may respond with 201; webhook must also return successful creation.
    ok = status == 201 and body.get('success') is True and len(after) == before + 1 and matching
    check(name, ok, f'HTTP {status}; tickets {before}->{len(after)}; expected {expected}; actual={ {k: row.get(k) for k in expected} }')
    return ok

def negative(name, filename, ident):
    before = len(tickets_for(ident))
    status, body = api(WEBHOOK, sample(filename, ident))
    after = len(tickets_for(ident))
    check(name, status == 400 and before == after, f'HTTP {status}; tickets {before}->{after}; response={body}')

def main():
    print(f'Running 7 tests: webhook={WEBHOOK}, crm={CRM}', flush=True)
    try:
        # First test serves as duplicate prerequisite; must be successful for useful duplicate assertion.
        urgent_id = PREFIX + '-urgent'
        urgent_ok = positive('TC01 urgent', 'urgent.json', {'category':'security','priority':'high','status':'pending_review','needs_human_review':1}, urgent_id)
        positive('TC02 routine', 'routine.json', {'category':'shipping','priority':'normal','status':'queued','needs_human_review':0}, PREFIX + '-routine')
        positive('TC03 billing', 'billing.json', {'category':'billing','status':'pending_review','needs_human_review':1}, PREFIX + '-billing')
        negative('TC04 missing message', 'missing-message.json', PREFIX + '-empty')
        negative('TC05 missing customer', 'missing-customer.json', PREFIX + '-customer')
        if urgent_ok:
            before = len(tickets_for(urgent_id))
            status, body = api(WEBHOOK, sample('duplicate.json', urgent_id))
            after = len(tickets_for(urgent_id))
            # n8n may surface downstream CRM 409 as 500, but duplication must not be stored.
            check('TC06 duplicate', status in (409, 500) and before == after == 1, f'HTTP {status}; tickets {before}->{after}; response={str(body)[:200]}')
        else:
            check('TC06 duplicate', False, 'Cannot run: prerequisite TC01 failed')
        positive('TC07 prompt injection', 'prompt-injection.json', {'category':'security','priority':'high','status':'pending_review','needs_human_review':1}, PREFIX + '-injection')
    except (URLError, OSError, ValueError, RuntimeError) as error:
        check('Execution environment', False, str(error))
    passed=sum(ok for _,ok,_ in results)
    print(f'\nSUMMARY: PASS {passed}, FAIL {len(results)-passed}, TOTAL {len(results)}')
    return 0 if passed == 7 and len(results) == 7 else 1

if __name__ == '__main__':
    sys.exit(main())
