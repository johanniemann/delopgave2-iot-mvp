"""Validate portable Markdown references and common secret filenames.

No URL fetching, content secret scanning or application correctness checking.
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path
from urllib.parse import unquote, urlsplit

LINK = re.compile(r"!?\[[^\]]*\]\(([^)]+)\)")
HOST_PATH = re.compile(r"(?:/Users/|/home/|[A-Za-z]:\\Users\\)")
SECRET_SUFFIXES = {'.pem', '.key', '.p12', '.pfx'}


def prose(text: str) -> str:
    """Ignore fenced examples when locating real references and headings."""
    return re.sub(r'(?ms)^(`{3,}|~{3,})[^\n]*\n.*?^\1\s*$', '', text)


def anchors(text: str) -> set[str]:
    """Support ordinary GitHub-style ATX headings, including duplicates."""
    result: set[str] = set()
    counts: dict[str, int] = {}
    for line in text.splitlines():
        match = re.match(r'^#{1,6}\s+(.+?)\s*#*\s*$', line)
        if match:
            slug = re.sub(r'[^\w\- ]', '', match.group(1).lower()).replace(' ', '-')
            count = counts.get(slug, 0)
            counts[slug] = count + 1
            result.add(f'{slug}-{count}' if count else slug)
    return result


def check_paths(root: Path, paths: list[str]) -> list[str]:
    root = root.resolve()
    errors: list[str] = []
    for name in sorted(set(paths)):
        path = root / name
        if path.is_symlink():
            errors.append(f'{name}: symlinks are not supported by this portable setup')
            continue
        if not path.is_file():
            errors.append(f'{name}: indexed file is missing')
            continue
        if (((path.name == '.env' or path.name.startswith('.env.'))
             and path.name != '.env.example') or path.suffix.lower() in SECRET_SUFFIXES):
            errors.append(f'{name}: local secret/key filename must not be versioned')
        if path.suffix.lower() != '.md':
            continue
        text = path.read_text(encoding='utf-8')
        if HOST_PATH.search(text):
            errors.append(f'{name}: contributor-specific absolute path')
        text = prose(text)
        targets = LINK.findall(text)
        if name == 'CLAUDE.md':
            targets += re.findall(r'^@([^\s]+)$', text, re.M)
        for raw in targets:
            target = raw.strip()
            if target.startswith('<') and '>' in target:
                target = target[1:target.index('>')]
            else:
                target = target.split(' "', 1)[0]
            url = urlsplit(target)
            if url.scheme in {'http', 'https', 'mailto'}:
                continue
            if url.scheme or url.netloc:
                errors.append(f'{name}: unsupported link {target}')
                continue
            dest = (path.parent / unquote(url.path)).resolve() if url.path else path
            if not dest.is_relative_to(root):
                errors.append(f'{name}: link leaves repository: {target}')
                continue
            if not dest.exists():
                errors.append(f'{name}: broken local reference: {target}')
            elif url.fragment and dest.suffix.lower() == '.md':
                if unquote(url.fragment) not in anchors(prose(dest.read_text(encoding='utf-8'))):
                    errors.append(f'{name}: missing heading: {target}')
    return errors


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    try:
        output = subprocess.check_output(
            ['git', 'ls-files', '--cached', '--others', '--exclude-standard', '-z'], cwd=root)
        paths = output.decode('utf-8').rstrip('\0').split('\0') if output else []
        errors = check_paths(root, paths)
    except (OSError, UnicodeError, subprocess.CalledProcessError) as exc:
        print(f'Repository check could not complete: {exc}', file=sys.stderr)
        return 1
    if errors:
        print('\n'.join(errors), file=sys.stderr)
        return 1
    print(f'Repository checks passed ({len(set(paths))} indexed/non-ignored files).')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
