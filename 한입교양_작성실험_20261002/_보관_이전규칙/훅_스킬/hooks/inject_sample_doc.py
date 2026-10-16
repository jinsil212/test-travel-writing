# -*- coding: utf-8 -*-
"""SessionStart 훅 — 세션 시작 때 견본 목록·차단 규칙·작성 규칙 1쪽을 컨텍스트에 넣는다.
사용: python .claude/hooks/inject_sample_doc.py <채널폴더명>
"""
import io, os, sys

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass
CH = sys.argv[1] if len(sys.argv) > 1 else "채널"
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
C = os.path.join(ROOT, CH)
guide = os.path.join(C, "분석지", "_쓰기전에_읽는_것.md")
passed_dir = os.path.join(C, "_합격원고")
raw_dir = os.path.join(C, "분석지", "원문")

print("[%s 작성 실험 폴더 — 세션 시작 안내]" % CH)
print("대본 파일(원고/*/대본*.txt, 최종원고.md, 파트/*.txt)을 쓰기 전에 ① 아래 견본을 Read로 전문 열람 ② 편 폴더에 쓰기전_설계.md(문단표·용어표)를 먼저 만든다. 둘 중 하나라도 없으면 PreToolUse 훅이 Write/Edit를 차단한다. 대본을 쓴 세션은 /대본검수(차가운 독자) 결과 파일에 판정이 적히기 전엔 턴을 끝낼 수 없다(Stop 훅).")
passed = sorted(n for n in os.listdir(passed_dir) if n.lower().endswith((".txt", ".md")) and not n.startswith("README")) if os.path.isdir(passed_dir) else []
if passed:
    print("1순위 견본 — _합격원고/ (사용자가 고쳐 합격시킨 원고. 전부 읽는다):")
    for n in passed:
        print("  - " + os.path.join(CH, "_합격원고", n))
else:
    print("1순위 견본 — _합격원고/: 아직 없음.")
raws = sorted(n for n in os.listdir(raw_dir) if n.endswith(".txt")) if os.path.isdir(raw_dir) else []
print("2순위 견본 — 분석지/원문/ 벤치마크 전문 (합격본 포함 3편 이상. 이번 편과 같은 유형·같은 채널 우선):")
for n in raws:
    print("  - " + os.path.join(CH, "분석지", "원문", n))
print("초안 뒤: python %s/분석지/_계측_원고.py <대본> → 범위 밖 항목만 수정 → /대본검수 → 고침 → 2차 독자 → 판정. 공용 _대본지침서.md 는 쓰는 동안 열지 않는다(검수 패스에서만)." % CH)
print()
if os.path.exists(guide):
    print("===== %s/분석지/_쓰기전에_읽는_것.md (자동 삽입) =====" % CH)
    sys.stdout.write(io.open(guide, encoding="utf-8").read())
