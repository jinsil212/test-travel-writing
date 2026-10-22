# 대본 수치 점검 도구 (여행_v2) — 2026-10-22 추가
# 사용: python -X utf8 .claude/tools/check_script.py 원고/{주제}/대본_vN.md
# 본문(<!-- 본문 시작 --> ~ <!-- 본문 끝 -->)만 보고, 문체카드 10-4 수치와 되풀이·라벨·가상 장면 후보를 출력한다.
# 판정은 사람이 한다 — 이 도구는 세기만 한다. 기준값(합격원고 9편 실측): 명령형 1~15%, 기관 언급 0~6, 가상 장면 0~1.
import re
import sys
from collections import Counter
from pathlib import Path

SENT = re.compile(r"(?<=[.!?])\s+")
ORG = re.compile(r"외교부|관광청|엠티에이|MTA|공식|시청|경찰|국토교통부|교통기관|우버도|시에서도|시도 ")
HYPO = re.compile(r"라고 해 보세요|상황을 생각해 보세요|생각해 보세요|상상해 보세요")
LABEL = re.compile(r"^(다음은|마지막은|하나는|다른 하나는|두 번째는|세 번째는|네 번째는|다섯 번째는)\s.{0,14}(예요|이에요)[.!]$|^\S{1,6}\s?가지예요[.!]$|^(거리에서는|여기서는)\s.{0,8}기억하세요[.!]$")
PLAN = re.compile(r"카드마다 말씀|카드에서 말씀|뼈대|구성안|항목 공식|억지 칸")  # '카드'=교통카드, '블록'=거리 블록은 정당한 말이라 제외
TAUT = re.compile(r"혼자(일 때|니까|라서)[^.]{0,20}(일행이 없|도와줄 사람이 없|혼자 해결)|일행이 없[^.]{0,12}(니까|거든요)")
REPEAT_KEYS = {
    "번호판": r"번호판",
    "거리뷰": r"거리뷰",
    "사람 있는 칸": r"(사람이 (있는|많은) 칸|직원이 타는 칸|차장이 타는 칸)",
    "막차": r"막차",
    "표적": r"표적",
    "주소 확인": r"주소를 지도에|지도 앱에 .{0,6}주소",
    "큰길": r"큰길",
}


def body_of(text):
    if "<!-- 본문 시작 -->" not in text or "<!-- 본문 끝 -->" not in text:
        sys.exit("[중단] 본문 표식 없음")
    b = text.split("<!-- 본문 시작 -->")[1].split("<!-- 본문 끝 -->")[0]
    return re.sub(r"^\s*#.*$", "", b, flags=re.M)


def main():
    if len(sys.argv) < 2:
        sys.exit("사용: check_script.py 원고/{주제}/대본_vN.md")
    body = body_of(Path(sys.argv[1]).read_text(encoding="utf-8"))
    flat = re.sub(r"\s+", " ", body).strip()
    sents = [s.strip() for s in SENT.split(flat) if s.strip()]
    n = len(sents)
    cmd = [s for s in sents if re.search(r"(세요|마세요)[.!?]?$", s)]
    short = [s for s in sents if len(s) < 20]
    orgs = ORG.findall(body)
    hypo = [s for s in sents if HYPO.search(s)]
    labels = [s for s in sents if LABEL.match(s)]
    plan = [s for s in sents if PLAN.search(s)]
    taut = [s for s in sents if TAUT.search(s)]
    think = len(re.findall(r"라고 생각해요", body))
    want = len(re.findall(r"추천드리고 싶어요", body))

    print(f"본문 공백 포함 {len(flat):,}자 · 공백 제외 {len(re.sub(r'\s', '', body)):,}자 · 문장 {n}개")
    print(f"명령형 끝 {len(cmd)}개 ({len(cmd)/n:.0%}) — 기준 15% 이하")
    print(f"기관·공식 언급 {len(orgs)}회 — 기준 6회 이하 : {dict(Counter(orgs))}")
    print(f"20자 미만 문장 {len(short)}개 ({len(short)/n:.0%}) — 정보 없는 것은 합칠 것")
    for s in short:
        print("   ·", s)
    print(f"'~라고 생각해요' {think}회(≤3) · '~추천드리고 싶어요' {want}회(0)")
    print(f"가상 장면 후보 {len(hypo)}개 — 기준 0")
    for s in hypo:
        print("   ·", s)
    print(f"라벨형 전환 후보 {len(labels)}개 — 기준 0")
    for s in labels:
        print("   ·", s)
    print(f"기획 용어 {len(plan)}개 — 기준 0 ('카드'가 교통카드가 아니라 구성 단위 뜻이면 직접 확인)")
    for s in plan:
        print("   ·", s)
    print(f"전제 되풀이 이유 후보 {len(taut)}개 — 기준 0")
    for s in taut:
        print("   ·", s)
    print("같은 지시 되풀이 후보(편에서 1회가 원칙):")
    for k, p in REPEAT_KEYS.items():
        c = len(re.findall(p, body))
        if c >= 2:
            print(f"   · {k}: {c}회")


if __name__ == "__main__":
    main()
