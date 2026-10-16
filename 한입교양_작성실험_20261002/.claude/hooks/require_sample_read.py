# -*- coding: utf-8 -*-
"""PreToolUse(Write|Edit) 훅 — 대본 파일을 쓰기 전에 정답원고(_합격원고/)를 전부 읽었는지만 검사한다.

사용: python .claude/hooks/require_sample_read.py <채널폴더명>
막는 대상: <채널>/원고/<편>/ 아래의 대본*.txt, 최종원고.md, 파트/*.txt
통과 조건: 이 세션에서 _합격원고/ 의 원고 파일(README 제외)을 하나도 빠짐없이 Read 했다.
"""
import io, json, os, re, sys

CH = sys.argv[1] if len(sys.argv) > 1 else "채널"
E = re.escape(CH)
SCRIPT_RE = re.compile(E + r'[\\/]원고[\\/]([^\\/]+)[\\/](대본[^\\/]*\.txt|최종원고\.md|파트[\\/][^\\/]+\.txt)$')
SAMPLE_RE = re.compile(r'_합격원고[\\/]([^\\/"\'\s]+\.(txt|md))')
BASH_READ_RE = re.compile(r'\b(cat|sed|head|tail|less|type|Get-Content)\b')


def deny(reason):
    sys.stdout.write(json.dumps({
        "hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny",
                               "permissionDecisionReason": reason},
        "systemMessage": "[대본 쓰기 차단] " + reason}, ensure_ascii=False))
    sys.exit(0)


def main():
    try:
        raw = sys.stdin.buffer.read().decode("utf-8", "replace")
    except Exception:
        raw = sys.stdin.read()
    try:
        data = json.loads(raw) if raw.strip() else {}
    except Exception:
        return
    fp = (data.get("tool_input") or {}).get("file_path") or ""
    if not SCRIPT_RE.search(fp):
        return

    cwd = data.get("cwd") or os.getcwd()
    passed_dir = None
    for root in (cwd, os.path.dirname(cwd)):
        cand = os.path.join(root, CH, "_합격원고")
        if os.path.isdir(cand):
            passed_dir = cand
            break
    if not passed_dir:
        return
    passed = [n for n in os.listdir(passed_dir) if n.lower().endswith((".txt", ".md")) and not n.startswith("README")]
    if not passed:
        return

    tp = data.get("transcript_path") or ""
    if not tp or not os.path.exists(tp):
        deny("세션 기록을 찾지 못해 정답원고 열람 여부를 확인할 수 없다. _합격원고/ 의 원고를 Read로 연 뒤 다시 쓴다.")

    read = set()
    with io.open(tp, encoding="utf-8", errors="ignore") as f:
        for line in f:
            if "tool_use" not in line:
                continue
            try:
                ev = json.loads(line)
            except Exception:
                continue
            for blk in (ev.get("message") or {}).get("content") or []:
                if not isinstance(blk, dict) or blk.get("type") != "tool_use":
                    continue
                name, inp = blk.get("name") or "", blk.get("input") or {}
                text = ""
                if name == "Read":
                    text = inp.get("file_path") or ""
                elif name in ("Bash", "PowerShell"):
                    cmd = inp.get("command") or ""
                    if BASH_READ_RE.search(cmd):
                        text = cmd
                for mm in SAMPLE_RE.finditer(text):
                    read.add(mm.group(1))

    missing = [n for n in passed if n not in read]
    if missing:
        deny("정답원고를 다 읽지 않았다 — 안 읽은 것: " + ", ".join(missing) + ". _합격원고/ 의 원고를 전부 Read로 끝까지 읽은 뒤 다시 쓴다.")


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    main()
