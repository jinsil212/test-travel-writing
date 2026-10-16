# -*- coding: utf-8 -*-
"""Stop 훅 — 이 세션에서 <채널>/원고/<편>/대본_v<N>.txt 를 썼으면, 같은 폴더에 검수_v<N>.md 가 대본보다 나중에 저장돼 있고
'판정:' 줄이 있어야 턴을 끝낼 수 있다. 없으면 한 번 막는다(stop_hook_active면 다시 막지 않고 알리기만 한다).
사용: python .claude/hooks/require_content_review.py <채널폴더명>
"""
import io, json, os, re, sys

CH = sys.argv[1] if len(sys.argv) > 1 else "채널"
SCRIPT_RE = re.compile(r'(.*' + re.escape(CH) + r'[\\/]원고[\\/][^\\/]+)[\\/]대본_v(\d+)\.txt$')


def main():
    try:
        raw = sys.stdin.buffer.read().decode("utf-8", "replace")
    except Exception:
        raw = sys.stdin.read()
    try:
        data = json.loads(raw) if raw.strip() else {}
    except Exception:
        return
    tp = data.get("transcript_path") or ""
    if not tp or not os.path.exists(tp):
        return
    written = {}
    with io.open(tp, encoding="utf-8", errors="ignore") as f:
        for line in f:
            if "tool_use" not in line:
                continue
            try:
                ev = json.loads(line)
            except Exception:
                continue
            for blk in (ev.get("message") or {}).get("content") or []:
                if isinstance(blk, dict) and blk.get("type") == "tool_use" and blk.get("name") in ("Write", "Edit"):
                    fp = (blk.get("input") or {}).get("file_path") or ""
                    m = SCRIPT_RE.match(fp)
                    if m:
                        written[fp] = (m.group(1), m.group(2))
    if not written:
        return
    missing = []
    for fp, (folder, ver) in written.items():
        if not os.path.exists(fp):
            continue
        review = os.path.join(folder, "검수_v%s.md" % ver)
        ok = False
        if os.path.exists(review) and os.path.getmtime(review) >= os.path.getmtime(fp) - 1:
            ok = bool(re.search(r"^판정:\s*(통과|미통과)", io.open(review, encoding="utf-8", errors="ignore").read(), re.M))
        if not ok:
            missing.append((os.path.basename(folder), ver))
    if not missing:
        return
    reason = ("내용 검수 없이 끝낼 수 없다. " + ", ".join("%s 대본_v%s" % (a, b) for a, b in missing) +
              " 에 대해 /대본검수 스킬 절차대로 차가운 독자 서브에이전트를 띄워 검수_v<N>.md 를 만들고(대본보다 나중에 저장), "
              "문제 행을 고친 뒤 맨 위에 '판정: 통과' 또는 '판정: 미통과' 를 적어라. 겉모양 계측만으로는 통과가 아니다.")
    if data.get("stop_hook_active"):
        sys.stdout.write(json.dumps({"systemMessage": "[내용 검수 미완] " + reason}, ensure_ascii=False))
        return
    sys.stdout.write(json.dumps({"decision": "block", "reason": reason,
                                 "systemMessage": "[내용 검수 미완] 턴 종료를 한 번 막음: " + ", ".join("%s v%s" % (a, b) for a, b in missing)},
                                ensure_ascii=False))


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    main()
