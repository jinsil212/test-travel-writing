# -*- coding: utf-8 -*-
"""한입교양 — 우리 원고를 합격원고(사용자 최종본)와 벤치마크 18편에 나란히 계측한다.

사용법
  python _계측_원고.py <대본1.txt> [<대본2.txt> ...]
  열은 ① 넘긴 파일들 ② 합격원고 평균(_합격원고/) ③ 지식팩토리 평균 ④ 18편 전체 평균·범위.

보는 것 (겉모양만. 흐름·이해는 /대본검수가 본다)
  - 공백 제외 글자, 문장 수, 평균 문장 길이, 질문 비율
  - 어미: ~니다 / ~요 / ~죠 / ~다
  - 시청자 호출(~잖아요·~시죠·떠올려 보세요·여러분), 그림 부사(팍팍·벅벅·푹·훌쩍·기겁 …)
  - 연구·조사 인용체(연구가 있·조사에 따르면 …), 설명문 신호(~는 것이다·~라는 점), 밈·속어(채널 금지 → 0이어야 함)
  - 수치 밀도: 1,000자당 숫자 덩어리(아라비아 숫자 + 한글 숫자 단위)
"""
import io, os, re, sys, glob

HERE = os.path.dirname(os.path.abspath(__file__))
CH = os.path.dirname(HERE)
BENCH_DIR = os.path.join(HERE, '원문')
PASSED_DIR = os.path.join(CH, '_합격원고')

CALL = [r'잖아요', r'시죠', r'보세요', r'여러분', r'떠올려', r'않나요', r'않으세요', r'볼까요', r'오시죠', r'아시죠', r'하시죠']
VIVID = ['팍팍', '벅벅', '푹 ', '훌쩍', '기겁', '펄펄', '듬뿍', '흠씬', '꽂히', '기습', '다닥다닥', '쏟아', '백기', '두 손', '속수무책', '폭탄', '천지']
CITE = [r'연구가 있', r'연구에 따르', r'조사를 보면', r'조사에 따르', r'설명에 따르', r'기록도', r'학자', r'연구자', r'논문']
EXPLAIN = [r'는 것이다', r'라는 점', r'것입니다\.', r'셈입니다']
MEME = [r'ㅋㅋ', r'ㄹㅇ', r'개꿀', r'존맛', r'레전드', r'킹받', r'찐', r'갓', r'급식', r'노답', r'대박']
NUM = re.compile(r'(\d[\d,.]*|[일이삼사오육칠팔구십백천만억]+\s*(년|그램|밀리그램|리터|배|퍼센트|도|명|개|원|유로|파운드|세기|시간|분|초|킬로|미터|센티))')


def clean(text):
    out = []
    for line in text.splitlines():
        if line.startswith('#'):
            continue
        line = re.sub(r'\[\d+:\d\d(:\d\d)?\]', ' ', line)
        out.append(line)
    return '\n'.join(out)


def sentences(text):
    t = re.sub(r'\s+', ' ', text)
    parts = re.split(r'(?<=[.!?])\s+', t)
    return [p.strip() for p in parts if len(p.strip()) > 1]


def endings(sents):
    c = {'니다': 0, '요': 0, '죠': 0, '다': 0, '기타': 0}
    for s in sents:
        w = s.rstrip('.!?"”\' ')
        if w.endswith('니다'):
            c['니다'] += 1
        elif w.endswith('죠'):
            c['죠'] += 1
        elif w.endswith('요'):
            c['요'] += 1
        elif w.endswith('다'):
            c['다'] += 1
        else:
            c['기타'] += 1
    return c


def measure(text):
    t = clean(text)
    nospace = len(re.sub(r'\s', '', t))
    sents = sentences(t)
    n = max(len(sents), 1)
    e = endings(sents)
    q = sum(1 for s in sents if s.endswith('?') or re.search(r'(까요|나요|ㄹ까|을까)\s*[?.]?$', s))
    return {
        '공백 제외 글자': nospace,
        '문장 수': len(sents),
        '평균 문장 길이(공백 제외)': round(nospace / n, 1),
        '질문 비율 %': round(100 * q / n),
        '~니다 %': round(100 * e['니다'] / n),
        '~요 %': round(100 * e['요'] / n),
        '~죠 %': round(100 * e['죠'] / n),
        '~다 %': round(100 * e['다'] / n),
        '시청자 호출 /1000자': round(1000 * sum(len(re.findall(p, t)) for p in CALL) / max(nospace, 1), 1),
        '그림 부사 /1000자': round(1000 * sum(t.count(v) for v in VIVID) / max(nospace, 1), 1),
        '연구·조사 인용체': sum(len(re.findall(p, t)) for p in CITE),
        '설명문 신호(것이다·라는 점…)': sum(len(re.findall(p, t)) for p in EXPLAIN),
        '밈·속어(0이어야)': sum(len(re.findall(p, t)) for p in MEME),
        '수치 덩어리 /1000자': round(1000 * len(NUM.findall(t)) / max(nospace, 1), 1),
    }


SENT_KEYS = {'문장 수', '평균 문장 길이(공백 제외)', '질문 비율 %', '~니다 %', '~요 %', '~죠 %', '~다 %'}


def avg(rows, k):
    # 문장부호가 없는 자동자막(문장 수 20 미만)은 문장 단위 평균에서 뺀다
    rows = [r for r in rows if k not in SENT_KEYS or r['문장 수'] >= 20]
    v = [r[k] for r in rows]
    return (round(sum(v) / len(v), 1), '%s~%s' % (min(v), max(v))) if v else ('-', '-')


def main(paths):
    bench = [(os.path.basename(p), measure(io.open(p, encoding='utf-8', errors='ignore').read())) for p in sorted(glob.glob(os.path.join(BENCH_DIR, '*.txt')))]
    kf = [m for n, m in bench if n.startswith('지식팩토리')]
    allb = [m for n, m in bench]
    passed = [measure(io.open(p, encoding='utf-8', errors='ignore').read()) for p in sorted(glob.glob(os.path.join(PASSED_DIR, '*.txt'))) if not os.path.basename(p).startswith('README')]
    cols = [(os.path.basename(p), measure(io.open(p, encoding='utf-8', errors='ignore').read())) for p in paths]
    keys = list(measure('가다.').keys())
    print('| 항목 | ' + ' | '.join(n for n, _ in cols) + ' | 합격원고(%d) | 지식팩토리 평균(%d) | 18편 평균 | 18편 범위 |' % (len(passed), len(kf)))
    print('|---|' + '---|' * (len(cols) + 4))
    for k in keys:
        pa = avg(passed, k)[0] if passed else '-'
        ka = avg(kf, k)[0]
        aa, ar = avg(allb, k)
        print('| %s | ' % k + ' | '.join(str(m[k]) for _, m in cols) + ' | %s | %s | %s | %s |' % (pa, ka, aa, ar))
    print()
    print('문장 단위 항목(문장 수·길이·질문·어미)의 벤치마크 평균은 문장부호가 있는 자막만으로 냈다.')
    print('읽는 법: 합격원고 열이 1순위 기준이다(사용자가 고친 최종본). 지식팩토리는 직접 경쟁 채널. 18편 범위는 참고. 밈·속어는 채널 금지라 0이어야 한다.')


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass
    main(sys.argv[1:])
