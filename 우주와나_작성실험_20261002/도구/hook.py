"""Codex/Claude command hook 어댑터. 프로젝트 신뢰/훅 신뢰 후 실행."""
import json
import re
import sys
from pathlib import Path
import pipeline

ROOT = pipeline.ROOT

def scoped(data):
    cwd = Path(data.get('cwd') or '.').resolve()
    try: return cwd.is_relative_to(ROOT.resolve())
    except ValueError: return False

def block(reason):
    return {'hookSpecificOutput': {'hookEventName': 'PreToolUse', 'permissionDecision': 'deny',
        'permissionDecisionReason': reason}, 'systemMessage': '[우주와나 단계 관문] ' + reason}

def protected(text):
    normalized = re.sub('/+', '/', text.replace('\\', '/')).lower()
    return '실험/에피소드/' in normalized or '우주와나/원고/' in normalized or 'active_episode.json' in normalized

def handle(data):
    event = data.get('hook_event_name', '')
    inp = data.get('tool_input') or {}
    text = json.dumps(inp, ensure_ascii=False)
    normalized = re.sub('/+', '/', text.replace('\\', '/')).lower()
    applies = scoped(data) or str(ROOT).replace('\\', '/').lower() in normalized
    if not applies: return {}
    if event in ('SessionStart', 'SubagentStart'):
        return {'hookSpecificOutput': {'hookEventName': event, 'additionalContext':
            '우주와나 실험 전용: AGENTS.md와 지침/운영.md 및 맡은 역할 원문을 읽는다. '
            '새 원고는 실험/에피소드에서 pipeline.py prepare/write/review로만 저장. '
            '앞 단계 PASS 없이 다음 단계 집필 금지. 테스트 밖 수정 금지. '
            'ASK 사용자 선택과 AUTO 작업자 선정을 구분. 훅은 내용 품질을 판정하지 않는다.'}}
    if event == 'PreToolUse':
        command = inp.get('cmd') or inp.get('command')
        if isinstance(command, str):
            # 허용하는 실행은 관문 CLI 또는 부작용 없는 단순 조회. 임의 코드는 평가하지 않는다.
            if re.search(r'[;\r\n`$<>(){}]|\|\||&&|--pre(?:\s|=)|-Command\b|-EncodedCommand\b', command, re.I):
                return block('복합 셸/코드 실행은 검사할 수 없어 차단. 조회는 단일 명령, 저장은 pipeline.py 사용')
            pattern = r"^\s*&?\s*['\"]([^'\"]+python(?:\.exe)?)['\"]\s+['\"]([^'\"]+pipeline\.py)['\"]\s+(init|decision|read-record|check|prepare|write|review|assemble|status)\b(.*)$"
            match = re.match(pattern, command, re.I)
            if match:
                python_path, script, action, arguments = match.groups()
                expected_python = (ROOT / '도구' / 'runtime.json')
                if expected_python.is_file() and Path(python_path).resolve() == Path(pipeline.load(expected_python)['python']).resolve() and Path(script).resolve() == (ROOT / '도구' / 'pipeline.py').resolve():
                    # 인수는 argparse가 검증. 인터프리터 옵션이나 셸 재진입은 허용하지 않는다.
                    if not re.search(r'\s-(?:c|m|Command|EncodedCommand)\b', arguments, re.I): return {}
            pieces = command.split('|')
            if all(re.match(r'^\s*(Get-Content|Get-ChildItem|Get-Item|Get-FileHash|Test-Path|Select-Object|Measure-Object|rg)\b', p, re.I) for p in pieces):
                return {}
            return block('이 실험 폴더의 임의 셸 쓰기는 차단. 입력은 실험/입력에 파일 도구로 만들고 관문 CLI로 저장')
        patch = inp.get('patch') or inp.get('input') or ''
        file_path = inp.get('file_path') or inp.get('path') or ''
        if protected(str(patch) + ' ' + str(file_path)):
            return block('단계 산출물 직접 수정 금지. 실험/입력에 수정본을 만들고 pipeline.py write 및 독립 review 재실행')
        return {}
    if event == 'Stop':
        pointer = ROOT / '실험' / 'active_episode.json'
        if not pointer.is_file(): return {}
        try:
            ep = pipeline.episode(pipeline.load(pointer)['episode'])
            state = pipeline.state_for(ep)
            if state['mode'] == 'ASK':
                return {'systemMessage': 'ASK: 선택 대기는 정상. 현재 단계와 미완료 항목을 정확히 보고하고 완성으로 표시하지 않는다.'}
            status = pipeline.run(type('Args', (), {'action': 'status', 'episode': ep.name})())
            if status['complete']: return {}
            reason = 'AUTO 최종 관문 미통과: ' + json.dumps(status, ensure_ascii=False)
        except Exception as exc:
            reason = '우주와나 실행 상태 검증 실패: ' + str(exc)
        if data.get('stop_hook_active'): return {'systemMessage': reason + ' 미완료로 보고. 무한 종료 차단 방지.'}
        return {'decision': 'block', 'reason': reason}
    return {}

if __name__ == '__main__':
    if hasattr(sys.stdout, 'reconfigure'): sys.stdout.reconfigure(encoding='utf-8')
    try:
        data = json.load(sys.stdin)
        result = handle(data)
    except Exception as exc:
        print('훅 입력/검사 오류: ' + str(exc), file=sys.stderr)
        sys.exit(2)
    print(json.dumps(result, ensure_ascii=False))
