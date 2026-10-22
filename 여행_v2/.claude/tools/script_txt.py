# 대본 txt 변환 도구 (여행_v2)
# 사용:
#   python -X utf8 script_txt.py 읽기용 원고/{주제}/대본_vN.md
#       → 원고/{주제}/대본_vN_읽기용.txt  (장 제목 구분선 + 한 문장 한 줄 + 문단 사이 빈 줄)
#   python -X utf8 script_txt.py 최종 원고/{주제}/대본_vN_읽기용.txt [대본_vN.md]
#       → 원고/{주제}/대본_최종_낭독문.txt (TTS용 클린 대본)
#         · 영문 약어·날짜(년·월·일)·달러/센트/원/퍼센트 금액을 한글 소리로 바꾼다
#         · 문단을 2~5문장 단위로 맞춘다 (긴 문단은 나누고, 한 문장 문단은 다음 문단에 붙인다)
#         · 대본 md를 같이 주면 읽기용 txt가 md와 다른지 알려 주고, 본문 표식이 없는 md는 거부한다
#         · 남으면 안 되는 표시([꼬리표]·▷·🇺🇸·S##·안내돼·결론부터 말씀드리면·해주고 싶은 얘기 등)를 경고한다
# 본문 범위: md의 <!-- 본문 시작 --> ~ <!-- 본문 끝 -->.
import re
import sys
from pathlib import Path

RULE = "━━━━━━━━━━━━━━━━━━━━"
BAD = [
    r"S\d{2}\b", r"\[[^\]\n]{1,14}\]", r"저희", r"<!--", r"\*\*", r"^#", r"▷", r"🇺🇸",
    r"안내돼", r"결론부터 말씀드리면", r"해주고 싶은 얘기", r"안내돼요", r"고 해요", r"고 하니까",
]
SENT_SPLIT = r"(?<=[.?!])\s+"

# ── 한글 소리 변환 ──────────────────────────────────────────────
DIGIT = "영일이삼사오육칠팔구"
SMALL = ["", "십", "백", "천"]
BIG = ["", "만", "억", "조"]


def num2kor(n: int) -> str:
    if n == 0:
        return "영"
    out, unit = [], 0
    while n > 0:
        chunk, n = n % 10000, n // 10000
        if chunk:
            s = ""
            for i, ch in enumerate(reversed(str(chunk))):
                d = int(ch)
                if d == 0:
                    continue
                s = (("" if d == 1 and i > 0 else DIGIT[d]) + SMALL[i]) + s
            if unit > 0 and s == "일":
                s = ""  # 일만 → 만
            out.append(s + BIG[unit])
        unit += 1
    return "".join(reversed(out))


def numstr(s: str) -> int:
    return int(s.replace(",", ""))


LETTER = {c: k for c, k in zip("ABCDEFGHIJKLMNOPQRSTUVWXYZ",
    "에이 비 씨 디 이 에프 지 에이치 아이 제이 케이 엘 엠 엔 오 피 큐 알 에스 티 유 브이 더블유 엑스 와이 제트".split())}
ABBR = {
    "OMNY": "옴니", "MTA": "엠티에이", "JFK": "제이에프케이", "LA": "엘에이", "DC": "디씨", "TKTS": "티케이티에스",
    "MIT": "엠아이티", "KTX": "케이티엑스", "SNS": "에스엔에스", "CVS": "씨브이에스", "GO": "고", "NYC": "엔와이씨",
    "USA": "유에스에이", "ID": "아이디", "OK": "오케이", "TV": "티비", "AI": "에이아이", "ATM": "에이티엠",
    "ESTA": "에스타", "TSA": "티에스에이", "WIFI": "와이파이", "UBER": "우버", "PATH": "패스", "SRT": "에스알티",
}
MONTH = {6: "유월", 10: "시월"}


def abbr2kor(word: str) -> str:
    return ABBR.get(word.upper()) or " ".join(LETTER[c] for c in word if c in LETTER)


def cents(frac: str) -> str:
    frac = (frac + "0")[:2]
    return f" {num2kor(int(frac))} 센트" if int(frac) else ""


def to_sound(text: str):
    """영문 약어·날짜·금액을 한글 소리로. (변환문, 남은 영문/숫자 목록) 반환"""
    t = text
    # 달러: $12.50 / 12.5달러 / 2달러 99센트 / 35달러
    t = re.sub(r"\$\s?(\d[\d,]*)(?:\.(\d+))?", lambda m: f"{num2kor(numstr(m[1]))} 달러{cents(m[2]) if m[2] else ''}", t)
    t = re.sub(r"(\d[\d,]*)\.(\d+)\s*달러", lambda m: f"{num2kor(numstr(m[1]))} 달러{cents(m[2])}", t)
    t = re.sub(r"(\d[\d,]*)\s*달러", lambda m: f"{num2kor(numstr(m[1]))} 달러", t)
    t = re.sub(r"(\d[\d,]*)\s*센트", lambda m: f"{num2kor(numstr(m[1]))} 센트", t)
    # 원: 1,340원 / 4만 7천 원 / 15만원
    t = re.sub(r"(\d[\d,]*)\s*(만|천|백)\s*(?=\d*\s*(?:만|천|백|원))", lambda m: f"{num2kor(numstr(m[1]))}{m[2]} ", t)
    t = re.sub(r"(\d[\d,]*)\s*원", lambda m: f"{num2kor(numstr(m[1]))} 원", t)
    # 퍼센트
    t = re.sub(r"(\d[\d,]*)\s*(%|퍼센트)", lambda m: f"{num2kor(numstr(m[1]))} 퍼센트", t)
    # 날짜: 2026년 / 10월 / 11일 / 9·11 / 9/11
    t = re.sub(r"(\d{4})\s*년", lambda m: f"{num2kor(int(m[1]))}년", t)
    t = re.sub(r"(\d{1,2})\s*월(?!요일)", lambda m: MONTH.get(int(m[1]), num2kor(int(m[1])) + "월"), t)
    t = re.sub(r"(?<![\d.])(\d{1,2})\s*일(?=\s|[,.]|$|에|부터|까지|쯤|이|은|부|간)", lambda m: f"{num2kor(int(m[1]))} 일", t)
    t = re.sub(r"\b9\s*[·/.]\s*11\b", "구일일", t)
    # 영문 약어: 대문자 2자 이상 → 글자 소리, 한 글자 대문자+한글(L선·G선) → 글자 소리
    t = re.sub(r"\b[A-Z]{2,}\b", lambda m: abbr2kor(m[0]), t)
    t = re.sub(r"\b([A-Z])(?=[가-힣])", lambda m: LETTER[m[1]] + " ", t)
    leftover = sorted(set(re.findall(r"[A-Za-z]{2,}", t)))
    digits = sorted(set(re.findall(r"\d[\d,.]*", t)), key=lambda s: (len(s), s))
    return t, leftover, digits


# ── 본문 추출·변환 ──────────────────────────────────────────────
def body_of(md_text):
    if "<!-- 본문 시작 -->" not in md_text or "<!-- 본문 끝 -->" not in md_text:
        sys.exit("[중단] md에 '<!-- 본문 시작 -->' / '<!-- 본문 끝 -->' 표시가 없음 — 낭독 본문 앞뒤에 넣고 메타·댓글·점검표는 밖에 둘 것")
    return md_text.split("<!-- 본문 시작 -->")[1].split("<!-- 본문 끝 -->")[0]


def to_reading(md_text):
    out = []
    for line in body_of(md_text).splitlines():
        line = line.strip()
        if not line:
            continue
        if line.startswith("#"):
            if out:
                out.append("")
            out += [RULE, "【" + line.lstrip("# ").strip() + "】", RULE, ""]
            continue
        out += [s.strip() for s in re.split(SENT_SPLIT, line) if s.strip()]
        out.append("")
    return "\n".join(out).rstrip() + "\n"


def reading_paras(reading_text):
    """읽기용 txt → 문장 리스트의 리스트(문단). 구분선·장 제목은 버림"""
    paras, cur, skip = [], [], False
    for line in reading_text.splitlines():
        s = line.strip()
        if s == RULE:
            skip = not skip
            continue
        if skip or (s.startswith("【") and s.endswith("】")):
            continue
        if not s:
            if cur:
                paras.append(cur)
                cur = []
            continue
        cur += [x.strip() for x in re.split(SENT_SPLIT, s) if x.strip()]
    if cur:
        paras.append(cur)
    return paras


def regroup(paras, lo=2, hi=5):
    """문단을 2~5문장으로: 긴 문단은 균등 분할, 1문장 문단은 다음(없으면 앞) 문단에 붙임"""
    split = []
    for p in paras:
        if len(p) <= hi:
            split.append(list(p))
            continue
        k = -(-len(p) // hi)  # 나눌 조각 수
        size = -(-len(p) // k)
        split += [p[i:i + size] for i in range(0, len(p), size)]
    out = []
    i = 0
    while i < len(split):
        cur = split[i]
        while len(cur) < lo and i + 1 < len(split) and len(cur) + len(split[i + 1]) <= hi:
            i += 1
            cur = cur + split[i]
        if len(cur) < lo and out and len(out[-1]) + len(cur) <= hi:
            out[-1] = out[-1] + cur
        else:
            out.append(cur)
        i += 1
    return out


def main():
    if len(sys.argv) < 3 or sys.argv[1] not in ("읽기용", "최종"):
        sys.exit("사용법은 파일 맨 위 주석 참고")
    mode, src = sys.argv[1], Path(sys.argv[2])
    text = src.read_text(encoding="utf-8")
    if mode == "읽기용":
        dst = src.with_name(src.stem + "_읽기용.txt")
        dst.write_text(to_reading(text), encoding="utf-8", newline="\n")
        print(f"[읽기용] {dst}")
        return
    if len(sys.argv) > 3:
        md_reading = to_reading(Path(sys.argv[3]).read_text(encoding="utf-8"))  # 표식 없으면 여기서 중단
        if md_reading != text:
            print("[알림] 읽기용 txt가 대본 md와 다름 — 사용자가 읽기용을 직접 고쳤을 수 있음. 바뀐 내용을 md에도 반영할 것.")
    paras = regroup(reading_paras(text))
    joined = [" ".join(p) for p in paras]
    converted, leftover, digits = to_sound("\n".join(joined))
    paras_out = converted.split("\n")
    bad = sorted(set(m.group(0) for p in paras_out for pat in BAD for m in re.finditer(pat, p, re.M)))
    if bad:
        print("[경고] 낭독문에 남으면 안 되는 표시:", ", ".join(bad))
    if leftover:
        print("[경고] 한글 소리로 못 바꾼 영문(직접 고칠 것):", ", ".join(leftover))
    if digits:
        print("[안내] 남은 숫자(단순 숫자는 그대로 둬도 됨, 되도록 한글로):", ", ".join(digits))
    dst = src.with_name("대본_최종_낭독문.txt")
    dst.write_text("\n\n".join(paras_out) + "\n", encoding="utf-8", newline="\n")
    body = "\n".join(paras_out)
    sizes = [len(p) for p in paras]
    print(f"[최종] {dst} · 문단 {len(paras)}개(문장 {min(sizes)}~{max(sizes)}개/문단) · 공백 포함 {len(body):,}자 · 공백 제외 {len(re.sub(chr(92)+'s', '', body)):,}자")


if __name__ == "__main__":
    main()
