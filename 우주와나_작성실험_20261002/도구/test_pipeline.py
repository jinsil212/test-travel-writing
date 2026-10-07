import importlib.util
import json
import sys
import tempfile
import unittest
import uuid
import shutil
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).parent))
import pipeline as p
import hook as h


class PipelineTests(unittest.TestCase):
    def setUp(self):
        self.old = p.ROOT, p.BASE, p.GUIDES, h.ROOT
        self.root = Path(__file__).parent / ('fixture-' + uuid.uuid4().hex)
        self.root.mkdir()
        p.ROOT = h.ROOT = self.root
        p.BASE = self.root / '실험' / '에피소드'
        p.GUIDES = self.root / '지침' / '에이전트'
        guides = ['_대본지침서.md', '우주와나/채널설정.md', '우주와나/수정·선택 사례.md',
                  '우주와나/분석지/_원고쓰는법.md', '우주와나/분석지/_검수기준서.md',
                  '지침/운영.md', '지침/에이전트/06_독립검수.md', p.COMMON_DETAIL, p.DETAIL_ROUTING] + list(set(p.DETAILS.values())) + ['지침/에이전트/' + n for n in set(p.ROLES.values())]
        self.bench = '우주와나/분석지/001_견본/원문.txt'
        self.sample = '우주와나/_합격원고/견본/01_대본.txt'
        for name in guides + [self.bench, self.sample]:
            self.put(name, '견본 구절. ' + '참고 내용 ' * 100)
        self.put(p.DETAIL_INDEX, {'source_sha256': {f: p.sha(self.root / f) for f in p.SOURCE_FILES},
            'routing_sha256': p.sha(self.root / p.DETAIL_ROUTING),
            'packets': {f: p.sha(self.root / f) for f in set(p.DETAILS.values()) | {p.COMMON_DETAIL}}})
        self.actors = {role: 'agent-' + role for role in p.ROLES}
        self.put('actors.json', self.actors)
        self.put('request.md', '사용자 요청: 한 편 시험')
        self.call('init', actors='actors.json', request='request.md', mode='AUTO', parts=1, max_minutes=None)
        self.ep = p.episode('test')
        for role in p.ROLES:
            files = p.required_readings(role)
            if role == 'review':
                files += list(set(p.DETAILS.values())) + ['지침/에이전트/' + n for n in set(p.ROLES.values())]
            self.put('reading.json', [{'file': f, 'quote': '견본 구절.', 'application': '이번 단계 적용'} for f in files])
            self.call('read-record', role=role, actor=self.actors[role], input='reading.json')

    def tearDown(self):
        p.ROOT, p.BASE, p.GUIDES, h.ROOT = self.old
        p.VALIDATED.clear()
        assert self.root.resolve().parent == Path(__file__).resolve().parent
        shutil.rmtree(self.root)

    def put(self, name, value):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value, ensure_ascii=False) if not isinstance(value, str) else value, encoding='utf-8')
        return path

    def call(self, action, **kw):
        return p.run(SimpleNamespace(action=action, episode='test', **kw))

    def prepare(self, stage):
        self.put('pre.json', {'purpose': '단계 목적', 'benchmark_choice': '선정', 'weakness_to_avoid': '반복 회피',
            'evidence': [{'file': self.bench, 'quote': '견본 구절.'}, {'file': self.sample, 'quote': '견본 구절.'}]})
        self.call('prepare', stage=stage, actor=self.actors[p.writer(stage)], input='pre.json')

    def write(self, stage):
        self.prepare(stage)
        self.put('draft.txt', '실제 원고 구절. ' + ('설명내용' * 1000 if stage == 'part_01' else '내용' * 30))
        self.call('assemble' if stage == 'final' else 'write', stage=stage,
                  actor=self.actors[p.writer(stage)], input='draft.txt')

    def payload(self, stage, key=None):
        key = key or stage
        target = self.ep / p.file_for(stage)
        relative = str(target.relative_to(self.root))
        result = {'verdict': 'PASS', 'unresolved': [], 'artifact_sha256': p.sha(target),
            'selection': {'source': 'worker', 'reason': '비교 선정'},
            'checks': {k: {'status': 'PASS', 'reason': '원고 대조', 'evidence':
                [{'file': relative, 'quote': '실제 원고 구절.', 'sha256': p.sha(target)}]}
                for k in p.criteria(key if stage == 'final' else 'part' if stage.startswith('part_') else stage)}}
        fact_path = self.ep / 'review_final_fact.json'
        if key == 'final_flow' and fact_path.exists():
            result['fact_review_reference'] = {'actor': self.actors['fact_review'],
                'artifact_sha256': p.sha(target), 'receipt_sha256': p.sha(fact_path),
                'checks': ['claims_sources', 'numbers_conditions', 'future_hypothesis']}
        return result

    def review(self, stage, key=None, payload=None, actor=None):
        key = key or stage
        role = 'fact_review' if key == 'final_fact' else 'flow_review' if key == 'final_flow' else 'review'
        self.put('review.json', payload or self.payload(stage, key))
        return self.call('review', stage=stage, kind=key, actor=actor or self.actors[role], input='review.json')

    def complete_through(self, stop='final'):
        for stage in p.stages(p.load(self.ep / 'state.json')):
            self.write(stage)
            for key in p.receipts(stage):
                self.review(stage, key)
            if stage == stop:
                break

    def test_lazy_roster_and_independent_review(self):
        p.validate_roster({'coordinator': 'root'})
        with self.assertRaises(p.GateError):
            p.validate_roster({'coordinator': 'root', 'plan': 'same', 'review': 'same'})
        with self.assertRaises(p.GateError):
            p.validate_roster({'coordinator': 'root', 'fact_review': 'same', 'flow_review': 'same'})

    def test_roster_addition_and_reassignment_guard(self):
        state=p.load(self.ep / 'state.json')
        state['actors']={'coordinator': self.actors['coordinator']}
        p.save(self.ep / 'state.json', state)
        self.put('addition.json', {'plan': 'new-plan'})
        self.call('roster', actor=self.actors['coordinator'], actors='addition.json')
        self.assertEqual(p.load(self.ep / 'state.json')['actors']['plan'], 'new-plan')
        self.put('addition.json', {'plan': 'replacement'})
        with self.assertRaises(p.GateError):
            self.call('roster', actor=self.actors['coordinator'], actors='addition.json')

    def test_role_detail_reading_is_required(self):
        record = p.load(self.ep / 'read_research.json')
        record['files'].pop(p.DETAILS['research'])
        p.save(self.ep / 'read_research.json', record)
        with self.assertRaisesRegex(p.GateError, '열람 기록 누락'):
            self.call('check', stage='research')

    def test_mutated_role_packet_blocks_reuse(self):
        self.put(p.DETAILS['research'], '변경된 역할별 원문')
        with self.assertRaisesRegex(p.GateError, '지침 변경'):
            self.call('check', stage='research')

    def test_new_execution_rejects_stale_source_packets(self):
        self.put('우주와나/채널설정.md', '새 사용자 지침')
        with self.assertRaisesRegex(p.GateError, '원문 묶음 갱신'):
            p.run(SimpleNamespace(action='init', episode='newtest', actors='actors.json',
                request='request.md', mode='AUTO', parts=1, max_minutes=None))
        self.assertFalse(p.episode('newtest').exists())

    def test_changed_roster_cannot_merge_independent_reviewers(self):
        state = p.load(self.ep / 'state.json')
        state['actors']['flow_review'] = state['actors']['fact_review']
        p.save(self.ep / 'state.json', state)
        with self.assertRaisesRegex(p.GateError, '서로 달라야'):
            self.call('status')

    def test_final_requires_every_numbered_criterion(self):
        self.complete_through('closing')
        self.write('final')
        payload = self.payload('final', 'final_flow')
        payload['checks'].pop('criterion_25')
        with self.assertRaisesRegex(p.GateError, 'criterion_25'):
            self.review('final', key='final_flow', payload=payload)

    def test_stage_review_requires_writers_detail_reading(self):
        self.write('research')
        record = p.load(self.ep / 'read_review.json')
        record['files'].pop(p.DETAILS['research'])
        p.save(self.ep / 'read_review.json', record)
        with self.assertRaisesRegex(p.GateError, '열람 기록 누락'):
            self.review('research')

    def test_flow_cannot_self_certify_factual_criteria(self):
        self.complete_through('closing')
        self.write('final')
        self.review('final', key='final_fact')
        payload = self.payload('final', 'final_flow')
        payload.pop('fact_review_reference')
        with self.assertRaisesRegex(p.GateError, '독립 사실 판정 참조'):
            self.review('final', key='final_flow', payload=payload)

    def test_auto_complete(self):
        self.complete_through()
        self.assertTrue(self.call('status')['complete'])

    def test_missing_dependency(self):
        with self.assertRaises((p.GateError, OSError)):
            self.call('check', stage='plan')

    def test_fail_blocks_next(self):
        self.write('research')
        payload = self.payload('research')
        payload.update(verdict='FAIL', unresolved=['근거 부족'])
        self.review('research', payload=payload)
        with self.assertRaises(p.GateError):
            self.call('check', stage='plan')

    def test_self_review(self):
        self.write('research')
        state = p.load(self.ep / 'state.json')
        state['actors']['review'] = self.actors['research']
        p.save(self.ep / 'state.json', state)
        with self.assertRaisesRegex(p.GateError, '자기 검수'):
            self.review('research', actor=self.actors['research'])

    def test_draft_mutation(self):
        self.complete_through('research')
        with (self.ep / 'research.md').open('a', encoding='utf-8') as f:
            f.write('변경')
        with self.assertRaises(p.GateError):
            self.call('check', stage='plan')

    def test_upstream_review_mutation(self):
        self.complete_through('plan')
        path = self.ep / 'review_research.json'
        data = p.load(path)
        data['comment'] = '검수 기록 변경'
        p.save(path, data)
        with self.assertRaisesRegex(p.GateError, '앞 단계 변경'):
            self.call('check', stage='package')

    def test_path_traversal(self):
        with self.assertRaises(p.GateError):
            p.inside(self.root, '../escape.txt')
        with self.assertRaises(p.GateError):
            p.episode('../test')

    def test_prepare_required(self):
        self.put('draft.txt', '원고')
        with self.assertRaisesRegex(p.GateError, 'prepare'):
            self.call('write', stage='research', actor=self.actors['research'], input='draft.txt')

    def test_invalid_evidence(self):
        self.write('research')
        payload = self.payload('research')
        payload['checks']['sources']['evidence'][0]['quote'] = '없는 구절'
        with self.assertRaisesRegex(p.GateError, '구절 불일치'):
            self.review('research', payload=payload)

    def test_ask_choice_guard(self):
        self.complete_through('research')
        state = p.load(self.ep / 'state.json')
        state['mode'] = 'ASK'
        p.save(self.ep / 'state.json', state)
        self.write('plan')
        payload = self.payload('plan')
        payload['selection'] = {'source': 'user', 'reason': '선택', 'quote': '없는 선택'}
        self.put('choice.md', '기획 1안을 선택합니다')
        self.call('decision', stage='plan', actor=self.actors['coordinator'], input='choice.md')
        payload['selection']['decision_sha256'] = p.sha(self.ep / 'decision_plan.md')
        with self.assertRaisesRegex(p.GateError, '발언 기록'):
            self.review('plan', payload=payload)

    def test_hook_raw_shell_and_patch_blocked(self):
        for inp in [{'cmd': 'Set-Content file.txt hacked'},
                    {'patch': '*** Update File: 실험/에피소드/test/part_01.txt\n+변경'},
                    {'file_path': str(self.ep / 'research.md')}]:
            out = h.handle({'hook_event_name': 'PreToolUse', 'cwd': str(self.root), 'tool_input': inp})
            self.assertEqual(out['hookSpecificOutput']['permissionDecision'], 'deny')

    def test_rule_mutation(self):
        self.put('_대본지침서.md', '변경한 지침')
        with self.assertRaisesRegex(p.GateError, '지침 변경'):
            self.call('status')

    def test_required_checks_cannot_all_be_na(self):
        self.write('research')
        payload = self.payload('research')
        for check in payload['checks'].values():
            check['status'] = 'NA'
        with self.assertRaises(p.GateError):
            self.review('research', payload=payload)

    def test_review_requires_target_evidence(self):
        self.write('research')
        payload = self.payload('research')
        for check in payload['checks'].values():
            check['evidence'] = [{'file': self.bench, 'quote': '견본 구절.', 'sha256': p.sha(self.root / self.bench)}]
        with self.assertRaises(p.GateError):
            self.review('research', payload=payload)

    def test_hook_absolute_windows_path_from_outside_scope(self):
        out = h.handle({'hook_event_name': 'PreToolUse', 'cwd': str(self.root.parent),
                        'tool_input': {'file_path': str(self.ep / 'research.md')}})
        self.assertEqual(out['hookSpecificOutput']['permissionDecision'], 'deny')

    def test_hook_read_subcommand_blocked(self):
        for cmd in ['Get-Content (New-Item hacked.txt -ItemType File)',
                    'rg --pre powershell target.txt']:
            out = h.handle({'hook_event_name': 'PreToolUse', 'cwd': str(self.root), 'tool_input': {'cmd': cmd}})
            self.assertEqual(out['hookSpecificOutput']['permissionDecision'], 'deny')

    def test_ask_phase_choices_independent_and_reselection_invalidates(self):
        state = p.load(self.ep / 'state.json')
        state['mode'] = 'ASK'
        p.save(self.ep / 'state.json', state)
        for stage in ['research', 'plan', 'package', 'opening']:
            self.write(stage)
            payload = self.payload(stage)
            if stage in ('plan', 'opening'):
                quote = stage + ' 1안을 선택합니다'
                self.put('choice.md', quote)
                self.call('decision', stage=stage, actor=self.actors['coordinator'], input='choice.md')
                payload['selection'] = {'source': 'user', 'reason': '사용자 선택', 'quote': quote,
                                        'decision_sha256': p.sha(self.ep / ('decision_' + stage + '.md'))}
            self.review(stage, payload=payload)
        self.assertEqual(self.call('check', stage='part_01')['ready'], 'part_01')
        self.put('choice.md', 'opening 2안으로 변경합니다')
        self.call('decision', stage='opening', actor=self.actors['coordinator'], input='choice.md')
        fresh = p.state_for(self.ep)
        p.validate_stage(self.ep, fresh, 'plan')
        p.validate_stage(self.ep, fresh, 'package')
        with self.assertRaises(p.GateError):
            self.call('check', stage='part_01')

    def test_prepare_reference_mutation_after_write(self):
        self.complete_through('research')
        self.put(self.bench, '견본 구절. 변경한 견본')
        with self.assertRaises(p.GateError):
            self.call('check', stage='plan')


if __name__ == '__main__':
    unittest.main()

