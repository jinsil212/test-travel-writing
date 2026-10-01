# -*- coding: utf-8 -*-
"""PreToolUse(Write|Edit) 훅 — 대본 파일을 쓰기 전에 (1) 견본을 실제로 읽었는지 (2) 쓰기 전 설계가 있는지 검사한다.

사용: python .claude/hooks/require_sample_read.py <채널폴더명>
막는 대상: <채널>/원고/<편>/ 아래의 대본*.txt, 최종원고.md, 파트/*.txt
통과 조건(이 세션 transcript 기준):
  1) <채널>/분석지/_쓰기전에_읽는_것.md 를 Read 했다
  2) _합격원고/ 에 파일이 있으면 그중 1개 이상을 Read 했다 (1순위 견본)
  3) 견본(_합격원고/* 또는 분석지/원문/*.txt)을 서로 다른 3개 이상 Read 했다
  4) 그 편 폴더에 쓰기전_설계.md 가 있다 (문단표·용어표. 없으면 대본부터 쓰지 못한다)
하나라도 안 되면 permissionDecision=deny.
"""
import io, json, os, re, sys

CH = sys.argv[1] if len(sys.argv) > 1 else "채널"
E = re.escape(CH)
SCRIPT_RE = re.compile(E + r'[\\/]원고[\\/]([^\\/]+)[\\/](대본[^\\/]*\.txt|최종원고\.md|파트[\\/][^\\/]+\.txt)$')
SAMPLE_RE = re.compile(r'(분석지[\\/]원문[\\/][^\\/]+\.txt|_합격원고[\\/][^\\/]+\.(txt|md))')
GUIDE_RE = re.compile(r'_쓰기전에_읽는_것\.md')
BASH_READ_RE = re.compile(r'\b(cat|sed|head|tail|less|type)\b')


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
    m = SCRIPT_RE.search(fp)
    if not m:
        return
    episode_dir = fp[:m.start(2)].rstrip("\\/")

    tp = data.get("transcript_path") or ""
    if not tp or not os.path.exists(tp):
        deny("세션 transcript를 찾지 못해 견본 열람 여부를 확인할 수 없다. 견본과 _쓰기전에_읽는_것.md 를 Read 도구로 연 뒤 다시 시도한다.")

    samples, guide = set(), False
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
                if not text:
                    continue
                if GUIDE_RE.search(text):
                    guide = True
                for mm in SAMPLE_RE.finditer(text):
                    samples.add(os.path.basename(mm.group(1)))

    cwd = data.get("cwd") or os.getcwd()
    passed_dir = None
    for root in (cwd, os.path.dirname(cwd)):
        cand = os.path.join(root, CH, "_합격원고")
        if os.path.isdir(cand):
            passed_dir = cand
            break
    passed_files = []
    if passed_dir:
        passed_files = [n for n in os.listdir(passed_dir) if n.lower().endswith((".txt", ".md")) and not n.startswith("README")]
    passed_read = any(n in samples for n in passed_files)

    problems = []
    if not guide:
        problems.append("분석지/_쓰기전에_읽는_것.md 를 Read 하지 않았다")
    if passed_files and not passed_read:
        problems.append("_합격원고/ 에 합격본 %d개가 있는데 하나도 Read 하지 않았다. 합격본이 1순위 견본이다" % len(passed_files))
    if len(samples) < 3:
        problems.append("견본(_합격원고/* 또는 분석지/원문/*.txt)을 Read 한 것이 %d개다. 서로 다른 3편 이상을 전문으로 읽어야 한다" % len(samples))
    design = os.path.join(episode_dir, "쓰기전_설계.md")
    if not os.path.exists(design):
        problems.append("이 편 폴더에 쓰기전_설계.md(문단표·용어표)가 없다. 설계 없이 대본부터 쓰지 않는다 (공용 P0-14·S1-1)")
    if problems:
        deny("대본 쓰기 차단 — " + " / ".join(problems) + ". 채널설정 원칙 9. 처리한 뒤 다시 쓰면 통과한다.")


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    main()
