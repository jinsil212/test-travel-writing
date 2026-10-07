"""우주와나 실험 전용 단계 관문. Python 표준 라이브러리만 사용."""
from __future__ import annotations
import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / '실험' / '에피소드'
GUIDES = ROOT / '지침' / '에이전트'
ROLES = {'research': '01_조사.md', 'plan': '02_기획.md', 'package': '03_제목썸네일.md',
         'opening': '04_도입.md', 'body': '05_본문클로징.md', 'review': '06_독립검수.md',
         'fact_review': '06_독립검수.md', 'flow_review': '06_독립검수.md', 'coordinator': '00_총괄.md'}
VALIDATED = set()
CHECKS = {
 'research': ['sources', 'uncertainty', 'briefing'],
 'plan': ['question_answer', 'scope', 'flow', 'benchmark', 'length_material'],
 'package': ['user_examples', 'candidate_coverage', 'same_promise', 'standalone', 'image_prompts'],
 'opening': ['benchmark_before_writing', 'weakness_not_copied', 'same_promise', 'beginner', 'transition'],
 'part': ['necessary', 'facts', 'connection', 'language', 'new_value'],
 'closing': ['promise_paid', 'new_meaning', 'no_repetition'],
 'final_fact': ['claims_sources', 'numbers_conditions', 'future_hypothesis', 'image_sources'],
 'final_flow': ['promise_chain', 'beginner', 'no_tangents_repetition', 'natural_language', 'latest_requests', 'length'],
}

class GateError(ValueError): pass

def require(ok, message):
    if not ok: raise GateError(message)

def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def read(path): return path.read_text(encoding='utf-8-sig')
def load(path): return json.loads(read(path))
def save(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + '.tmp')
    temp.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    temp.replace(path)

def inside(root, relative):
    require(isinstance(relative, str) and relative.strip(), '빈 경로')
    path = (root / relative).resolve()
    require(path.is_relative_to(root.resolve()), '작업 범위를 벗어난 경로')
    return path

def episode(name):
    require(bool(re.fullmatch(r'[\w가-힣-]{1,80}', name)), '편 이름은 문자·숫자·밑줄·하이픈만')
    return inside(BASE, name)

def rule_snapshot():
    files = [ROOT / '_대본지침서.md', ROOT / '우주와나' / '채널설정.md',
             ROOT / '우주와나' / '수정·선택 사례.md',
             ROOT / '우주와나' / '분석지' / '_원고쓰는법.md',
             ROOT / '우주와나' / '분석지' / '_검수기준서.md', ROOT / '지침' / '운영.md']
    files += [GUIDES / name for name in sorted(set(ROLES.values()))]
    require(all(p.is_file() for p in files) and len(files) >= 12, '역할 지침 또는 원문 기준 누락')
    return {str(p.relative_to(ROOT)): sha(p) for p in files}

def stages(state):
    return ['research', 'plan', 'package', 'opening'] + [f'part_{i:02d}' for i in range(1, state['parts'] + 1)] + ['closing', 'final']

def writer(stage):
    if stage.startswith('part_') or stage == 'closing': return 'body'
    return 'coordinator' if stage == 'final' else stage

def file_for(stage): return stage + ('.txt' if stage.startswith('part_') or stage in ('opening', 'closing', 'final') else '.md')
def receipts(stage): return ['final_fact', 'final_flow'] if stage == 'final' else [stage]
def criteria(stage): return CHECKS['part' if stage.startswith('part_') else stage]

def state_for(ep):
    VALIDATED.clear()
    state = load(ep / 'state.json')
    require(state['rules'] == rule_snapshot(), '지침 변경: 기존 통과 기록 재사용 금지. 새 실행 폴더에서 재검토')
    require(state['request_sha256'] == sha(ep / 'request.md'), '최신 요청 변경: 기존 통과 기록 재사용 금지. 새 실행으로 재검토')
    require(state['mode'] in ('ASK', 'AUTO'), '잘못된 진행 모드')
    return state

def deps(ep, state, stage):
    result = {}
    for prev in stages(state)[:stages(state).index(stage)]:
        validate_stage(ep, state, prev)
        for fn in [file_for(prev)] + ['review_' + key + '.json' for key in receipts(prev)]:
            result[fn] = sha(ep / fn)
    return result

def actor(state, role, actor_id):
    require(role in ROLES and state['actors'].get(role) == actor_id, '등록된 담당 에이전트와 일치하지 않음')

def reading(ep, state, role):
    path = ep / ('read_' + role + '.json')
    require(path.is_file(), f'{role}: 원문 열람 근거가 없음')
    record = load(path)
    actor(state, role, record['actor'])
    required = [f'지침/에이전트/{ROLES[role]}', '지침/운영.md', '우주와나/채널설정.md', '우주와나/수정·선택 사례.md', '_대본지침서.md']
    require(all(p in record['files'] for p in required), f'{role}: 필수 역할·공통 원문 열람 기록 누락')
    for relative, item in record['files'].items():
        path = inside(ROOT, relative)
        require(path.is_file() and sha(path) == item['sha256'], '열람한 자료가 바뀜: ' + relative)
        require(item['quote'].strip() and item['quote'] in read(path), '열람 근거 구절 불일치: ' + relative)
        require(item.get('application', '').strip(), '이번 작업 적용 설명 누락')
    # 파일 열람/구절 일치가 이해·전문 정독을 증명하지는 않는다. 독립 검수가 확인한다.

def validate_receipt(ep, state, stage, key, item):
    role = 'fact_review' if key == 'final_fact' else 'flow_review' if key == 'final_flow' else 'review'
    actor(state, role, item.get('actor'))
    require(item['actor'] != state['actors'][writer(stage)], '작성자 자기 검수 통과 금지')
    reading(ep, state, role)
    require(item.get('verdict') == 'PASS', '검수 미통과: ' + key)
    require(item.get('unresolved') == [], '미해결 필수 문제 존재')
    target = ep / file_for(stage)
    meta = load(ep / ('draft_' + stage + '.json'))
    require(meta['read_sha256'] == sha(ep / ('read_' + writer(stage) + '.json')), '작성 전 열람 기록 변경: prepare/write 재실행')
    require(meta['artifact_sha256'] == sha(target), '관문 밖 원고 변경: write 재실행')
    require(meta['preflight_sha256'] == sha(ep / ('prepare_' + stage + '.json')), '작성 전 근거 변경: prepare/write 재실행')
    prepared = load(ep / ('prepare_' + stage + '.json'))
    for ev in prepared['evidence']:
        require(ev['sha256'] == sha(inside(ROOT, ev['file'])), '작성 후 견본/준비 근거 변경: 재검토')
    require(item.get('artifact_sha256') == sha(target), '검수 이후 원고 변경: ' + stage)
    require(item.get('rules') == state['rules'], '검수 기준 버전 불일치')
    require(item.get('dependencies') == deps(ep, state, stage), '앞 단계 변경: 후속 단계 재검수 필요')
    checks = item.get('checks', {})
    expected = criteria(key if stage == 'final' else 'part' if stage.startswith('part_') else stage)
    require(set(expected).issubset(checks), '필수 검사 항목 누락: ' + ','.join(expected))
    for name in expected:
        check = checks[name]
        require(check.get('status') in ('PASS', 'NA'), name + ': 판정 누락/미통과')
        require(check.get('status') != 'NA' or name in ('image_sources',), name + ': 필수 기준은 NA로 면제할 수 없음')
        require(check.get('reason', '').strip(), name + ': 판정 이유 누락')
        evidence = check.get('evidence', [])
        require(evidence, name + ': 실제 구절 근거 없음')
        require(any(inside(ROOT, ev.get('file', '')) == target.resolve() for ev in evidence), name + ': 검수 대상 원고의 실제 구절 필요')
        for ev in evidence:
            path = inside(ROOT, ev.get('file', ''))
            require(path.is_file() and ev.get('quote', '').strip() and ev['quote'] in read(path), name + ': 근거 구절 불일치')
            require(ev.get('sha256') == sha(path), name + ': 근거 자료 변경')
    if stage in ('plan', 'package', 'opening'):
        selection = item.get('selection', {})
        expected_source = 'user' if state['mode'] == 'ASK' else 'worker'
        require(selection.get('source') == expected_source, '선택 주체 불일치. ASK는 실제 사용자 선택 필요')
        require(selection.get('reason', '').strip(), '선택 근거 누락')
        if state['mode'] == 'ASK':
            path = ep / ('decision_' + stage + '.md')
            require(path.is_file() and selection.get('quote', '').strip() and selection['quote'] in read(path), '실제 사용자 발언 기록 없음')
            require(selection.get('decision_sha256') == sha(path), '사용자 선택 기록 변경')
    if stage == 'final':
        combined = '\n\n'.join(read(ep / file_for(s)).strip() for s in stages(state) if s == 'opening' or s.startswith('part_') or s == 'closing') + '\n'
        require(read(target) == combined, '최종본이 통과한 도입·파트·클로징과 다름')
        count = len(re.sub(r'\s', '', read(target)))
        require(count >= 4000, '최소 10분 보수 추정(400자/분): 4000자 미만')
        if state.get('max_minutes'):
            require(count / 300 <= state['max_minutes'], '상한 보수 추정(300자/분) 초과')

def validate_stage(ep, state, stage):
    if stage in VALIDATED: return
    require(stage in stages(state), '없는 단계')
    require((ep / file_for(stage)).is_file(), '산출물 없음: ' + stage)
    reading(ep, state, writer(stage))
    for key in receipts(stage):
        path = ep / ('review_' + key + '.json')
        require(path.is_file(), '독립 검수 기록 없음: ' + key)
        validate_receipt(ep, state, stage, key, load(path))
    VALIDATED.add(stage)

def run(args):
    ep = episode(args.episode)
    if args.action == 'init':
        require(not ep.exists(), '기존 실행을 덮어쓰지 않음. 새 편/실행 이름 사용')
        roster = load(inside(ROOT, args.actors))
        require(set(ROLES).issubset(roster), '담당 역할 누락')
        require(all(isinstance(v, str) and v.strip() for v in roster.values()), '실제 에이전트 ID 누락')
        require(roster['fact_review'] != roster['flow_review'], '최종 사실·흐름 검수 담당은 서로 달라야 함')
        for role in ('research', 'plan', 'package', 'opening', 'body', 'coordinator'):
            require(roster[role] not in (roster['review'], roster['fact_review'], roster['flow_review']), '작성/총괄 담당과 독립 검수 담당 겹침')
        require(1 <= args.parts <= 15, '파트 수는 1~15')
        request = inside(ROOT, args.request)
        require(request.is_file() and read(request).strip(), '실제 요청 원문 없음')
        ep.mkdir(parents=True)
        (ep / 'request.md').write_text(read(request), encoding='utf-8')
        save(ep / 'state.json', {'version': 1, 'parts': args.parts, 'mode': args.mode,
            'max_minutes': args.max_minutes, 'actors': roster, 'rules': rule_snapshot(),
            'request_sha256': sha(ep / 'request.md')})
        save(ROOT / '실험' / 'active_episode.json', {'episode': args.episode})
        return {'initialized': str(ep), 'mode': args.mode, 'note': 'ID/사용자 발언의 진위는 총괄이 확인하는 기록이며 암호학적 인증이 아님'}
    state = state_for(ep)
    if args.action == 'decision':
        require(state['mode'] == 'ASK' and args.stage in ('plan', 'package', 'opening'), 'ASK의 선택 단계만 기록')
        actor(state, 'coordinator', args.actor)
        text = read(inside(ROOT, args.input))
        require(text.strip(), '실제 사용자 선택/위임 발언 없음')
        (ep / ('decision_' + args.stage + '.md')).write_text(text, encoding='utf-8')
        return {'decision': args.stage, 'sha256': sha(ep / ('decision_' + args.stage + '.md')), 'note': '총괄은 실제 사용자 발언과 대조'}
    if args.action == 'read-record':
        actor(state, args.role, args.actor)
        payload = load(inside(ROOT, args.input))
        record = {'actor': args.actor, 'files': {}}
        for ev in payload:
            path = inside(ROOT, ev['file'])
            require(path.is_file() and ev['quote'].strip() and ev['quote'] in read(path), '열람 근거 구절 불일치')
            require(ev.get('application', '').strip(), '적용 설명 없음')
            record['files'][ev['file']] = {'sha256': sha(path), 'quote': ev['quote'], 'application': ev['application']}
        save(ep / ('read_' + args.role + '.json'), record)
        reading(ep, state, args.role)
        return {'recorded': args.role}
    if args.action in ('check', 'prepare', 'write', 'review', 'assemble'):
        require(args.stage in stages(state), '없는 단계')
        dependencies = deps(ep, state, args.stage)
        reading(ep, state, writer(args.stage))
        if args.action == 'check': return {'ready': args.stage, 'dependencies': dependencies}
        if args.action == 'prepare':
            actor(state, writer(args.stage), args.actor)
            payload = load(inside(ROOT, args.input))
            require(payload.get('purpose', '').strip(), '이번 단계 목적 누락')
            evidence = payload.get('evidence', [])
            require(evidence, '작성 전 참고 구절 근거 없음')
            for ev in evidence:
                path = inside(ROOT, ev['file'])
                require(path.is_file() and ev['quote'].strip() and ev['quote'] in read(path), '작성 전 근거 불일치')
                ev['sha256'] = sha(path)
            if args.stage in ('plan', 'package', 'opening') or args.stage.startswith('part_') or args.stage == 'closing':
                require(payload.get('benchmark_choice', '').strip() and payload.get('weakness_to_avoid', '').strip(), '사전 견본 선정·약점 비복제 계획 필요')
                paths = [ev['file'].replace('\\', '/') for ev in evidence]
                require(any('우주와나/분석지/' in p and not p.split('/')[-1].startswith('_') for p in paths), '이번에 선택한 벤치마크 원문/분석지 근거 필요')
                require(any('우주와나/_합격원고/' in p and p.endswith('01_대본.txt') for p in paths), '사용자 합격원고 실제 문장 근거 필요')
            payload.update(dependencies=dependencies, read_sha256=sha(ep / ('read_' + writer(args.stage) + '.json')))
            save(ep / ('prepare_' + args.stage + '.json'), payload)
            return {'prepared': args.stage, 'note': '선정 근거 저장. 전문 정독과 내용 이해는 별도 검수'}
        if args.action in ('write', 'assemble'):
            actor(state, writer(args.stage), args.actor)
            require(args.stage != 'final' or args.action == 'assemble', '최종본은 assemble로 조립')
            preflight = ep / ('prepare_' + args.stage + '.json')
            require(preflight.is_file(), '작성 전 prepare 관문 미완료')
            prepared = load(preflight)
            require(prepared['dependencies'] == dependencies and prepared['read_sha256'] == sha(ep / ('read_' + writer(args.stage) + '.json')), '작성 전 근거 또는 앞 단계 변경. prepare 재실행')
            for ev in prepared['evidence']:
                require(ev['sha256'] == sha(inside(ROOT, ev['file'])), '작성 전 견본 변경. prepare 재실행')
            if args.action == 'assemble':
                require(args.stage == 'final', '조립은 final 단계만')
                text = '\n\n'.join(read(ep / file_for(s)).strip() for s in stages(state) if s == 'opening' or s.startswith('part_') or s == 'closing') + '\n'
            else:
                text = read(inside(ROOT, args.input))
            require(text.strip(), '빈 산출물')
            (ep / file_for(args.stage)).write_text(text, encoding='utf-8')
            save(ep / ('draft_' + args.stage + '.json'), {'artifact_sha256': sha(ep / file_for(args.stage)),
                'read_sha256': prepared['read_sha256'], 'preflight_sha256': sha(preflight)})
            return {'written': file_for(args.stage), 'sha256': sha(ep / file_for(args.stage)), 'status': '독립 검수 대기'}
        key = args.kind if args.stage == 'final' else args.stage
        require(key in receipts(args.stage), '검수 종류 불일치')
        role = 'fact_review' if key == 'final_fact' else 'flow_review' if key == 'final_flow' else 'review'
        actor(state, role, args.actor)
        payload = load(inside(ROOT, args.input))
        require(payload.get('artifact_sha256') == sha(ep / file_for(args.stage)), '검수자가 읽은 파일 해시를 명시해야 함')
        payload.update(actor=args.actor, rules=state['rules'], dependencies=dependencies)
        for check in payload.get('checks', {}).values():
            for ev in check.get('evidence', []):
                path = inside(ROOT, ev['file'])
                require(ev.get('sha256') == sha(path), '검수자가 읽은 근거 자료 해시를 명시해야 함')
        if state['mode'] == 'ASK' and args.stage in ('plan', 'package', 'opening'):
            require(payload.get('selection', {}).get('decision_sha256') == sha(ep / ('decision_' + args.stage + '.md')), '선택 기록 해시 필요')
        # FAIL 보고도 보관하지만 다음 단계는 PASS만 허용한다.
        if payload.get('verdict') == 'PASS': validate_receipt(ep, state, args.stage, key, payload)
        else: require(payload.get('verdict') == 'FAIL' and payload.get('unresolved'), '미통과 사유 필요')
        save(ep / ('review_' + key + '.json'), payload)
        return {'review': key, 'verdict': payload['verdict']}
    if args.action == 'status':
        result = []
        for stage in stages(state):
            try:
                validate_stage(ep, state, stage)
                result.append({'stage': stage, 'status': 'PASS'})
            except (GateError, OSError, KeyError, TypeError) as exc:
                result.append({'stage': stage, 'status': 'BLOCKED', 'reason': str(exc)})
                break
        return {'stages': result, 'complete': len(result) == len(stages(state)) and result[-1]['status'] == 'PASS'}
    raise GateError('지원하지 않는 명령')

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['init', 'decision', 'read-record', 'check', 'prepare', 'write', 'review', 'assemble', 'status'])
    parser.add_argument('--episode', required=True)
    parser.add_argument('--stage')
    parser.add_argument('--role')
    parser.add_argument('--actor')
    parser.add_argument('--input')
    parser.add_argument('--kind', choices=['final_fact', 'final_flow'])
    parser.add_argument('--mode', choices=['ASK', 'AUTO'], default='ASK')
    parser.add_argument('--parts', type=int, default=4)
    parser.add_argument('--max-minutes', type=float)
    parser.add_argument('--actors')
    parser.add_argument('--request')
    args = parser.parse_args()
    try:
        print(json.dumps(run(args), ensure_ascii=False, indent=2))
    except (GateError, OSError, KeyError, TypeError, json.JSONDecodeError) as exc:
        print(json.dumps({'blocked': True, 'reason': str(exc)}, ensure_ascii=False))
        return 2
    return 0

if __name__ == '__main__':
    if hasattr(sys.stdout, 'reconfigure'): sys.stdout.reconfigure(encoding='utf-8')
    sys.exit(main())
