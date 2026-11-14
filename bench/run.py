"""Measure the trailer: catch rate, false alarms, routing share, review minutes, trust ledger.

python3 -m bench.run            # 13 sample PRs (with UI) + 60 mutants
python3 -m bench.run --no-ui --mutants 0
"""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from trailer import engine, render, workspace  # noqa: E402
from bench import mutants as mutmod  # noqa: E402

# Review-time model (minutes). Assumptions are explicit so judges can change them.
MIN_PER_LINE = 0.6      # reading a changed line *with* the surrounding code it needs (~100 lines/hour)
ORIENT = 4.0            # opening the PR, understanding the requirement
TIER_COST = {
    "light": lambda t: 2.0,                                    # read trailer, watch video, sign
    "targeted": lambda t: min(3.0 + 1.0 * len(t["refusals"]) + MIN_PER_LINE * flagged_lines(t), baseline(t) + 1.0),
    "full": lambda t: baseline(t) + 1.5,                       # full read plus reading the trailer
    "return": lambda t: 1.0,                                   # glance at verified finding, bounce to agent
}


def baseline(t):
    return ORIENT + MIN_PER_LINE * t["lines_changed"]


def flagged_lines(t):
    files = {i["file"] for i in t["findings"] + t["refusals"] if i["file"]}
    return sum(d["added"] + d["removed"] for d in t["diff"] if d["path"] in files)


def points_at(t, path):
    return [i for i in t["findings"] + t["refusals"] if i["file"] == path]


def score_samples(trailers, truth):
    rows = []
    for t in trailers:
        pid = t["pr"]["id"]
        bug = truth.get(pid)
        tier = t["decision"]["tier"]
        verified_block = [f for f in t["findings"] if f["verified"] and f["severity"] == "block"]
        on_bug = points_at(t, bug["file"]) if bug else []
        strict = bool(bug and tier == "return" and any(f["file"] == bug["file"] or f["rule"].startswith("T-") for f in verified_block))
        attention = bool(bug and (strict or (tier in ("targeted", "full") and on_bug)))
        rows.append({
            "pr": pid, "area": t["requirement"]["area"], "buggy": bool(bug), "tier": tier,
            "blocked": strict, "routed_to_bug": attention, "escaped": bool(bug and not attention),
            "false_alarm": bool(not bug and verified_block), "unverified_noise": bool(not bug and [f for f in t["findings"] if not f["verified"]]),
            "lines": t["lines_changed"], "baseline_min": round(baseline(t), 1),
            "trailer_min": round(TIER_COST[tier](t), 1), "door": t["danger"]["door"],
            "findings": len(t["findings"]), "refusals": len(t["refusals"]),
            "bug": bug["bug"] if bug else None,
            "caught_by": sorted({f["rule"] for f in verified_block}) if strict else sorted({i["rule"] for i in on_bug}),
        })
    return rows


def summarise(rows):
    bugs = [r for r in rows if r["buggy"]]
    clean = [r for r in rows if not r["buggy"]]
    n = len(rows)
    tiers = {k: sum(r["tier"] == k for r in rows) for k in ("light", "targeted", "full", "return")}
    base = sum(r["baseline_min"] for r in rows)
    trail = sum(r["trailer_min"] for r in rows)
    return {
        "prs": n, "buggy": len(bugs), "clean": len(clean),
        "blocked_with_verified_evidence": sum(r["blocked"] for r in bugs),
        "routed_to_human_at_bug": sum(r["routed_to_bug"] and not r["blocked"] for r in bugs),
        "escaped": sum(r["escaped"] for r in bugs),
        "catch_rate": round(sum(r["routed_to_bug"] for r in bugs) / max(1, len(bugs)), 3),
        "strict_catch_rate": round(sum(r["blocked"] for r in bugs) / max(1, len(bugs)), 3),
        "false_alarm_rate": round(sum(r["false_alarm"] for r in clean) / max(1, len(clean)), 3),
        "unverified_noise_on_clean": sum(r["unverified_noise"] for r in clean),
        "tiers": tiers, "share_routed_to_human_read": round((tiers["targeted"] + tiers["full"]) / n, 3),
        "minutes_baseline": round(base, 1), "minutes_with_trailer": round(trail, 1),
        "minutes_saved_pct": round(100 * (1 - trail / base), 1) if base else 0,
    }


def trust_ledger(rows, start_after=3, penalty=5):
    """Trust per area: Light checks are only allowed in an area after `start_after` PRs with no escapes.
    An escape withdraws trust: the next `penalty` PRs in that area get a full read."""
    state, log = {}, []
    for r in rows:
        a = state.setdefault(r["area"], {"clean_streak": 0, "withdrawn_for": 0, "escapes": 0})
        status = "withdrawn" if a["withdrawn_for"] else ("earned" if a["clean_streak"] >= start_after else "probation")
        effective = r["tier"]
        if status == "withdrawn" and r["tier"] in ("light", "targeted"):
            effective = "full"
        elif status == "probation" and r["tier"] == "light":
            effective = "targeted"
        if r["escaped"] and effective != "full":  # a full human read is assumed to catch it
            a["escapes"] += 1
            a["clean_streak"] = 0
            a["withdrawn_for"] = penalty
            event = "escape found after merge: trust withdrawn"
        else:
            a["clean_streak"] += 1
            a["withdrawn_for"] = max(0, a["withdrawn_for"] - 1)
            event = ""
        log.append({"pr": r["pr"], "area": r["area"], "status_before": status, "ai_tier": r["tier"],
                    "effective_tier": effective, "event": event})
    return {"areas": state, "log": log,
            "escapes_without_ledger": sum(r["escaped"] for r in rows),
            "escapes_with_ledger": sum(1 for l in log if l["event"]),
            "extra_full_reads_from_ledger": sum(1 for l in log if l["effective_tier"] == "full" and l["ai_tier"] != "full")}


def run_mutants(out, family, n):
    mdir = ROOT / "out" / f"_mutants_{family}"
    mtruth = mutmod.generate(mdir, n=n, family=family)
    workspace.PRS = mdir
    mrows = []
    for pid in sorted(mtruth):
        t = engine.build(pid, out / f"_mutant_trailers_{family}", with_ui=False)
        tr = mtruth[pid]
        verified_block = [f for f in t["findings"] if f["verified"] and f["severity"] == "block"]
        tier = t["decision"]["tier"]
        mrows.append({"pr": pid, "area": tr["file"].split("/")[-1][:-3], "buggy": True,
                      "escaped": tier == "light", "routed_to_bug": tier != "light",
                      "mutation": f"{tr['file']}:{tr['line']} {tr['mutation']}",
                      "tier": tier, "blocked": tier == "return", "routed": tier in ("targeted", "full"),
                      "light": tier == "light", "lines": t["lines_changed"], "baseline_min": round(baseline(t), 1),
                      "trailer_min": round(TIER_COST[tier](t), 1), "tests_caught": tests_caught(t),
                      "caught_by": sorted({f["rule"] for f in verified_block})})
    workspace.PRS = ROOT / "prs"
    m = len(mrows)
    return {"summary": {"family": family, "mutants": m,
                        "blocked_with_verified_evidence": sum(r["blocked"] for r in mrows),
                        "routed_to_human": sum(r["routed"] for r in mrows),
                        "passed_as_light": sum(r["light"] for r in mrows),
                        "strict_catch_rate": round(sum(r["blocked"] for r in mrows) / m, 3),
                        "catch_rate": round(sum(not r["light"] for r in mrows) / m, 3),
                        "note": "Survivors include equivalent mutants that change nothing observable; "
                                "they were not removed by hand."},
            "rows": mrows, "ledger": trust_ledger(mrows)}


def tests_caught(t):
    return any(f["rule"] in ("T-REGRESSION", "T-CLAIM-UNMET") and f["verified"] for f in t["findings"])


def baselines(rows):
    """Dumb routers the trailer must beat. 'Caught' = the PR went to a human read or was blocked on evidence."""
    bugs = [r for r in rows if r["buggy"]] or [{}]
    clean = [r for r in rows if not r["buggy"]]

    def score(name, routes, minutes):
        caught = sum(1 for r in rows if r["buggy"] and routes(r))
        alarms = sum(1 for r in clean if routes(r))
        return {"name": name, "catch_rate": round(caught / len([r for r in rows if r["buggy"]] or [1]), 3),
                "flags_on_clean": f"{alarms}/{len(clean)}" if clean else "n/a",
                "minutes": round(sum(minutes(r) for r in rows), 1)}

    full = lambda r: r["baseline_min"]
    return [
        score("Approve everything", lambda r: False, lambda r: 2.0),
        score("Tests only (CI green = merge)", lambda r: r["tests_caught"], lambda r: 1.0 if r["tests_caught"] else 2.0),
        score("Diff size router (>15 lines = full read)", lambda r: r["lines"] > 15, lambda r: full(r) if r["lines"] > 15 else 2.0),
        score("Full read of everything", lambda r: True, full),
        score("PR Trailer", lambda r: r["tier"] != "light", lambda r: r["trailer_min"]),
    ]


def spot_checks(rows, share=0.2, seed=5):
    """Humans spot-check a random share of light-lane PRs with a full read; misses found this way feed the ledger."""
    import random
    light = [r["pr"] for r in rows if r["tier"] == "light"]
    rng = random.Random(seed)
    k = max(1, round(share * len(light))) if light else 0
    picked = sorted(rng.sample(light, k)) if k else []
    found = [p for p in picked if any(r["pr"] == p and r["buggy"] for r in rows)]
    return {"policy": f"full read of {int(share * 100)}% of light-lane PRs, chosen at random",
            "light_prs": len(light), "picked": picked, "misses_found": found}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(ROOT / "out"))
    ap.add_argument("--no-ui", action="store_true")
    ap.add_argument("--mutants", type=int, default=60)
    a = ap.parse_args()
    out = Path(a.out)

    truth = json.loads((ROOT / "bench" / "ground_truth.json").read_text())
    truth = {k: v for k, v in truth.items() if v}
    trailers = []
    for pid in workspace.all_pr_ids():
        t = engine.build(pid, out, with_ui=not a.no_ui)
        (out / pid / "trailer.md").write_text(render.markdown(t))
        trailers.append(t)
        print(f"{pid}: {t['decision']['label']}", flush=True)
    rows = score_samples(trailers, truth)
    for r, t in zip(rows, trailers):
        r["tests_caught"] = tests_caught(t)
    result = {"samples": {"summary": summarise(rows), "rows": rows, "ledger": trust_ledger(rows)},
              "assumptions": {"min_per_line": MIN_PER_LINE, "orientation_min": ORIENT,
                              "light_min": 2.0, "targeted_min": "3 + 1 per open question + 0.6 per flagged line",
                              "full_min": "baseline + 1.5", "return_min": 1.0}}

    if a.mutants:
        result["mutants"] = run_mutants(out, "dev", a.mutants)
        result["heldout"] = run_mutants(out, "heldout", a.mutants)
    result["baselines"] = {"samples": baselines(rows)}
    if a.mutants:
        result["baselines"]["mutants"] = baselines(result["mutants"]["rows"])
        result["baselines"]["heldout"] = baselines(result["heldout"]["rows"])
    result["spot_checks"] = spot_checks(rows + result.get("mutants", {}).get("rows", []))
    (out / "bench.json").write_text(json.dumps(result, indent=2))
    print(json.dumps(result["samples"]["summary"], indent=2))
    if a.mutants:
        print(json.dumps(result["mutants"]["summary"], indent=2))
        print(json.dumps(result["heldout"]["summary"], indent=2))
    print(json.dumps(result["baselines"], indent=1))
    print(json.dumps(result["spot_checks"]))


if __name__ == "__main__":
    main()
