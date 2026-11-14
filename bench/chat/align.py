"""Agreement between the GROUNDED judge and hand labels: TPR (judge fails what a human fails), TNR (judge passes what a human passes)."""
import json, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import grade  # noqa: E402
H = json.loads((HERE / "hand_labels.json").read_text())
traces = json.loads((HERE / H["trace_file"]).read_text())
rows = grade.grade(HERE / H["trace_file"])
tp = sum(1 for r in rows if not H["labels"][r["id"]] and not r["grounded"])
fn = sum(1 for r in rows if not H["labels"][r["id"]] and r["grounded"])
tn = sum(1 for r in rows if H["labels"][r["id"]] and r["grounded"])
fp = sum(1 for r in rows if H["labels"][r["id"]] and not r["grounded"])
res = {"n": len(rows), "human_fail": tp + fn, "tpr": round(tp / max(1, tp + fn), 3), "tnr": round(tn / max(1, tn + fp), 3),
       "agreement": round((tp + tn) / len(rows), 3),
       "disagreements": [{"id": r["id"], "human": H["labels"][r["id"]], "judge": r["grounded"], "critique": r["_critique"]} for r in rows if H["labels"][r["id"]] != r["grounded"]]}
(HERE / "alignment.json").write_text(json.dumps(res, indent=1))
print(json.dumps(res, indent=1))
