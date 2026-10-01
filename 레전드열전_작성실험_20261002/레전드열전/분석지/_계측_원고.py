# -*- coding: utf-8 -*-
"""레전드 열전 — 우리 원고를 벤치마크(퇴근후헛소리 19편)와 나란히 계측한다.

사용법
  python _계측_원고.py <대본1.txt> [<대본2.txt> ...]
  (벤치마크 평균·범위는 같은 폴더의 원문/*.txt 19편에서 매번 다시 계산한다)

보는 것
  - 공백 제외 글자수, 종결어미 수, 종결어미 간 평균 글자수(≈문장 길이)
  - 종결어미 분포: 서술(~다, ~했다고 한다) 대 논평(~습니다, ~죠, ~네요, ~요)
  - 장치: 참고로 / 여러분 / 설·전해진다 / 구독 인사
  - 구어·요즘 비유 횟수, 설명문 신호(셈이·것이다·겁니다·정리하면 등) 횟수
  - 질문 수, 숫자 밀도(1,000자당 숫자 덩어리)

한계
  - 벤치마크는 자동자막이라 문장부호가 없다. 그래서 문장 길이는 종결어미 간 글자수로 잰다. 우리 원고도 같은 방식으로 재야 비교가 된다.
"""
import io, os, re, sys, glob

HERE = os.path.dirname(os.path.abspath(__file__))
BENCH_DIR = os.path.join(HERE, '원문')

PUNCT = '.,!?:;()[]{}<>~·… "\'“”‘’「」『』'

SPOKEN = [
    '양아치', '얻어 터', '얻어터', '튀었', '튀어', '꼬셔', '꼬시', '뽀록', '조인트', '빡쳐', '빡치',
    '뻥', '열 받', '열받', '털렸', '털린', '털리', '깨졌', '깨진', '얍삽', '쫄딱', '두들겨', '나가떨어',
    '요즘으로 치면', '지금 같으면', '오락실', '게임', '거들먹', '집적', '고철', '영감님', '아저씨',
    '열라', '그야말로', '무려', '쳐들어', '때려눕', '때려잡',
]
EXPLAIN = [
    (r'셈이', '셈이죠·셈입니다'),
    (r'것이다', '~는 것이다'),
    (r'겁니다', '~ㄴ 겁니다'),
    (r'라는 점', '~라는 점'),
    (r'정리하면', '정리하면'),
    (r'차례다', '~할 차례다'),
    (r'실마리', '실마리'),
    (r'흥미로운', '흥미로운 건'),
    (r'보여주지 않은', '영화가 보여주지 않은'),
]


def clean_bench(text):
    out = []
    for line in text.splitlines():
        if line.startswith('#'):
            continue
        line = re.sub(r'\[\d+:\d\d\]', ' ', line)
        line = line.replace('>>', ' ')
        line = re.sub(r'\[음악\]', ' ', line)
        out.append(line)
    return '\n'.join(out)


def classify_endings(text):
    c = {'다': 0, '다고한다': 0, '습니다': 0, '죠': 0, '네요': 0, '요': 0}
    words = [w.strip(PUNCT) for w in text.split()]
    words = [w for w in words if w]
    for i, w in enumerate(words):
        prev = words[i - 1] if i else ''
        hearsay = prev.endswith('다고') or prev.endswith('라고')
        if w.endswith('습니다') or w.endswith('입니다'):
            c['습니다'] += 1
        elif w.endswith('죠'):
            c['죠'] += 1
        elif w.endswith('네요'):
            c['네요'] += 1
        elif w.endswith('요'):
            c['요'] += 1
        elif w.endswith('다'):
            if hearsay and w == '한다':
                c['다고한다'] += 1
            else:
                c['다'] += 1
    return c


def measure(text):
    t = text
    nospace = len(re.sub(r'\s', '', t))
    e = classify_endings(t)
    total = sum(e.values()) or 1
    narr = e['다'] + e['다고한다']
    comm = e['습니다'] + e['죠'] + e['네요'] + e['요']
    m = {
        '공백 제외 글자': nospace,
        '종결어미 수': total,
        '종결어미 간 평균 글자(≈문장 길이)': round(nospace / total, 1),
        '서술 비율 %': round(100 * narr / total),
        '논평 비율 %': round(100 * comm / total),
        '  ~했다고 한다 %': round(100 * e['다고한다'] / total),
        '  ~습니다 %': round(100 * e['습니다'] / total),
        '  ~죠 %': round(100 * e['죠'] / total),
        '  ~네요 %': round(100 * e['네요'] / total),
        '참고로': len(re.findall(r'참고로', t)),
        '여러분': len(re.findall(r'여러분', t)),
        '설·전해진다·알려져': len(re.findall(r'(라는 설|설이 있|전해진다|전해지는|알려져 있|전해졌)', t)),
        '구독 인사': len(re.findall(r'구독과 좋아요', t)),
        '구어·요즘 비유': sum(len(re.findall(re.escape(s), t)) for s in SPOKEN),
        '설명문 신호(셈이·것이다·겁니다…)': sum(len(re.findall(p, t)) for p, _ in EXPLAIN),
        '질문(~까/~까요)': len(re.findall(r'(을까|ㄹ까|일까|했을까|까요)[\s?.]', t)),
        '숫자 덩어리 /1000자': round(1000 * len(re.findall(r'\d+', t)) / max(nospace, 1), 1),
    }
    return m


def fmt(v):
    return str(v)


def main(paths):
    bench = []
    for p in sorted(glob.glob(os.path.join(BENCH_DIR, '*.txt'))):
        bench.append(measure(clean_bench(io.open(p, encoding='utf-8').read())))
    keys = list(bench[0].keys()) if bench else list(measure('가다.').keys())
    cols = []
    for p in paths:
        txt = io.open(p, encoding='utf-8').read()
        if '[0:00]' in txt:
            txt = clean_bench(txt)
        cols.append((os.path.basename(p), measure(txt)))

    header = '| 항목 | ' + ' | '.join(n for n, _ in cols) + ' | 벤치마크 평균(%d편) | 벤치마크 범위 |' % len(bench)
    sep = '|---|' + '---|' * (len(cols) + 2)
    print(header)
    print(sep)
    for k in keys:
        vals = [b[k] for b in bench]
        if vals:
            avg = round(sum(vals) / len(vals), 1)
            rng = '%s~%s' % (min(vals), max(vals))
        else:
            avg, rng = '-', '-'
        row = '| %s | ' % k + ' | '.join(fmt(m[k]) for _, m in cols) + ' | %s | %s |' % (avg, rng)
        print(row)
    print()
    print('벤치마크 구어 표현이 실제로 쓰인 예: 양아치, 얻어 터졌다, 몰래 튀었다, 꼬셔도, 뽀록나, 조인트, 빡쳐서, 뻥, 열 받아, 얍삽이, 동전 교환, 요즘으로 치면')


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    sys.stdout.reconfigure(encoding='utf-8')
    main(sys.argv[1:])
