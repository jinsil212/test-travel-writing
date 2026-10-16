# 여행 원고 전체 요약 수집 — 각 주제 폴더에서 제목·핵심메시지·구성·분량·상태를 뽑는다
import io, json, re, sys
from pathlib import Path

ROOT = Path(r"C:/Users/진실/Documents/테스트/여행/원고")


def read(p):
    try:
        return io.open(p, encoding="utf-8").read()
    except Exception:
        return ""


def latest_script(folder):
    cands = sorted(folder.glob("대본_v*.md"), key=lambda p: p.stat().st_mtime)
    cands = [c for c in cands if "읽기용" not in c.name]
    return cands[-1] if cands else None


def body_of(text):
    if "<!-- 본문 시작 -->" in text and "<!-- 본문 끝 -->" in text:
        return text.split("<!-- 본문 시작 -->")[1].split("<!-- 본문 끝 -->")[0]
    # 마커가 없는 옛 형식: 점검표 앞까지
    m = re.split(r"\n## 점검표", text)
    return m[0] if m else text


def first_after(text, pattern, limit=3):
    m = re.search(pattern, text)
    if not m:
        return ""
    tail = text[m.end():].strip().splitlines()
    out = []
    for line in tail:
        s = line.strip()
        if not s:
            if out:
                break
            continue
        if s.startswith("#"):
            break
        out.append(s)
        if len(out) >= limit:
            break
    return " ".join(out)


rows = []
for folder in sorted(ROOT.iterdir()):
    if not folder.is_dir():
        continue
    plan = read(folder / "기획.md")
    pick = read(folder / "선택.md")
    sp = latest_script(folder)
    script = read(sp) if sp else ""

    title = ""
    pats = [r"^- 제목:\s*(.+)$", r"^\s*[-*]\s*\*\*제목[^:：]*[:：]\*\*\s*(.+)$",
            r"^\s*[-*]\s*제목[^:：]*[:：]\s*(.+)$", r"^\*\*제목[^:：]*[:：]\*\*\s*(.+)$"]
    for src in (script, pick, plan):
        for pat in pats:
            for m in re.finditer(pat, src, re.M):
                cand = m.group(1).strip().strip("`")
                if "|" in cand or len(cand) < 10:
                    continue
                title = cand
                break
            if title:
                break
        if title:
            break
    emoji = "🇺🇸🗽🍻🇲🇽🛍️❤️🚨🇰🇷"
    bad = ("제목 블록", "확정 이유", "약속", "빼기로")
    if not title or any(b in title for b in bad) or "[" not in title:
        best = ""
        for src in (script, pick, plan):
            for line in src.splitlines():
                s = line.strip().lstrip("-*# ").strip()
                s = re.sub(r"^\**제목[^:：]*[:：]\**\s*", "", s).strip().strip("`")
                if "|" in s or "[" not in s or len(s) < 25:
                    continue
                if not any(ch in s for ch in emoji):
                    continue
                if any(b in s for b in bad):
                    continue
                best = s
                break
            if best:
                break
        if best:
            title = best

    thumb = ""
    for pat in [r"^- 썸네일:\s*(.+)$", r"\*\*썸네일:\*\*\s*(.+)$"]:
        m = re.search(pat, script, re.M) or re.search(pat, pick, re.M)
        if m:
            thumb = m.group(1).strip()
            break

    core = ""
    m = re.search(r"\*\*핵심 주제 한 문장:\*\*\s*(.+)", script)
    if m:
        core = m.group(1).strip()
    if not core:
        core = first_after(plan, r"##\s*1\.\s*핵심 메시지.*\n", 2)

    hooks = first_after(plan, r"##\s*2\.\s*후킹 포인트.*\n", 3)

    dup = first_after(plan, r"판정:\s*", 1)

    body = body_of(script)
    sections = [l.strip("# ").strip() for l in body.splitlines() if l.startswith("## ")]
    nar = "\n".join(l for l in body.splitlines() if not l.startswith("##"))
    chars = len(nar.strip())

    files = sorted(p.name for p in folder.iterdir() if p.is_file())
    final = any(n.startswith("대본_최종") for n in files)
    vmax = max([int(m.group(1)) for n in files for m in [re.match(r"대본_v(\d+)\.md$", n)] if m] or [0])

    rows.append({
        "folder": folder.name,
        "title": title,
        "thumb": thumb,
        "core": core,
        "hooks": hooks,
        "dup": dup,
        "sections": sections,
        "chars": chars,
        "version": vmax,
        "final": final,
        "has_plan": bool(plan),
        "script_file": sp.name if sp else "",
        "mtime": max((p.stat().st_mtime for p in folder.iterdir() if p.is_file()), default=0),
    })

io.open(r"C:/Users/진실/Documents/테스트/여행/work/원고요약.json", "w", encoding="utf-8").write(
    json.dumps(rows, ensure_ascii=False, indent=1)
)
print("폴더", len(rows), "개")
for r in rows:
    print(f"{r['folder']:<22} v{r['version']}{'·최종' if r['final'] else ''} {r['chars']:>5}자 섹션{len(r['sections']):>2} | {r['title'][:40]}")
