"""Bind the manually reviewed policy rows and independent reports to one version.

No verdict is inferred from the script. Missing/failed reviews remain blocked.
"""
from pathlib import Path
import csv
import importlib.util
import json
import sys

root = Path(__file__).resolve().parent
repo = root.parents[1]
spec = importlib.util.spec_from_file_location('gate', repo / '_도구' / 'script-gate.py')
gate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gate)
version = sys.argv[1]
policy_path = root / f'규칙대조_{version}.tsv'
if not policy_path.exists():
    policy_path = root / '규칙대조.tsv'
basis_path = root / f'검토근거_{version}.md'
if not basis_path.exists():
    basis_path = root / '검토근거.md'
case = gate.new_case(root / f'대본_{version}.txt', repo / '_대본지침서.md', '채널미정', 'main-author')
rows = list(csv.DictReader(policy_path.open(encoding='utf-8'), delimiter='\t'))
used = set()
basis = {
    'scope': '주제는 송시열의 말이 왕과 조정의 결정에 영향을 준 이유다.',
    'prior': '직전 두 편의 실제 발행 순서는 미확인이다.',
    'angle': '기획 방향: 왕과 가까웠다는 추상 해설에서 끝내지 않고,',
    'packaging': '클릭 이유: 왕도 아닌 송시열의 말에 왕과 관리들이 반응한 이유를 알고 싶다.',
    'language': '기획어를 대본으로 풀기: 신임 → 왕이 글을 보내 함께 나라 일을 하자고 부름.',
    'bench': '이원익의 저장 제목은 왕들이 왜 그를 죽이지 못했는지 묻는다.',
    'events': '군사 충원·유계 등용·상복 규정·스승들의 생애·학자 간 별도 논쟁은 이번 질문을 답하는 데 필수적이지 않아 제외했다.',
    'limits': '실제 음성으로 듣지 않았다.',
    'facts': '이 기록에서 분명히 확인되는 범위를 넘어 전체 공사가 영구 폐지되었다고 쓰지 않는다.',
    'process': '두 번의 서로 다른 수정과 판본별 독립 검토를 기록한다.',
    'hook': '훅 경계는 왕의 반응과 관리들의 행동을 보겠다는 약속이 끝나고 사제 관계라는 첫 근거를 제시하는 자리다.',
    'ending': '마지막은 책임 추궁 요청에 대한 숙종의 응답으로 한 번만 닫는다.',
    'revisions': '두 번째 수정은 조립본의 중복·이해 누락·행위 주체를 대조했다.',
    'metrics': '자동 계측값과 수동 기능 판정은 구분한다.',
}
for rule in case['rules']:
    matches = [(i, row) for i, row in enumerate(rows) if rule['section'].startswith(row['selector'])]
    if len(matches) != 1:
        raise SystemExit(f'Expected exactly one manually authored disposition: {rule["section"]}: {matches}')
    idx, row = matches[0]
    if idx in used:
        raise SystemExit(f'One disposition accidentally covered multiple rules: {row["selector"]}')
    used.add(idx)
    rule['status'] = {'pass': 'pass', 'na': 'not_applicable', 'pending': 'pending'}[row['status']]
    rule['reason'] = row['reason']
    key = row['basis']
    if key in ('flow', 'approval'):
        ev = gate.evidence(root / '흐름안.md', '이는 흐름 승인이지 아직 작성되지 않은 개정 원고의 최종 승인이 아니다.')
    else:
        ev = gate.evidence(basis_path, basis[key])
    rule['evidence'] = [gate.evidence(policy_path, row['reason']), ev]
if len(used) != len(rows):
    raise SystemExit('Unused policy dispositions: ' + str([r for i, r in enumerate(rows) if i not in used]))

for role, quote in {
    'brief': basis['scope'],
    'benchmark': '선택한 이원익 벤치마크 원문 17,433자를 준비 단계에서 세 구간으로 끝까지 읽었다.',
    'channel': '채널은 채널미정, 역사 초심자 대상 존댓말 설명체다.',
    'approved_or_absence': '`채널미정/_합격원고/` 경로가 없는 것을 다시 확인했다.',
    'prior_or_absence': basis['prior'],
}.items():
    case['inputs'].append({'role': role, 'evidence': [gate.evidence(basis_path, quote)]})
binding = {'draft_sha256': case['draft']['sha256'], 'guide_sha256': case['guide']['sha256']}
case['plan_approval'] = dict(binding, kind='user_plan', evidence=[gate.evidence(root / '흐름안.md', '사용자가 `ㅇ`으로 승인했다.')])
for filename, axes in [(f'사실검토_{version}.json', ['facts']), (f'독자검토_{version}.json', ['comprehension', 'engagement', 'promise', 'repetition'])]:
    report_path = root / filename
    if not report_path.exists():
        continue
    doc = json.loads(gate.read(report_path))
    for axis in axes:
        entry = doc['axes'][axis]
        case['reviews'].append({
            'draft_sha256': doc['draft_sha256'], 'guide_sha256': doc['guide_sha256'],
            'reviewer': doc['reviewer'], 'method': doc['method'], 'axis': axis,
            'verdict': entry['verdict'], 'report': gate.snapshot(report_path),
            'evidence': [gate.evidence(report_path, entry['reason'])],
        })
        for finding in entry['findings']:
            case['findings'].append(dict(finding, status='open'))
case['final_approval'] = None
output = root / sys.argv[2]
gate.write_json(output, case, exclusive=True)
errors = gate.validate(case)
print(json.dumps({'case': str(output), 'rules': len(rows), 'reviews': len(case['reviews']), 'errors': errors}, ensure_ascii=False, indent=2))
