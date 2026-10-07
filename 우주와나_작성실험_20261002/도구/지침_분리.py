"""우주와나의 기존 세부 지침을 역할별 원문 묶음으로 생성·검증한다."""
from __future__ import annotations
import argparse
import hashlib
import json
import re
from pathlib import Path

SOURCES = {'COMMON': '_대본지침서.md', 'CHANNEL': '우주와나/채널설정.md',
           'CASES': '우주와나/수정·선택 사례.md',
           'WRITING': '우주와나/분석지/_원고쓰는법.md',
           'REVIEW': '우주와나/분석지/_검수기준서.md'}
PACKETS = {'common': '공통_원문.md', 'coordinator': '00_총괄_원문.md',
           'research': '01_조사_원문.md', 'plan': '02_기획_원문.md',
           'package': '03_제목썸네일_원문.md', 'opening': '04_도입_원문.md',
           'body': '05_본문클로징_원문.md', 'fact_review': '07_사실검수_원문.md',
           'flow_review': '08_흐름검수_원문.md'}
TIMESTAMP_HEADING = '(공용 타임스탬프 형식 — 다른 채널 전용 예외 뒤의 공통 항목)'

def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def digest(text): return hashlib.sha256(text.encode('utf-8')).hexdigest()
def read(p): return p.read_text(encoding='utf-8-sig')
def inside(root, name):
    p = (root / name).resolve()
    if not p.is_relative_to(root.resolve()): raise ValueError('범위 밖 경로: ' + name)
    return p

def segments(text):
    lines = text.splitlines(keepends=True)
    starts = [(0, 0, '(서두)')]
    fence = None
    for i, line in enumerate(lines):
        fm = re.match(r'^\s{0,3}(`{3,}|~{3,})', line)
        if fm:
            marker = fm[1][0]
            if fence is None: fence = marker
            elif marker == fence: fence = None
            continue
        if fence is not None: continue
        if line.startswith('**타임스탬프는 챕터 단위로 묶는다.**') and '극한실화 예외를 제외한 공용 형식' in line:
            starts.append((i, 3, TIMESTAMP_HEADING))
            continue
        hm = re.match(r'^(#{1,6})\s+(.+?)\s*$', line.rstrip('\r\n'))
        if hm: starts.append((i, len(hm[1]), line.rstrip('\r\n')))
    result = []
    for j, (start, level, heading) in enumerate(starts):
        end = starts[j + 1][0] if j + 1 < len(starts) else len(lines)
        if start == end: continue
        result.append({'line_start': start + 1, 'line_end': end, 'level': level,
                       'heading': heading, 'text': ''.join(lines[start:end])})
    assert ''.join(x['text'] for x in result) == text
    return result

def render(root):
    base = root / '지침' / '세부지침'
    routes_path = base / '배정규칙.json'
    routes = json.loads(read(routes_path))
    assert set(routes) == set(SOURCES.values()), '5개 원문 배정 규칙 필요'
    blocks = []
    source_hashes = {}
    for prefix, relative in SOURCES.items():
        source = inside(root, relative)
        source_hashes[relative] = sha(source)
        ss = segments(read(source))
        actual_heads = {s['heading'] for s in ss}
        unknown = set(routes[relative]) - actual_heads - {'(서두)'}
        raw_lines = {line.rstrip('\r\n') for line in read(source).splitlines()}
        assert unknown.issubset(raw_lines), f'{relative}: 실제 없는 heading {unknown - raw_lines}'
        stack = []
        for n, s in enumerate(ss, 1):
            while stack and stack[-1][0] >= s['level']: stack.pop()
            own = routes[relative].get(s['heading'])
            if own is None:
                # 상위 장의 배정을 잇되 새 상위 장은 자동으로 누락시키지 않는다.
                assert s['level'] > 2 and stack, f'{relative}: 명시 배정 누락 {s["heading"]}'
                own = stack[-1][1]
            assert isinstance(own, list) and set(own).issubset(PACKETS), s['heading']
            stack.append((s['level'], own, s['heading']))
            exclusion = ''
            if not own:
                assert any(t in k[2] for k in stack for t in ('따뜻한심리학', '부자경제', '극한실화')), '제외 근거 필요'
                exclusion = '다른 채널 전용 조항. 원문 보존, 우주와나 업무에는 미배정.'
            blocks.append({**s, 'id': f'{prefix}-{n:03d}', 'source': relative,
                           'roles': sorted(set(own)), 'source_sha256': source_hashes[relative],
                           'packet_roles': ['common'] if 'common' in own else sorted(set(own)),
                           'text_sha256': digest(s['text']), 'exclusion': exclusion})
    output = {}
    for role, filename in PACKETS.items():
        selected = [b for b in blocks if role in b['packet_roles']]
        assert selected, role + ': 배정 원문 없음'
        content = f'# 우주와나 {role} — 담당 세부 지침 원문\n\n'
        content += '기존 원문을 그대로 나눈 생성 문서입니다. 실행·읽기·충돌 처리는 지침/운영.md 하나를 기준으로 합니다. 모든 담당이 공통_원문.md를 읽으며, 공통 블록은 담당 묶음에 다시 복사하지 않습니다. 역할 책임은 원문_배정표.json의 roles, 실제 수록 위치는 packet_roles로 구별합니다.\n\n'
        content += '같은 원문 블록을 같은 버전으로 이미 전문 읽었으면 블록 ID로 대응을 확인하고 읽기 근거를 재사용할 수 있습니다. 실제 채택 견본 원문·분석지·합격원고 전문 정독은 별도로 유지합니다.\n\n'
        content += '출처별 블록 ID와 원문 줄을 표시했습니다. 사례의 사용자 발언·작업자 관찰·과거 상태를 구별합니다. 특정 편의 확정 문구·수치·분량은 그 편의 범위이며 과학 사실은 재검증합니다. 옛 경로는 읽기 참고입니다. 최신 사용자 요청 및 테스트 운영의 순차 관문·필수/권장 구분이 우선합니다.\n\n'
        content += '| 원문 블록 | 원문 위치 | 제목 |\n|---|---|---|\n'
        for b in selected:
            content += f'| {b["id"]} | {b["source"]}:{b["line_start"]} | {b["heading"].lstrip("# ").replace("|", "／")} |\n'
        for b in selected:
            content += f'\n---\n\n### 원문 블록 {b["id"]}\n\n출처: `{b["source"]}` {b["line_start"]}~{b["line_end"]}행. 아래는 원문 그대로입니다.\n\n'
            content += b['text'] + ('\n' if not b['text'].endswith('\n') else '')
        output['지침/세부지침/' + filename] = content
    index = {'version': 2, 'source_sha256': source_hashes,
             'routing_sha256': sha(routes_path),
             'packets': {path: digest(content) for path, content in output.items()},
             'blocks': [{k: v for k, v in b.items() if k != 'text'} for b in blocks],
             'coverage': {'source_blocks': len(blocks), 'assigned_blocks': sum(bool(b['roles']) for b in blocks),
                          'excluded_other_channel_blocks': sum(not b['roles'] for b in blocks),
                          'unassigned_applicable_blocks': 0}}
    common_ids = {b['id'] for b in blocks if 'common' in b['packet_roles']}
    overlaps = {role: sorted(common_ids & {b['id'] for b in blocks if role in b['packet_roles']}) for role in PACKETS if role != 'common'}
    assert all(not ids for ids in overlaps.values()), '공통과 담당 묶음의 중복'
    index['reading_overlap'] = overlaps
    output['지침/세부지침/원문_배정표.json'] = json.dumps(index, ensure_ascii=False, indent=2) + '\n'
    return output, index

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    root = args.root.resolve()
    output, index = render(root)
    if args.check:
        for relative, content in output.items():
            assert read(inside(root, relative)) == content, '원문 분리본 불일치: ' + relative
        for relative, expected in index['packets'].items():
            assert sha(inside(root, relative)) == expected, '분리본 실제 바이트 해시 불일치: ' + relative
    else:
        for relative, content in output.items():
            p = inside(root, relative)
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(content, encoding='utf-8', newline='\n')
    print(json.dumps({'mode': 'check' if args.check else 'generate', **index['coverage'],
                      'packets': len(PACKETS)}, ensure_ascii=False))

if __name__ == '__main__': main()
