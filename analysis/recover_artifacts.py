"""Recover embedded SVG resources and correlate object code with the executable."""
from pathlib import Path
import hashlib
import json
import re
import struct
import sys
import xml.etree.ElementTree as ET
import zlib

ROOT = Path(sys.argv[1]).resolve()
EVIDENCE = ROOT / 'analysis' / 'evidence'
RECOVERED = ROOT / 'analysis' / 'recovered-resources'
RECOVERED.mkdir(parents=True, exist_ok=True)
inventory = json.loads((EVIDENCE / 'coff_inventory.json').read_text())

source = (ROOT / 'qrc_reources.cpp').read_text()
data_source = source.split('qt_resource_data[] = {', 1)[1].split('};', 1)[0]
resource_blocks = re.split(r'// [^\n]*/art/([^\n]+)\n', data_source)
resources = []
for name, contents in zip(resource_blocks[1::2], resource_blocks[2::2]):
    name = name.strip()
    payload = bytes(int(x, 16) for x in re.findall(r'0x([0-9a-fA-F]{1,2})\s*,?', contents))
    length = int.from_bytes(payload[:4], 'big')
    image = payload[4:4+length]
    assert len(image) == length, name
    compressed = not image.startswith(b'<')
    if compressed:
        uncompressed_length = int.from_bytes(image[:4], 'big')
        image = zlib.decompress(image[4:])
        assert len(image) == uncompressed_length, name
    ET.fromstring(image)
    destination = RECOVERED / 'art' / name
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(image)
    resources.append(dict(file='art/' + name, size=len(image), compressed_in_original=compressed,
                          sha256=hashlib.sha256(image).hexdigest()))
qrc = '<RCC>\n  <qresource prefix="/">\n' + ''.join(
    '    <file>' + item['file'] + '</file>\n' for item in resources
) + '  </qresource>\n</RCC>\n'
(RECOVERED / 'reources.qrc').write_text(qrc, encoding='utf8')

exe = (ROOT / 'SonarFrontEnd.exe').read_bytes()
correlations = []
for obj in inventory:
    code = next((s for s in obj['sections'] if s['name'] == '.text'), None)
    if not code or code['size'] < 20:
        continue
    data = (ROOT / obj['file']).read_bytes()[code['pointer']:code['pointer']+code['size']]
    mask = set()
    for rel in code['relocations']:
        mask.update(range(rel['offset'], rel['offset'] + (8 if rel['type'] == 1 else 4)))
    intervals = []
    start = 0
    for i in range(len(data)+1):
        if i == len(data) or i in mask:
            if i > start:
                intervals.append((start, i))
            start = i+1
    begin, end = max(intervals, key=lambda item: item[1]-item[0])
    seed = data[begin:end]
    at = exe.find(seed)
    candidate = -1
    mismatches = []
    while at >= 0:
        possible = at-begin
        if 0 <= possible <= len(exe)-len(data):
            differences = [i for i, byte in enumerate(data)
                           if i not in mask and exe[possible+i] != byte]
            if candidate < 0 or len(differences) < len(mismatches):
                candidate, mismatches = possible, differences
            if not differences:
                break
        at = exe.find(seed, at+1)
    correlations.append(dict(file=obj['file'], object_sha256=hashlib.sha256((ROOT/obj['file']).read_bytes()).hexdigest(),
                             text_size=len(data), seed_size=len(seed),
                             executable_file_offset=candidate,
                             verified_nonrelocated_bytes=len(data)-len(mask) if candidate>=0 else 0,
                             mismatch_count=len(mismatches) if candidate>=0 else None))

report = dict(resources=resources, object_executable_correlations=correlations)
(EVIDENCE / 'recovery.json').write_text(json.dumps(report, indent=2), encoding='utf8')
print(json.dumps(report, indent=2))
