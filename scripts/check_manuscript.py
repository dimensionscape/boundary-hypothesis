"""Check the manuscript against its executable appendix and numbered results."""
from pathlib import Path
import hashlib
import json
import re

import verify

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'manuscript/paper.md'


def summary_table(record):
    rows = [
        ('Finite operator representations', str(record['operator_cases'])),
        ('Count probability and forward-equation cases', str(record['count_cases'])),
        ('Maximum forward-equation residual', f"{record['max_forward_error']:.3e}"),
        ('Exact harmonic identities', str(record['exact_harmonic_cases'])),
        ('Exact independent packing integrals', str(record['packing_integral_cases'])),
        ('Transition-composition cases', str(record['composition_cases'])),
        ('Coupled birth thresholds', f"{record['matched_future_thresholds']:,}"),
        ('Biased mean opportunity count', f"{record['mean_opportunities']:.9f}"),
        ('Program assertions', 'All passed'),
    ]
    return '\n'.join(['| Check | Cases or result |', '|---|---|'] +
                     [f'| {name} | {value} |' for name, value in rows])


def check():
    raw = SOURCE.read_text(encoding='utf-8')
    record = verify.run()
    program = (ROOT / 'scripts/verify.py').read_text(encoding='utf-8').rstrip()
    listing = re.search(r'<!-- CODE:BEGIN -->\n```python\n(.*?)\n```', raw, re.S)
    assert listing and listing[1] == program, 'Executable appendix differs from verify.py'
    summary = re.search(r'<!-- SUMMARY:BEGIN -->\n(.*?)\n<!-- SUMMARY:END -->', raw, re.S)
    assert summary and summary[1] == summary_table(record), 'Verification table is stale'
    assert [int(x) for x in re.findall(r'\\tag\{(\d+)\}', raw)] == list(range(1, 19))
    assert [int(x) for x in re.findall(r'\*\*Proposition (\d+)\.', raw)] == list(range(1, 12))
    assert len(re.findall(r'^\*\*Proof\.\*\*', raw, re.M)) == 11
    assert re.findall(r'^## Appendix ([A-D])\.', raw, re.M) == list('ABCD')
    body, references = raw.split('## References\n', 1)
    assert [int(x) for x in re.findall(r'^\[(\d+)\]', references, re.M)] == list(range(1, 14))
    prose = re.sub(r'```.*?```', '', body, flags=re.S)
    cited = {int(item) for group in re.findall(r'\[([1-9]\d*(?:,[1-9]\d*)*)\]', prose)
             for item in group.split(',')}
    assert cited == set(range(1, 14))
    assert not re.search(r'[\u2010-\u2015]|\ufffd', raw)
    assert not re.search(r'[A-Z]:[/\\]|file://|\b(?:TODO|FIXME)\b', raw)
    assert '**Christopher Speciale**' in raw
    assert 'Research manuscript - January 18, 2026' in raw
    namespace = {'__name__': 'appendix_listing'}
    exec(compile(listing[1], 'Appendix D', 'exec'), namespace)
    assert namespace['run']() == record
    results = ROOT / 'results'
    results.mkdir(exist_ok=True)
    (results / 'verification.json').write_text(json.dumps(record, indent=2) + '\n', encoding='utf-8')
    audit = {
        'source': 'manuscript/paper.md',
        'source_sha256': hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
        'verification_program': 'scripts/verify.py',
        'verification_program_sha256': hashlib.sha256((ROOT / 'scripts/verify.py').read_bytes()).hexdigest(),
        'equations': 18, 'proved_propositions': 11, 'appendices': 4, 'references': 13,
        'executable_appendix_matches': True, 'verification_table_matches': True,
        'checks_passed': True,
    }
    (results / 'manuscript-check.json').write_text(json.dumps(audit, indent=2) + '\n', encoding='utf-8')
    return raw, record, audit


if __name__ == '__main__':
    _, _, audit = check()
    print(json.dumps(audit, indent=2))
