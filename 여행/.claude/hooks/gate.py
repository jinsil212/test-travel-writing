# 여행 원고 저장 차단 장치 (PreToolUse)
# 원고/{주제}/ 안의 기획.md·대본*.md 저장 전에 필수 조건을 검사한다.
# 조건 미달이면 exit 2 → 저장 거부, stderr 메시지가 Claude에게 전달된다.
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CASES = ROOT / "참고" / "03_사례21.md"


def block(msg):
    sys.stderr.write("[여행 원고 차단] " + msg + "\n")
    sys.exit(2)


def case_ids():
    if not CASES.exists():
        return []
    return re.findall(r"^##\s*(S\d{2})\b", CASES.read_text(encoding="utf-8"), re.M)


def new_content(tool, ti, path):
    if tool == "Write":
        return ti.get("content", "")
    text = path.read_text(encoding="utf-8") if path.exists() else ""
    edits = ti.get("edits") or [ti]
    for e in edits:
        old, new = e.get("old_string", ""), e.get("new_string", "")
        text = text.replace(old, new) if e.get("replace_all") else text.replace(old, new, 1)
    return text


def check_plan(folder, text):
    missing = []
    if not (folder / "자료.md").exists():
        missing.append("같은 폴더의 자료.md(조사 출처)가 먼저 있어야 함")
    for key in ("중복 확인", "핵심 메시지", "후킹", "블록", "썸네일", "도입", "확정"):
        if key not in text:
            missing.append(f"'{key}' 항목 없음")
    for n in range(1, 6):
        if not re.search(rf"유형\s*{n}", text):
            missing.append(f"유형{n} 점검 줄 없음")
    ids = case_ids()
    lost = [i for i in ids if i not in text]
    if lost:
        missing.append("사례 비교표에 빠진 번호: " + ", ".join(lost))
    if missing:
        block("기획.md 저장 불가 — 참고 자료를 다시 읽고 채울 것:\n- " + "\n- ".join(missing))


def check_script(folder, text):
    missing = []
    for f in ("자료.md", "기획.md", "선택.md"):
        if not (folder / f).exists():
            missing.append(f"{f} 없음")
    if "선택.md 없음" in missing:
        missing.append("1단계 확정안(제목·썸네일·도입 1개와 확정 이유)을 선택.md에 먼저 적어야 대본을 쓴다")
    if "흐름 대응표" not in text:
        missing.append("대본 위쪽에 '흐름 대응표'(참고한 사례 원고 번호와 적용한 흐름)가 없음 — CLAUDE.md 2단계 '흐름 원고 찾기'를 먼저 할 것")
    if "점검표" not in text:
        missing.append("대본 끝에 02_공통_원고작성.md의 점검표 결과가 없음")
    if missing:
        block("대본 저장 불가:\n- " + "\n- ".join(missing))


def main():
    data = json.loads(sys.stdin.buffer.read().decode("utf-8"))
    tool = data.get("tool_name", "")
    ti = data.get("tool_input", {}) or {}

    if tool in ("Bash", "PowerShell"):
        cmd = ti.get("command", "")
        writes = re.search(r">|Set-Content|Out-File|Add-Content|\btee\b|\bcp\b|\bmv\b|Copy-Item|Move-Item", cmd)
        # 실제 원고/{주제}/기획·대본·선택 파일 경로가 있을 때만 막는다 ("사례원고", "대본 단계" 같은 단어는 통과)
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
    if len(rel.parts) != 3 or rel.parts[0] != "원고":
        return
    name, folder = rel.parts[2], path.parent
    if name == "기획.md":
        check_plan(folder, new_content(tool, ti, path))
    elif name.startswith("대본"):
        check_script(folder, new_content(tool, ti, path))


if __name__ == "__main__":
    main()
