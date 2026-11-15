"""Idempotent metadata-only execution records in MongoDB Atlas, with a local outbox."""
from datetime import datetime, timezone
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import threading

ROOT=Path(__file__).resolve().parents[1]
_lock=threading.RLock()
_client=None

def _outbox():
    path=Path(os.environ.get('TIETO_RUNLOG_OUTBOX',str(ROOT/'var/product/runlog.sqlite')))
    path.parent.mkdir(parents=True,exist_ok=True)
    db=sqlite3.connect(path,timeout=5)
    db.execute('CREATE TABLE IF NOT EXISTS events (id TEXT PRIMARY KEY, body TEXT NOT NULL, delivered INTEGER NOT NULL DEFAULT 0)')
    return db

@contextmanager
def _transaction():
    db=_outbox()
    try:
        with db:yield db
    finally:db.close()

def _collection():
    global _client
    uri=os.environ.get('MONGODB_URI','')
    if not uri:return None
    if not uri.startswith(('mongodb+srv://','mongodb://')):raise ValueError('Invalid MongoDB configuration')
    if _client is None:
        from pymongo import MongoClient
        _client=MongoClient(uri,appname='pr-trailer',serverSelectionTimeoutMS=2500,
                            connectTimeoutMS=2500,socketTimeoutMS=2500,tls=True)
    database=os.environ.get('MONGODB_DATABASE','pr_trailer')
    if not database.replace('_','').isalnum():raise ValueError('Invalid log database')
    return _client[database]['execution_events']

def _metadata(run_id,label,result,metadata):
    # No raw source, test stdout, private paths, tokens or arbitrary caller fields.
    return {'_id':hashlib.sha256((str(run_id)+':'+str(label)).encode()).hexdigest(),
            'runId':str(run_id)[:80],'label':str(label)[:100],
            'eventType':'review_decision' if metadata.get('eventType')=='review_decision' else 'test_check',
            'action':metadata.get('action') if metadata.get('action') in ('merge','return','block','unblock','revert') else None,
            'actor':str(metadata.get('actor',''))[:100],
            'commitSha':str(metadata.get('commitSha',''))[:40],
            'recordedAt':datetime.now(timezone.utc).isoformat(),
            'repo':str(metadata.get('repo',''))[:200],
            'headSha':str(metadata.get('headSha',''))[:40],
            'number':metadata.get('number') if isinstance(metadata.get('number'),int) else None,
            'exitCode':result.get('exitCode'),'tests':result.get('tests'),'passed':result.get('passed'),
            'seconds':result.get('seconds'),'outputSha256':result.get('outputSha256'),
            'provider':result.get('execution',{}).get('provider','local'),
            'sandboxId':result.get('execution',{}).get('sandboxId')}

def flush():
    """Replay pending records; provider failure preserves them for a later retry."""
    try:
        collection=_collection()
        if collection is None:return {'provider':'local-outbox','stored':False,'pending':True}
        delivered=0
        with _lock,_transaction() as db:
            for id,body in db.execute('SELECT id,body FROM events WHERE delivered=0 ORDER BY rowid LIMIT 100'):
                collection.replace_one({'_id':id},json.loads(body),upsert=True)
                db.execute('UPDATE events SET delivered=1 WHERE id=?',(id,));delivered+=1
        return {'provider':'mongodb-atlas','stored':True,'delivered':delivered}
    except Exception:
        return {'provider':'mongodb-atlas','stored':False,'pending':True}

def record_check(run_id,label,result,metadata):
    record=_metadata(run_id,label,result,metadata)
    with _lock,_transaction() as db:
        db.execute('INSERT INTO events(id,body,delivered) VALUES(?,?,0) ON CONFLICT(id) DO UPDATE SET body=excluded.body,delivered=0',
                   (record['_id'],json.dumps(record)))
    receipt=flush()
    with _lock,_transaction() as db:
        delivered=db.execute('SELECT delivered FROM events WHERE id=?',(record['_id'],)).fetchone()[0]
    receipt['stored']=bool(delivered);receipt['eventId']=record['_id'];return receipt

def read_run(run_id):
    """Read from Atlas when configured, proving logs survive a worker restart."""
    try:
        collection=_collection()
        if collection is None:return {'provider':'local-outbox','durableRemote':False,'events':[]}
        events=list(collection.find({'runId':str(run_id)},{'_id':0}).limit(101))
        return {'provider':'mongodb-atlas','durableRemote':True,'events':events[:100],'truncated':len(events)>100}
    except Exception:
        raise RuntimeError('Archived run records are temporarily unavailable') from None

def record_decision(action,row,receipt,actor):
    """Archive an acknowledged human/GitHub decision, never its free-text note."""
    identity=receipt.get('sha') or receipt.get('commentId') or receipt.get('number') or row.get('number')
    run_id=row.get('runId') or 'review-'+str(row.get('id',''))+'-'+str(row.get('number',''))
    try:
        return record_check(run_id,'decision-'+action+'-'+str(identity),{'execution':{'provider':'github'}},
            {'eventType':'review_decision','action':action,'actor':actor,'repo':row.get('repo'),
             'headSha':row.get('headSha'),'number':row.get('number'),'commitSha':receipt.get('sha','')})
    except Exception:
        # A completed GitHub decision must never appear to have failed merely
        # because the optional audit sink is unavailable.
        return {'provider':'mongodb-atlas','stored':False,'pending':False}

