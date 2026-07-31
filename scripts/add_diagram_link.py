#!/usr/bin/env python3
import re

with open('docs/index.md', 'r', encoding='utf-8') as f:
    content = f.read()

overview = '\n## Schema Overview\n\n- [ER diagram — concept relationships](schema_diagram.md)\n\n'
content = re.sub(r'\n(## (?:Enumerations|Classes))', overview + r'\n\1', content, count=1)

with open('docs/index.md', 'w', encoding='utf-8') as f:
    f.write(content)

print('Added schema overview link to index.md')