"""Assemble the standalone page after editing its template or shared sections."""
from pathlib import Path

root = Path(__file__).resolve().parent
for target in ('index', 'contact'):
    page = (root / (target + '.template.html')).read_text(encoding='utf-8')
    for name in ('header.html', 'footer.html'):
        page = page.replace("{% include '" + name + "' %}", (root / name).read_text(encoding='utf-8'))
    (root / (target + '.html')).write_text(page, encoding='utf-8')
    print('Built ' + target + '.html')
