#!/usr/bin/env python3
"""Check repository Markdown file/image links and local heading anchors; no network."""
from pathlib import Path
import re
import sys
from urllib.parse import unquote, urlsplit

ROOT=Path(__file__).resolve().parents[1]


def anchors(text):
    found=set(re.findall(r'(?:id|name)=["\']([^"\']+)["\']',text))
    counts={}
    for line in re.sub(r'```.*?```','',text,flags=re.S).splitlines():
        if not re.match(r'^#{1,6} ',line): continue
        title=re.sub(r'^#+\s+','',line).strip().lower()
        title=re.sub(r'<[^>]+>','',title)
        slug=re.sub(r'[^\w\- ]','',title).replace(' ','-')
        count=counts.get(slug,0);counts[slug]=count+1
        found.add(slug+(f'-{count}' if count else ''))
    return found


def main():
    files=[ROOT/'README.md',ROOT/'CHANGELOG.md',ROOT/'WSJTX-REBUILD-HANDOFF.md',ROOT/'AGENTS.md',*sorted((ROOT/'docs').rglob('*.md'))]
    errors=[];checked=0
    for source in files:
        if not source.exists(): continue
        text=re.sub(r'```.*?```','',source.read_text(),flags=re.S)
        for target in re.findall(r'!?\[[^\]]*\]\(([^)]+)\)',text):
            target=target.split(' "',1)[0].strip('<>')
            url=urlsplit(target)
            if url.scheme or url.netloc: continue
            dest=(source.parent/unquote(url.path)).resolve() if url.path else source
            checked+=1
            if not dest.exists():errors.append(f'{source.relative_to(ROOT)}: missing {target}')
            elif url.fragment and dest.suffix=='.md' and unquote(url.fragment) not in anchors(dest.read_text()):errors.append(f'{source.relative_to(ROOT)}: missing anchor {target}')
    for error in errors:print(error)
    print(f'Checked {checked} local links across {len(files)} Markdown files; {len(errors)} errors.')
    return bool(errors)


if __name__=='__main__':sys.exit(main())
