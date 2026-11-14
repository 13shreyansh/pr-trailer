"""Runtime probes executed inside a workspace (python3 -I _probe.py <ws> <mode> <json-arg>).

idor  : call every API route that takes account_id as the wrong user; report which ones answer.
call  : evaluate module.function on a list of argument tuples; report results (for differential testing).
"""
import importlib
import json
import sys
from pathlib import Path

ws = Path(sys.argv[1]).resolve()
sys.path.insert(0, str(ws))
mode, arg = sys.argv[2], json.loads(sys.argv[3])

if mode == "idor":
    from ledger import api, db as dbmod
    from ledger.transfers import create_transfer
    from ledger.auth import Forbidden
    db = dbmod.connect()
    dbmod.seed(db)
    create_transfer(db, "u-anna", "acc-anna", "FI5542345670000081", 1234, memo="private")
    out = []
    for (method, path), fn in api.ROUTES.items():
        if path not in arg["routes"]:
            continue
        params = {"account_id": "acc-anna", "amount": "1.00", "to_iban": "FI5542345670000081"}
        try:
            body = fn(db, "u-ben", params)
            out.append({"route": f"{method} {path}", "answered": True, "body": json.dumps(body)[:300]})
        except Forbidden:
            out.append({"route": f"{method} {path}", "answered": False})
        except Exception as e:
            out.append({"route": f"{method} {path}", "answered": False, "error": f"{type(e).__name__}: {e}"})
    print(json.dumps(out))
elif mode == "call":
    mod = importlib.import_module(arg["module"])
    fn = getattr(mod, arg["function"])
    res = []
    for args in arg["inputs"]:
        try:
            res.append(repr(fn(*args)))
        except Exception as e:
            res.append(f"raise {type(e).__name__}")
    print(json.dumps(res))
