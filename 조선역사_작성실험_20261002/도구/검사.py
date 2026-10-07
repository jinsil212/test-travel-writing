"""대본 기계 검사 — 금지목록의 ⚙ 항목을 예/아니오로 잡는다.

사용: python 도구/검사.py <대본.txt> [직전 편 대본.txt]
걸린 줄을 보여준다. 고칠지는 사람이(검수 에이전트가) 판단한다.
"""
import re, sys
sys.stdout.reconfigure(encoding="utf-8")

text = open(sys.argv[1], encoding="utf-8").read()
prev = open(sys.argv[2], encoding="utf-8").read() if len(sys.argv) > 2 else ""
sents = [s.strip() for s in re.split(r"(?<=[.?!])\s+|\n+", text) if s.strip()]

CHECKS = [
    ("12 가운뎃점", r"·"),
    ("13 소리로 헷갈림", r"(베를|베와|베 |군포)"),
    ("15 '○○ 임금' 호칭", r"(태조|정종|태종|세종|문종|단종|세조|예종|성종|연산군|중종|인종|명종|선조|광해군|인조|효종|현종|숙종|경종|영조|정조|순조|헌종|철종|고종)\s*임금"),
    ("16 소제목·화면지시", r"^(#|\[|\(화면|\(자막|챕터|\d+\.\s)"),
    ("11 밋밋한 시작", r"(알아보겠습니다|안녕하세요|오늘은 .{0,20}에 대해)"),
    ("20 훈계·축원", r"(여러분도 .{0,30}(바랍니다|하시길|합시다))"),
    ("5 과장", r"(아무도 (몰랐|눈여겨|알지 못)|역사상 (최악|최고)|상상조차|전무후무)"),
    ("2 추상어", r"(엄청난 변화|놀라운 결과|중요한 의미|큰 의미|특별한 의미)"),
    ("4 번역투 의심", r"(을|를) (준|주는|가져다준) (사람|것)들?|챙겨 가는"),
]

hits = 0
for name, pat in CHECKS:
    for i, s in enumerate(sents, 1):
        if re.search(pat, s, re.M):
            print(f"[{name}] {i}: {s[:90]}"); hits += 1

# 1 뒤집은 대구: "~게 아닙니다/아니라" 앞뒤 문장에 같은 2글자 이상 단어가 반복
for i in range(len(sents) - 1):
    a, b = sents[i], sents[i + 1]
    if re.search(r"(게|것이|건) 아닙니다|아니라", a):
        stop = {"것이", "아닙", "그런", "때문", "있었", "했습", "합니", "입니"}
        wa = {w[:2] for w in re.findall(r"[가-힣]{2,}", a)}; wb = {w[:2] for w in re.findall(r"[가-힣]{2,}", b)}
        common = (wa & wb) - stop
        if common:
            print(f"[1 뒤집은 대구 의심] {i+1}: {a[:60]} / {b[:60]}  공통={sorted(common)[:3]}"); hits += 1

# 같은 진입 선언·문장이 직전 편에 그대로 있으면
if prev:
    for s in sents:
        if len(s) > 15 and s in prev:
            print(f"[19 직전 편과 같은 문장] {s[:90]}"); hits += 1

n = len(re.sub(r"\s", "", text))
longs = [s for s in sents if len(s) > 80]
print(f"\n공백 제외 {n}자 (약 {n/380:.1f}분) · 문장 {len(sents)}개 · 80자 넘는 문장 {len(longs)}개 · 걸린 곳 {hits}개")
for s in longs[:10]:
    print(f"[긴 문장] {s[:90]}…")
