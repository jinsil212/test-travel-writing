# -*- coding: utf-8 -*-
"""별도 검토자 보고서(JSON)에 원고 문자 위치(start/end)와 판본 해시를 붙인다.
사용: python3 _검수/김육_대동법_review_bind.py <in_report.json> <out_report.json>
- 모든 quote를 현재 원고(UTF-8, 개행 정규화)에서 찾아 start/end를 기록한다.
- 문단 quote는 문단 순서대로 대응시키고, use/supports/draft_evidence/findings.quote는 문자열 검색으로 찾는다.
- 못 찾는 인용은 오류로 출력하고 종료 코드 2를 낸다. 판정 내용은 바꾸지 않는다."""
import importlib.util, json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("sg", ROOT / "_도구" / "script-gate.py")
sg = importlib.util.module_from_spec(spec); spec.loader.exec_module(sg)
DRAFT = ROOT / "채널미정" / "원고" / "김육_대동법" / "대본_검토본.txt"

text = sg.read(str(DRAFT))
paras = sg.paragraphs(text)
errors = []

def norm_q(q):
    return q.strip()

def locate(q, lo=0, hi=None, label=""):
    q = norm_q(q)
    hi = len(text) if hi is None else hi
    i = text.find(q, lo, hi)
    if i < 0:
        i = text.find(q)
        if i < 0:
            errors.append(f"{label}: 인용을 원고에서 찾지 못함: {q[:50]}")
            return None
    return {"start": i, "end": i + len(q), "quote": q}

src = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8-sig"))
rep = dict(src)
rep["draft_sha256"] = sg.digest(DRAFT)
rep["guide_sha256"] = sg.digest(sg.GUIDE)

for axis, entry in rep.get("axes", {}).items():
    de = []
    for item in entry.get("draft_evidence", []) or []:
        span = locate(item["quote"], label=f"{axis} draft_evidence")
        if span: de.append(span)
    entry["draft_evidence"] = de
    for f in entry.get("findings", []) or []:
        if "quote" in f:
            span = locate(f["quote"], label=f"{axis} finding {f.get('id')}")
            if span: f.update(span)

checks = rep.get("comprehension_checks", [])
if len(checks) != len(paras):
    errors.append(f"문단 수 불일치: 보고서 {len(checks)} / 원고 {len(paras)}")
bound = []
for idx, row in enumerate(checks):
    if idx >= len(paras):
        break
    part = paras[idx]
    row = dict(row)
    row["paragraph"] = idx + 1
    if norm_q(row.get("quote", "")) != part["quote"]:
        errors.append(f"문단 {idx+1}: 전문 불일치 (보고서: {norm_q(row.get('quote',''))[:40]} / 원고: {part['quote'][:40]})")
        row["quote"] = part["quote"]
    deps = []
    for dep in row.get("dependencies", []) or []:
        dep = dict(dep)
        use = dep.get("use", {})
        span = locate(use.get("quote", ""), part["start"], part["end"], label=f"문단 {idx+1} use")
        if span: dep["use"] = span
        sups = []
        for s in dep.get("supports", []) or []:
            sp = locate(s.get("quote", ""), 0, None, label=f"문단 {idx+1} support")
            if sp:
                if span and sp["end"] > span["end"]:
                    # 같은 인용이 앞에도 있으면 앞의 것을 택한다
                    j = text.rfind(sp["quote"], 0, span["end"])
                    if j >= 0:
                        sp = {"start": j, "end": j + len(sp["quote"]), "quote": sp["quote"]}
                    else:
                        errors.append(f"문단 {idx+1}: 선행 설명이 사용처보다 뒤에 있음: {sp['quote'][:40]}")
                sups.append(sp)
        dep["supports"] = sups
        deps.append(dep)
    row["dependencies"] = deps
    bound.append(row)
rep["comprehension_checks"] = bound

Path(sys.argv[2]).write_text(json.dumps(rep, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
if errors:
    print("\n".join(errors)); sys.exit(2)
print(json.dumps({"status": "BOUND", "paragraphs": len(bound), "output": sys.argv[2]}, ensure_ascii=False))
