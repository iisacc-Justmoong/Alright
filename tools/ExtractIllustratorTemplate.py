"""Extract native streams from a blank Illustrator 2020+ PDF-compatible AI saved without compression.

Usage: python3 tools/ExtractIllustratorTemplate.py INPUT.ai resources/DocumentTemplates
The source must have one empty RGB 1920x1080 artboard; runtime resizes both native and PDF records.
"""
import re
import sys
from pathlib import Path

source = Path(sys.argv[1]).read_bytes()
output = Path(sys.argv[2])
# Native stream IDs come from the template dictionary, not fixed PDF object numbers.
match = re.search(rb'<</AIMetaData (\d+) 0 R(.*?)>>', source, re.S)
if not match:
    raise ValueError('Missing native Illustrator dictionary')
refs = re.findall(rb'/AIPrivateData(\d+) (\d+) 0 R', match[2])
refs.sort(key=lambda x: int(x[0]))
def stream(number):
    obj = re.search(rb'\b' + number + rb' 0 obj\s*<</Length (\d+)>>stream\r?\n', source)
    if not obj:
        raise ValueError('Save without compression before extracting native streams')
    return source[obj.end():obj.end() + int(obj[1])]
metadata = stream(match[1])
native = b''.join(stream(number) for _, number in refs)
for data in [native, metadata]:
    if not data.startswith(b'%!PS-Adobe') or data.count(b'%AI3_Cropmarks: 0 -1080 1920 0') != 1:
        raise ValueError('Expected uncompressed blank 1920x1080 Illustrator artboard')
if native.count(b'%_1920 -1080 /RealPointRelToROrigin') != 1:
    raise ValueError('Expected one native artboard record')
output.mkdir(parents=True, exist_ok=True)
(output / 'Blank.aiprivate').write_bytes(native)
(output / 'Blank.aimetadata').write_bytes(metadata)
