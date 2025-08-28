import re
from pathlib import Path
from typing import Dict, List

MAP_LINE = re.compile(r'^\s*(?P<lhs>.+?)\s*->\s*\{(?P<rhs>.*?)\}\s*$')
WRAP_STR = re.compile(r'^\s*[A-Za-z_]\w*\s*\(\s*([\'"])(.*?)\1\s*\)\s*$')
WRAP_ANY = re.compile(r'^\s*[A-Za-z_]\w*\s*\(\s*([^\(\),]+?)\s*\)\s*$')


def normalize_lhs(lhs: str) -> str:
    s = lhs.strip()
    m = WRAP_STR.match(s)
    if m:
        return m.group(2).strip()

    m = WRAP_ANY.match(s)
    if m:
        inner = m.group(1).strip()
        if (inner.startswith('"') and inner.endswith('"')) or (inner.startswith("'") and inner.endswith("'")):
            inner = inner[1:-1]
        return inner.strip()

    if (s.startswith('"') and s.endswith('"')) or (s.startswith("'") and s.endswith("'")):
        s = s[1:-1]
    return s.strip()



def extract_all_vars_map(text: str) -> Dict[str, List[str]]:
    result: Dict[str, List[str]] = {}
    for raw in text.splitlines():
        line = raw.strip()
        if not line or '->' not in line or '{' not in line or '}' not in line:
            continue
        m = MAP_LINE.match(line)
        if not m:
            continue

        lhs_raw = m.group('lhs').strip()
        rhs_content = m.group('rhs').split('#', 1)[0]

        all_vars = [t.strip() for t in rhs_content.split(',') if t.strip()]

        if not all_vars:
            continue

        key = normalize_lhs(lhs_raw)
        result[key] = all_vars

    return result


def extract_all_vars_map_from_file(path: str) -> Dict[str, List[str]]:
    text = Path(path).read_text(encoding="utf-8", errors="ignore")
    return extract_all_vars_map(text)

