"""python3 -m trailer [PR-ID ...] [--no-ui] [--llm gemini]"""
import argparse
from pathlib import Path

from . import engine, render, workspace


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("prs", nargs="*")
    ap.add_argument("--out", default="out")
    ap.add_argument("--no-ui", action="store_true")
    ap.add_argument("--llm", choices=["gemini"], default=None)
    ap.add_argument("--llm-replay", default=None, help="cache dir: reuse recorded LLM answers, record new ones")
    a = ap.parse_args()
    llm = None
    if a.llm == "gemini":
        from . import llm as llm_mod
        llm = llm_mod.Gemini(replay_dir=a.llm_replay)
    out = Path(a.out)
    for pid in a.prs or workspace.all_pr_ids():
        t = engine.build(pid, out, with_ui=not a.no_ui, llm=llm)
        (out / pid / "trailer.md").write_text(render.markdown(t))
        print(f"{pid:7} {t['decision']['label']:17} door={t['danger']['door']:22} "
              f"findings={len(t['findings'])} refusals={len(t['refusals'])}")
    if llm:
        print("LLM grounding:", llm.stats)


if __name__ == "__main__":
    main()
