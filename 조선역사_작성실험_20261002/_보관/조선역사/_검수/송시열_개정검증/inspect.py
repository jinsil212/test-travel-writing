"""Reproducible text counts, not semantic judgements."""
from pathlib import Path
import importlib.util
import json
import re
import sys

root = Path(__file__).resolve().parent
repo = root.parents[1]
spec = importlib.util.spec_from_file_location('bench', repo / '_도구' / 'bench-metrics.py')
bench = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bench)
text = (root / sys.argv[1]).read_text(encoding='utf-8')
sents = bench.split_sentences(text)
title = '왕도 아닌데 조정을 움직인 송시열, 그의 말은 왜 힘이 있었나'
sections = ['왕도 아닌데,', '효종에게 송시열은 낯선', '두 사람이 만난 1658년', '효종 다음에는 아들', '숙종은 후궁에게서', '그런데 송시열이 죽은 뒤에도,']
starts = [text.index(s) for s in sections] + [len(text)]
sections_data = []
for i, label in enumerate(sections):
    ss = bench.split_sentences(text[starts[i]:starts[i+1]])
    sections_data.append({'start': label, 'sentence_chars': sum(map(len, ss)), 'sentences': len(ss)})
number_runs = []
run = []
for s in sents + ['']:
    if len(re.findall(r'\d+', s)) >= 3:
        run.append(s)
    elif run:
        number_runs.append(run)
        run = []
names = ['송시열', '효종', '현종', '숙종', '민정중', '장희빈', '봉림대군', '송준길', '유계', '윤빈', '윤증']
report = {
    'draft': sys.argv[1], 'raw_chars': len(text), 'sentence_chars': sum(map(len, sents)),
    'estimated_minutes_at_409': round(sum(map(len, sents)) / 409, 2),
    'title': title, 'title_chars': len(title), 'sections': sections_data,
    'names': {n: {'count': text.count(n), 'first': text.find(n)} for n in names},
    'questions': [s for s in sents if '?' in s],
    'dates': [s for s in sents if re.search(r'\d{4}년|\d+년 뒤|가을|나중|그 뒤|이후', s)],
    'three_number_runs': number_runs,
    'direct_quotes': re.findall('“([^”]+)”', text),
    'tts_middle_dots': text.count('·'),
    'markup_lines': [s for s in text.splitlines() if re.match(r'^\s*(?:#|\|)', s)],
    'violent_detail_candidates': [s for s in sents if re.search(r'사약|죽|처벌|고문|시신|피를|칼로', s)],
    'lexical_watch_only': {n: text.count(n) for n in ['힘', '신임', '지지', '말', '떠나', '다시', '기막', '소름']},
}
target = root / sys.argv[2]
with target.open('x', encoding='utf-8') as f:
    json.dump(report, f, ensure_ascii=False, indent=2)
print(json.dumps(report, ensure_ascii=False, indent=2))
