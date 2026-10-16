# 여행 원고 전체 정리 → HTML → (Chrome headless) PDF
import io, json, html, datetime
from pathlib import Path

BASE = Path(r"C:/Users/진실/Documents/테스트/여행")
rows = json.loads(io.open(BASE / "work/원고요약.json", encoding="utf-8").read())
by = {r["folder"]: r for r in rows}

GROUPS = [
    ("숙소 — 어디에 묵을까", ["뉴욕숙소", "뉴욕숙소_미드폼", "뉴욕한인민박호텔호스텔", "뉴욕장기숙소", "뉴욕여성숙소귀가", "뉴욕예약조건"]),
    ("교통·공항 — 어떻게 다닐까", ["뉴욕공항선택", "뉴욕지하철", "뉴욕도착첫날", "뉴욕마지막날짐", "뉴욕버스투어"]),
    ("일정·동선 — 며칠을 어떻게 쓸까", ["뉴욕예약순서", "뉴욕7일경비", "뉴욕비예보", "뉴욕전망대비예보", "뉴욕비오는날대체일정"]),
    ("근교·도시 선택 — 어디까지 갈까", ["동부3도시9일", "나이아가라당일", "나이아가라준비", "미국도시13곳", "미국4도시비교"]),
    ("티켓·패스·공연 — 뭘 미리 살까", ["뉴욕패스계산", "뉴욕패스비교", "뉴욕패스예약", "브로드웨이예매", "브로드웨이영어"]),
    ("쇼핑 — 뭘 어디서 살까", ["뉴욕기념품샵", "미국선물매장", "뉴욕쇼핑가격비교", "우드버리하루"]),
    ("주의사항 — 뭘 조심할까", ["뉴욕주의사항", "뉴욕팁결제"]),
    ("동행별 — 누구와 갈까", ["뉴욕동행별", "뉴욕친구", "뉴욕커플", "뉴욕아이동반", "뉴욕부모님일정", "뉴욕혼자여행", "뉴욕칸쿤신혼여행"]),
    ("준비물·날씨", ["뉴욕가을옷차림"]),
]

placed = {f for _, fs in GROUPS for f in fs}
rest = [r["folder"] for r in rows if r["folder"] not in placed]
if rest:
    GROUPS.append(("그 밖에", rest))


def status(r):
    if r["final"]:
        return "최종 낭독문 완료", "done"
    if r["version"] >= 1:
        return f"대본 v{r['version']}", "wip"
    if r["has_plan"]:
        return "기획까지", "plan"
    return "구상만", "idea"


def esc(s):
    return html.escape(s or "")


def short(s, n):
    s = (s or "").strip()
    return s if len(s) <= n else s[: n - 1] + "…"


total = len(rows)
done = sum(1 for r in rows if r["final"])
wip = sum(1 for r in rows if not r["final"] and r["version"] >= 1)
plan_only = total - done - wip
chars = sum(r["chars"] for r in rows)
today = datetime.date.today().strftime("%Y년 %m월 %d일")

parts = []
parts.append(f"""<!doctype html><html lang="ko"><head><meta charset="utf-8"><title>여행 원고 전체 정리</title>
<style>
@page {{ size: A4; margin: 16mm 14mm; }}
* {{ box-sizing: border-box; }}
body {{ font-family: "Malgun Gothic","맑은 고딕",sans-serif; color:#1a1a1a; font-size:10.5pt; line-height:1.55; margin:0; }}
h1 {{ font-size:24pt; margin:0 0 6px; letter-spacing:-.5px; }}
.sub {{ color:#666; font-size:10pt; }}
.cover {{ padding:52mm 0 0; text-align:center; page-break-after:always; }}
.stats {{ display:flex; gap:10px; justify-content:center; margin:26px 0 0; }}
.stat {{ border:1px solid #ddd; border-radius:8px; padding:12px 18px; min-width:90px; }}
.stat b {{ display:block; font-size:19pt; }}
.stat span {{ color:#777; font-size:9pt; }}
h2 {{ font-size:14pt; margin:22px 0 10px; padding:7px 10px; background:#f2f4f7; border-left:4px solid #333; page-break-after:avoid; }}
table {{ width:100%; border-collapse:collapse; font-size:9pt; }}
th,td {{ border-bottom:1px solid #e3e3e3; padding:5px 6px; text-align:left; vertical-align:top; }}
th {{ background:#fafafa; border-bottom:1.5px solid #ccc; }}
.card {{ border:1px solid #e0e0e0; border-radius:8px; padding:11px 13px; margin:0 0 10px; page-break-inside:avoid; }}
.card .t {{ font-weight:700; font-size:11pt; margin-bottom:5px; }}
.card .meta {{ color:#777; font-size:8.5pt; margin-bottom:7px; }}
.row {{ display:flex; gap:7px; margin:3px 0; font-size:9.5pt; }}
.row .k {{ color:#888; min-width:52px; flex:none; }}
.secs {{ color:#333; font-size:9pt; }}
.badge {{ display:inline-block; border-radius:10px; padding:1px 8px; font-size:8pt; margin-left:6px; }}
.done {{ background:#e6f4ea; color:#1e7a37; }}
.wip {{ background:#eef2fb; color:#2a4b9b; }}
.plan {{ background:#fdf3e3; color:#8a5a12; }}
.idea {{ background:#f3f3f3; color:#777; }}
</style></head><body>
<div class="cover">
<h1>여행 원고 전체 정리</h1>
<div class="sub">C:\\Users\\진실\\Documents\\테스트\\여행\\원고 · {today} 기준</div>
<div class="stats">
<div class="stat"><b>{total}</b><span>전체 원고</span></div>
<div class="stat"><b>{done}</b><span>최종 완료</span></div>
<div class="stat"><b>{wip}</b><span>대본 작성됨</span></div>
<div class="stat"><b>{plan_only}</b><span>기획·구상</span></div>
<div class="stat"><b>{chars//10000}만자</b><span>대본 총 분량</span></div>
</div>
</div>""")

# 한눈에 보기
parts.append('<h2>한눈에 보기</h2><table><tr><th style="width:4%">#</th><th style="width:17%">주제 폴더</th><th>제목</th><th style="width:9%">분량</th><th style="width:13%">상태</th></tr>')
i = 0
for gname, folders in GROUPS:
    for f in folders:
        r = by.get(f)
        if not r:
            continue
        i += 1
        st, cls = status(r)
        parts.append(
            f'<tr><td>{i}</td><td>{esc(r["folder"])}</td><td>{esc(short(r["title"], 62))}</td>'
            f'<td>{r["chars"]:,}자</td><td><span class="badge {cls}">{st}</span></td></tr>'
        )
parts.append("</table>")

# 그룹별 상세
for gname, folders in GROUPS:
    items = [by[f] for f in folders if f in by]
    if not items:
        continue
    parts.append(f'<h2>{esc(gname)} <span style="font-weight:400;color:#888;font-size:10pt">· {len(items)}편</span></h2>')
    for r in items:
        st, cls = status(r)
        parts.append('<div class="card">')
        parts.append(f'<div class="t">{esc(r["folder"])}<span class="badge {cls}">{st}</span></div>')
        parts.append(f'<div class="meta">{esc(short(r["title"], 150)) or "(제목 미정)"}</div>')
        if r["core"]:
            parts.append(f'<div class="row"><span class="k">한 줄 주제</span><span>{esc(short(r["core"], 180))}</span></div>')
        if r["thumb"]:
            parts.append(f'<div class="row"><span class="k">썸네일</span><span>{esc(short(r["thumb"], 140))}</span></div>')
        if r["sections"]:
            secs = " · ".join(s for s in r["sections"] if not s.startswith(("흐름", "약속", "점검", "글자", "출처")))
            parts.append(f'<div class="row"><span class="k">구성</span><span class="secs">{esc(short(secs, 420))}</span></div>')
        detail = f'{r["chars"]:,}자'
        if r["chars"]:
            detail += f' · 약 {round(r["chars"]/380)}분'
        if r["script_file"]:
            detail += f' · {r["script_file"]}'
        parts.append(f'<div class="row"><span class="k">분량</span><span>{esc(detail)}</span></div>')
        parts.append("</div>")

parts.append("</body></html>")

out_html = BASE / "work/여행원고_전체정리.html"
io.open(out_html, "w", encoding="utf-8").write("\n".join(parts))
print("HTML:", out_html)
