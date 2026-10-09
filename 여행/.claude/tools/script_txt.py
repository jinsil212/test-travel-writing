# 대본 txt 변환 도구
# 사용:
#   python -X utf8 script_txt.py 읽기용 원고/{주제}/대본_vN.md
#       → 원고/{주제}/대본_vN_읽기용.txt  (장 제목 구분선 + 한 문장 한 줄 + 문단 사이 빈 줄)
#   python -X utf8 script_txt.py 최종 원고/{주제}/대본_vN_읽기용.txt [대본_vN.md]
#       → 원고/{주제}/대본_최종_낭독문.txt (장 제목 없이, 문단 1개 = 1줄, 문단 사이 빈 줄 — TTS용 클린 대본)
#       대본 md를 같이 주면 읽기용 txt가 md와 다른지(사용자가 읽기용을 직접 고쳤는지) 알려 준다.
# 본문 범위: md의 <!-- 본문 시작 --> ~ <!-- 본문 끝 -->.
import re
import sys
from pathlib import Path

RULE = "━━━━━━━━━━━━━━━━━━━━"
BAD = r"S\d{2}\b|\[각색\]|저희|<!--|\*\*|^#"


def body_of(md_text):
    if "<!-- 본문 시작 -->" not in md_text:
        sys.exit("[중단] md에 '<!-- 본문 시작 -->' 표시가 없음")
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
        out += [s.strip() for s in re.split(r"(?<=[.?!])\s+", line) if s.strip()]
        out.append("")
    return "\n".join(out).rstrip() + "\n"


def to_final(reading_text):
    paras, cur, skip = [], [], False
    for line in reading_text.splitlines():
        s = line.strip()
        if s == RULE:
            skip = not skip  # 구분선 사이(장 제목)는 버림
            continue
        if skip or (s.startswith("【") and s.endswith("】")):
            continue
        if not s:
            if cur:
                paras.append(" ".join(cur))
                cur = []
            continue
        cur.append(s)
    if cur:
        paras.append(" ".join(cur))
    return "\n\n".join(paras) + "\n", paras


def main():
    if len(sys.argv) < 3 or sys.argv[1] not in ("읽기용", "최종"):
        sys.exit(__doc__ or "사용법은 파일 맨 위 주석 참고")
    mode, src = sys.argv[1], Path(sys.argv[2])
    text = src.read_text(encoding="utf-8")
    if mode == "읽기용":
        dst = src.with_name(src.stem + "_읽기용.txt")
        dst.write_text(to_reading(text), encoding="utf-8", newline="\n")
        print(f"[읽기용] {dst}")
        return
    final, paras = to_final(text)
    if len(sys.argv) > 3:
        md_reading = to_reading(Path(sys.argv[3]).read_text(encoding="utf-8"))
        if md_reading != text:
            print("[알림] 읽기용 txt가 대본 md와 다름 — 사용자가 읽기용을 직접 고쳤을 수 있음. 바뀐 내용을 md에도 반영할 것.")
    bad = sorted(set(m.group(0) for p in paras for m in re.finditer(BAD, p, re.M)))
    if bad:
        print("[경고] 낭독문에 남으면 안 되는 표시:", ", ".join(bad))
    dst = src.with_name("대본_최종_낭독문.txt")
    dst.write_text(final, encoding="utf-8", newline="\n")
    body = "\n".join(paras)
    print(f"[최종] {dst} · 문단 {len(paras)}개 · 공백 포함 {len(body):,}자 · 공백 제외 {len(re.sub(chr(92)+'s', '', body)):,}자")


if __name__ == "__main__":
    main()
