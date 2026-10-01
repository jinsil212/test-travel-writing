# -*- coding: utf-8 -*-
"""레전드 열전 벤치마크 계측 — 퇴근후헛소리 자동자막(json3) 기준.

하는 일
1) 원문/*.ko.json3 를 시간표시가 붙은 읽기용 .txt 로 변환
2) 편별로 길이, 말 속도, 도입 길이, 종결어미 분포, 장치 횟수를 계측
3) 결과를 _계측_19편.md 로 저장

한계
- 자동자막이라 문장부호가 거의 없다. 종결어미는 어미 문자열로 세며 문장 수가 아니다.
- 도입 끝은 캐치프레이즈 문구("파헤쳐"/"이야기를 시작"/"펼쳐본다" 등)가 나오는 줄의 끝으로 잡는다.
- 화면에만 나온 자막, 인터뷰 클립의 외국어는 그대로 포함된다.
"""
import json, re, io, os, glob

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, '원문')

# 편 정보: 파일 id -> (제목, 조회수(만), 공개일)
INFO = {
    'E1P9tRoPawo': ('실제 황비홍은 얼마나 싸움을 잘했나?', 37.8, '2026-09-14'),
    'WOqUkSuHpBE': ('성룡, 이연걸, 견자단이 싸우면 누가 이기나?', 22.1, '2026-09-08'),
    'ftR-JytwZkM': ('이소룡의 서머솔트킥을 대역했다는 백플립 달인 원화!', 58.2, '2026-09-02'),
    'SUzuSXxisOE': ('미스터 홍콩 겸 무술가 겸 악역 배우 양사!', 22.5, '2026-08-27'),
    'fcLFuEbSwLQ': ('삼합회에 맞서다 매니저를 잃은 이연걸!', 12.4, '2026-08-21'),
    'PSMtMy6i8PQ': ('임청하가 한국을 아직도 잊지 못하는 이유!', 4.1, '2026-08-16'),
    '5bczb1zFYmk': ('연애는 사랑과 전쟁, 인생은 야인시대였던 외팔이 검객 왕우!', 12.9, '2026-08-10'),
    'QUg7xTfTpuQ': ('나는 반 한국인이다. 성룡이 한국으로 도망치려 한 이유!', 1.9, '2026-08-03'),
    't1PH2oBbGuI': ('박정희 대통령 경호원이었던 부산 출신 발차기 4대퇴왕!', 5.4, '2026-07-28'),
    'LUXmdGJgr8g': ('해병대 출신의 무술영화 발차기 4대 퇴왕 왕호!', 12.9, '2026-07-23'),
    'nWMF_BsCkZ0': ('김일이 전설의 레슬러 루 테즈에게 실제 싸움을 건 이유!', 6.7, '2026-07-18'),
    'MfhmgkjuWgA': ('역도산이 약속을 깨고 기무라와 실전을 벌인 진짜 이유!', 1.5, '2026-07-12'),
    'rSwiJ9_mYfI': ('무술영화 역사상 최고의 악역! 한국인 무술가 황정리', 30.7, '2026-07-05'),
    'Y5-4h_xwz1U': ('시라소니와 무술 대결해서 이겼다는 합기도의 아버지 지한재!', 28.5, '2026-06-30'),
    'rHBml2KgDZU': ('최영의 도장깨기, 소뿔 자르기 어디까지 진실인가?', 15.5, '2026-06-24'),
    'CX_p0pmMd7s': ('아이디어 도둑 맞고 빡쳐서 홍콩가서 성공한 이소룡[이소룡 2편]', 3.0, '2026-06-18'),
    'sE20Zjo8ff8': ('UFC챔피언들과 이소룡과 싸워본 무술가들이 말하는 실전능력[이소룡1편]', 12.3, '2026-06-11'),
    'wBcqx1CwcPc': ('이소룡, 알리의 스승이자 미 국회의원들의 사부였던 남자! 이준구', 0.5, '2026-06-05'),
    '0Kj24VVbk30': ('성룡, 홍금보의 사부이자 이소룡의 절친이었던 한국인 황인식!', 18.3, '2026-05-31'),
}

HOOK_END = re.compile(r'(파헤쳐|팔쳐|펼쳐|해쳐)\s*(본다|봅니다|보겠다|보겠습니다)|이야기를 시작|시작해 본다|시작해본다')

ENDING_NAMES = ['~다 (서술)', '~했다고 한다 (전언·서술)', '~습니다', '~했다고 합니다 (전언·논평)', '~죠', '~네요', '기타 ~요']


def classify_endings(text):
    """어절 끝을 한 번씩만 판정한다. 자동자막이라 문장부호가 없어 어절 단위로 본다."""
    c = {n: 0 for n in ENDING_NAMES}
    PUNCT = '.,!?:;()[]{}<>~·… ' + '"' + "'" + '“”‘’「」『』'
    strip = lambda s: s.strip(PUNCT)
    words = [strip(w) for w in text.split()]
    words = [w for w in words if w]
    for i, w in enumerate(words):
        prev = words[i - 1] if i else ''
        hearsay = prev.endswith('다고') or prev.endswith('라고')
        if w.endswith('습니다') or w.endswith('입니다'):
            c['~했다고 합니다 (전언·논평)' if (hearsay and w in ('합니다', '한답니다')) else '~습니다'] += 1
        elif w.endswith('죠'):
            c['~죠'] += 1
        elif w.endswith('네요'):
            c['~네요'] += 1
        elif w.endswith('요'):
            c['기타 ~요'] += 1
        elif w.endswith('다'):
            c['~했다고 한다 (전언·서술)' if (hearsay and w == '한다') else '~다 (서술)'] += 1
    return c

DEVICES = [
    ('참고로', r'참고로'),
    ('여러분', r'여러분'),
    ('설/전해진다', r'(라는 설|설이 있|전해진다|전해지는|알려져 있)'),
    ('확인 안 됨', r'(확인은 안|확인이 안|확인하기 어|사실 여부)'),
    ('구독 인사', r'구독과 좋아요'),
]


def load(path):
    j = json.load(io.open(path, encoding='utf-8'))
    ev = []
    for e in j.get('events', []):
        segs = e.get('segs')
        if not segs:
            continue
        t = ''.join(s.get('utf8', '') for s in segs).replace('\n', ' ').strip()
        if not t:
            continue
        ev.append((e.get('tStartMs', 0), e.get('dDurationMs', 0), t))
    return ev


def to_text(ev):
    """10초 간격으로 시간표시를 붙인 읽기용 텍스트."""
    out, last = [], -10**9
    for st, du, t in ev:
        if st - last >= 10000:
            s = st // 1000
            out.append('\n[%d:%02d] ' % (s // 60, s % 60))
            last = st
        out.append(t + ' ')
    return ''.join(out).strip()


def measure(ev):
    full = ' '.join(t for _, _, t in ev)
    nospace = len(re.sub(r'\s', '', full))
    dur_ms = max(st + du for st, du, _ in ev)
    dur_min = dur_ms / 60000
    # 도입 끝 지점
    hook_ms, hook_chars = None, None
    acc = 0
    for st, du, t in ev:
        acc += len(re.sub(r'\s', '', t))
        if HOOK_END.search(t):
            hook_ms, hook_chars = st + du, acc
            break
    counts = classify_endings(full)
    total_end = sum(counts.values())
    dev = {n: len(re.findall(p, full)) for n, p in DEVICES}
    return dict(nospace=nospace, dur_min=dur_min, cpm=nospace / dur_min,
                hook_s=(hook_ms / 1000 if hook_ms else None), hook_chars=hook_chars,
                endings=counts, total_end=total_end, dev=dev)


rows = []
for path in sorted(glob.glob(os.path.join(SRC, '*.ko.json3'))):
    vid = os.path.basename(path).split('.')[0]
    ev = load(path)
    txt = to_text(ev)
    title, views, date = INFO.get(vid, (vid, 0, ''))
    io.open(os.path.join(SRC, '%s_%s.txt' % (date, re.sub(r'[\\/:*?"<>|!,\[\]]', '', title)[:28])), 'w',
            encoding='utf-8').write('# %s\n# https://youtu.be/%s  조회수 %s만  %s\n\n%s\n' % (title, vid, views, date, txt))
    m = measure(ev)
    m.update(vid=vid, title=title, views=views, date=date)
    rows.append(m)

rows.sort(key=lambda r: -r['views'])

L = []
L.append('# 레전드 열전 — 벤치마크 계측 (퇴근후헛소리 롱폼 19편)\n')
L.append('자동자막(json3)을 `_계측.py`로 계측했다. 자동자막이라 문장부호가 없어 **문장 수가 아니라 어미 문자열 출현 횟수**를 센다.\n')
L.append('| 편 | 조회수(만) | 길이(분) | 공백제외 글자 | 말속도(자/분) | 도입 끝(초) | 도입 글자 |')
L.append('|---|---|---|---|---|---|---|')
for r in rows:
    L.append('| %s | %.1f | %.1f | %d | %d | %s | %s |' % (
        r['title'][:24], r['views'], r['dur_min'], r['nospace'], round(r['cpm']),
        ('%.0f' % r['hook_s']) if r['hook_s'] else '-', r['hook_chars'] or '-'))

cpms = [r['cpm'] for r in rows]
hooks = [r['hook_s'] for r in rows if r['hook_s']]
hookc = [r['hook_chars'] for r in rows if r['hook_chars']]
lens = [r['nospace'] for r in rows]
mins = [r['dur_min'] for r in rows]
L.append('\n## 요약 (실측)\n')
L.append('| 항목 | 최소 | 최대 | 평균 |')
L.append('|---|---|---|---|')
L.append('| 영상 길이(분) | %.1f | %.1f | %.1f |' % (min(mins), max(mins), sum(mins)/len(mins)))
L.append('| 공백 제외 글자 | %d | %d | %d |' % (min(lens), max(lens), sum(lens)/len(lens)))
L.append('| 말속도(자/분) | %d | %d | %d |' % (min(cpms), max(cpms), sum(cpms)/len(cpms)))
L.append('| 도입 길이(초) | %.0f | %.0f | %.0f |' % (min(hooks), max(hooks), sum(hooks)/len(hooks)))
L.append('| 도입 글자(공백 제외) | %d | %d | %d |' % (min(hookc), max(hookc), sum(hookc)/len(hookc)))

L.append('\n## 종결어미 분포 (어미 출현 횟수 기준 %)\n')
L.append('| 편 | ' + ' | '.join(ENDING_NAMES) + ' | 합계 |')
L.append('|---' * (len(ENDING_NAMES) + 2) + '|')
agg = {n: 0 for n in ENDING_NAMES}
tot = 0
for r in rows:
    c = r['endings']; t = r['total_end'] or 1
    L.append('| %s | ' % r['title'][:16] + ' | '.join('%d%%' % round(c[n] * 100 / t) for n in ENDING_NAMES) + ' | %d |' % r['total_end'])
    for n in ENDING_NAMES:
        agg[n] += c[n]
    tot += r['total_end']
L.append('| **전체** | ' + ' | '.join('**%d%%**' % round(agg[n] * 100 / tot) for n in ENDING_NAMES) + ' | %d |' % tot)

narr = agg['~다 (서술)'] + agg['~했다고 한다 (전언·서술)']
comm = tot - narr
L.append('\n서술층(~다, ~했다고 한다) 대 논평층(~습니다, ~죠, ~네요, ~요) = **%d%% 대 %d%%**\n' % (
    round(narr * 100 / (narr + comm)), round(comm * 100 / (narr + comm))))

L.append('## 장치 횟수 (편당)\n')
L.append('| 편 | ' + ' | '.join(n for n, _ in DEVICES) + ' |')
L.append('|---' * (len(DEVICES) + 1) + '|')
for r in rows:
    L.append('| %s | ' % r['title'][:16] + ' | '.join(str(r['dev'][n]) for n, _ in DEVICES) + ' |')
for n, _ in DEVICES:
    v = [r['dev'][n] for r in rows]
    L.append('\n- %s: 최소 %d, 최대 %d, 평균 %.1f' % (n, min(v), max(v), sum(v) / len(v)))

io.open(os.path.join(HERE, '_계측_19편.md'), 'w', encoding='utf-8').write('\n'.join(L) + '\n')
print('\n'.join(L[:8]))
print('...')
print('말속도 평균 %d자/분, 도입 평균 %.0f초' % (sum(cpms)/len(cpms), sum(hooks)/len(hooks)))
print('서술 %d%% : 논평 %d%%' % (round(narr*100/(narr+comm)), round(comm*100/(narr+comm))))
