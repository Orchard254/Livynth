#!/usr/bin/env python3
"""Local sanity check for LIVYNTH agent pack. Does not launch OpenCode."""
from pathlib import Path
import json,re
root=Path(__file__).resolve().parents[1]
conf=json.loads((root/'opencode.jsonc').read_text())
assert conf['default_agent']=='livynth-director'
agents=sorted((root/'.opencode'/'agents').glob('*.md'))
assert len(agents)==30, f'Expected 30, got {len(agents)}'
assert len({p.stem for p in agents})==30
primary=[]
for p in agents:
    s=p.read_text(encoding='utf-8')
    assert s.startswith('---\n') and s.count('\n---\n')>=1, p
    fm=s.split('---',2)[1]
    assert 'description:' in fm and 'permissions:' in fm, p
    modes=re.findall(r'^mode: (primary|subagent)$',fm,re.M)
    assert len(modes)==1,p
    if modes[0]=='primary': primary.append(p.stem)
    assert 'Acceptance gate' in s and 'Mission' in s,p
assert primary==['livynth-director'], primary
assert (root/'AGENTS.md').is_file() and (root/'docs'/'C001_GEO03_DISPATCH.md').is_file()
print('PASS: 30 unique agent definitions, 1 primary, 29 subagents, common rules and dispatch docs')
