# 여행_v2 원고 저장 차단 장치 (PreToolUse)
# 원고/{주제}/ 안의 기획.md·대본*.md 저장 전에 필수 조건을 검사한다. 미달이면 exit 2 → 저장 거부.
# 검사: 뼈대가 합격원고 번호(F##)이고 실제 파일이 있는지 / 낭독 본문에 금지 구절·꼬리표·▷·🇺🇸가 없는지 /
#       핵심 문장이 본문에 2회 이상 반복되지 않는지 / 상단 메타(핵심 문장·제목·썸네일·경험 질문·상품 자리)·고정 댓글·점검표가 있는지
# 또 합격원고/_holdout/ 안의 파일은 검증 중 읽기·검색을 막는다(베끼기 방지).
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FOLDER = ROOT / "합격원고"
FORBID = [
    ("안내돼", "출처 헤지 '안내돼' — 확인된 사실은 단정으로, 기준일 문장 1회로 대신"),
    ("결론부터 말씀드리면", "벤치마크 상투구"),
    ("해주고 싶은 얘기", "벤치마크 상투구"),
    ("▷", "화면용 표 표식은 본문 밖에"),
    ("🇺🇸", "국기 이모지 금지"),
    ("저희", "1인칭은 '저'"),
    ("[각색]", "각색 경험담 금지 — 경험 질문으로 남길 것"),
]


def block(msg):
    sys.stderr.write("[여행_v2 차단] " + msg + "\n")
    sys.exit(2)


def f_ids():
    return sorted(p.name[:3] for p in FOLDER.glob("F[0-9][0-9]_*.txt"))


def new_content(tool, ti, path):
    if tool == "Write":
        return ti.get("content", "")
    text = path.read_text(encoding="utf-8") if path.exists() else ""
    for e in ti.get("edits") or [ti]:
        old, new = e.get("old_string", ""), e.get("new_string", "")
        text = text.replace(old, new) if e.get("replace_all") else text.replace(old, new, 1)
    return text


def norm(s):
    return re.sub(r"[\s.,!?~…'\"()·]", "", s)


def check_plan(folder, text):
    missing = []
    if not (folder / "자료.md").exists():
        missing.append("같은 폴더의 자료.md(조사 출처)가 먼저 있어야 함")
    for key in ("중복 확인", "핵심 질문", "각도", "상품", "유형", "뼈대", "제목", "썸네일"):
        if key not in text:
            missing.append(f"'{key}' 항목 없음")
    ids = re.findall(r"\bF\d{2}\b", text)
    if not ids:
        missing.append("뼈대가 합격원고 번호(F01~)로 적혀 있지 않음 — 합격원고/_색인.md에서 가장 가까운 1편을 고를 것")
    else:
        have = f_ids()
        bad = [i for i in set(ids) if i not in have]
        if bad:
            missing.append("합격원고에 없는 번호(검증 중 _holdout로 빠진 편 포함): " + ", ".join(sorted(bad)))
    if "🇺🇸" in text:
        missing.append("제목·썸네일에 국기 이모지 🇺🇸가 있음")
    if missing:
        block("기획.md 저장 불가:\n- " + "\n- ".join(missing))


def check_script(folder, text):
    missing = []
    for f in ("자료.md", "기획.md", "선택.md"):
        if not (folder / f).exists():
            missing.append(f"{f} 없음")
    if "<!-- 본문 시작 -->" not in text or "<!-- 본문 끝 -->" not in text:
        missing.append("낭독 본문 앞뒤 '<!-- 본문 시작 -->' / '<!-- 본문 끝 -->' 표식 없음")
        body = ""
    else:
        body = text.split("<!-- 본문 시작 -->")[1].split("<!-- 본문 끝 -->")[0]
    head = text.split("<!-- 본문 시작 -->")[0]
    for key in ("핵심 문장", "뼈대", "제목", "썸네일", "경험 질문", "상품"):
        if key not in head:
            missing.append(f"상단 메타에 '{key}' 없음")
    tail = text.split("<!-- 본문 끝 -->")[-1] if "<!-- 본문 끝 -->" in text else ""
    for key in ("고정 댓글", "점검표"):
        if key not in tail:
            missing.append(f"본문 아래에 '{key}' 없음")
    if "🇺🇸" in head:
        missing.append("제목·썸네일에 국기 이모지 🇺🇸가 있음")
    ids = re.findall(r"\bF\d{2}\b", head)
    if not ids:
        missing.append("뼈대 합격원고 번호(F##)가 상단에 없음")
    else:
        have = f_ids()
        bad = [i for i in set(ids) if i not in have]
        if bad:
            missing.append("합격원고에 없는 번호: " + ", ".join(sorted(bad)))
    if body:
        for word, why in FORBID:
            if word in body:
                missing.append(f"본문에 '{word}' 있음 — {why}")
        tags = re.findall(r"\[[^\]\n]{1,14}\]", body)
        if tags:
            missing.append("본문에 꼬리표 " + ", ".join(sorted(set(tags))[:6]) + " — 전환은 말로")
        if re.search(r"\bS\d{2}\b", body):
            missing.append("본문에 사례 번호 S##")
        m = re.search(r"핵심 문장\s*[:：]\s*(.+)", head)
        if m:
            key = norm(m.group(1))
            key = key[: max(12, int(len(key) * 0.6))]  # 앞 60%만 비교(어미 변형 허용)
            if len(key) >= 8 and norm(body).count(key) >= 2:
                missing.append("핵심 문장이 본문에 2회 이상 반복됨 — 도입 끝 또는 마무리 한 곳에서 1회만")
        # 분량: 뼈대 편 길이에는 맞추지 않는다(사용자 지시 2026-10-21). 극단적 축약만 막는 절대 하한.
        plain = re.sub(r"<!--.*?-->|^#.*$", "", body, flags=re.M | re.S)
        plain = re.sub(r"\s+", " ", plain).strip()
        n_body = len(plain)
        if n_body < 4500:
            missing.append(f"본문 {n_body:,}자 — 절대 하한 4,500자 미만")
        n_think = len(re.findall(r"라고 생각해요", body))
        if n_think > 3:
            missing.append(f"'~라고 생각해요' {n_think}회 — 3회 이하로('~추천해요'로 바로)")
        if "추천드리고 싶어요" in body:
            missing.append("'~추천드리고 싶어요' — '~추천해요'로")
    if missing:
        block("대본 저장 불가:\n- " + "\n- ".join(missing))


def main():
    data = json.loads(sys.stdin.buffer.read().decode("utf-8"))
    tool = data.get("tool_name", "")
    ti = data.get("tool_input", {}) or {}
    blob = json.dumps(ti, ensure_ascii=False)

    if "_holdout" in blob and (FOLDER / "_holdout").exists():
        block("합격원고/_holdout 안의 파일은 검증(hold-out) 중 읽기·검색·복사 금지")

    if tool in ("Bash", "PowerShell"):
        cmd = ti.get("command", "")
        writes = re.search(r">|Set-Content|Out-File|Add-Content|\btee\b|\bcp\b|\bmv\b|Copy-Item|Move-Item", cmd)
        target = re.search(r"(?<![가-힣])원고[/\\][^/\\\s\"']+[/\\](기획|대본|선택)[^/\\\s\"']*\.md", cmd)
        if writes and target:
            block("원고 파일(기획·대본·선택)은 셸 명령이 아니라 Write/Edit 도구로만 저장한다.")
        return

    fp = ti.get("file_path")
    if not fp:
        return
    path = Path(fp).resolve()
    try:
        rel = path.relative_to(ROOT)
    except ValueError:
        return
    if tool not in ("Write", "Edit", "MultiEdit"):
        return
    if len(rel.parts) != 3 or rel.parts[0] != "원고":
        return
    name, folder = rel.parts[2], path.parent
    if name == "기획.md":
        check_plan(folder, new_content(tool, ti, path))
    elif name.startswith("대본") and name.endswith(".md"):
        check_script(folder, new_content(tool, ti, path))


if __name__ == "__main__":
    main()
