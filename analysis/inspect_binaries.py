"""Static inspection of the supplied PE/COFF files; never executes the app.

Optional dependencies: pefile and capstone, installable in a temporary directory.
Usage: python inspect_binaries.py ROOT OUTPUT [TEMP_PACKAGE_DIRECTORY]
"""
from pathlib import Path
import ctypes
import hashlib
import json
import os
import re
import struct
import sys

ROOT = Path(sys.argv[1]).resolve()
OUT = Path(sys.argv[2]).resolve()
if len(sys.argv) > 3:
    sys.path.insert(0, sys.argv[3])
import pefile
from capstone import Cs, CS_ARCH_X86, CS_MODE_64

OUT.mkdir(parents=True, exist_ok=True)
_dll_directory = os.add_dll_directory(str(ROOT))
_runtime = ctypes.CDLL(str(ROOT / 'libstdc++-6.dll'))
_demangle = _runtime.__cxa_demangle
_demangle.argtypes = [ctypes.c_char_p, ctypes.c_void_p,
                      ctypes.c_void_p, ctypes.POINTER(ctypes.c_int)]
_demangle.restype = ctypes.c_void_p

def demangle(name):
    if not name.startswith('_Z'):
        return name
    status = ctypes.c_int()
    ptr = _demangle(name.encode(), None, None, ctypes.byref(status))
    return ctypes.string_at(ptr).decode(errors='replace') if ptr else name

def strings(data):
    result = [{'offset': m.start(), 'text': m.group().decode('ascii')}
              for m in re.finditer(rb'[\x20-\x7e]{4,}', data)]
    result += [{'offset': m.start(), 'text': m.group().decode('utf-16le')}
               for m in re.finditer(rb'(?:[\x20-\x7e]\x00){4,}', data)]
    return sorted(result, key=lambda v: v['offset'])

def inspect_pe(path):
    data = path.read_bytes()
    pe = pefile.PE(data=data)
    imports = {}
    for entry in getattr(pe, 'DIRECTORY_ENTRY_IMPORT', []):
        imports[entry.dll.decode()] = [i.name.decode(errors='replace')
            if i.name else '#' + str(i.ordinal) for i in entry.imports]
    delayed = {}
    for entry in getattr(pe, 'DIRECTORY_ENTRY_DELAY_IMPORT', []):
        delayed[entry.dll.decode()] = [i.name.decode(errors='replace')
            if i.name else '#' + str(i.ordinal) for i in entry.imports]
    result = dict(file=path.relative_to(ROOT).as_posix(), size=len(data),
                  sha256=hashlib.sha256(data).hexdigest(),
                  machine=hex(pe.FILE_HEADER.Machine),
                  timestamp=pe.FILE_HEADER.TimeDateStamp,
                  subsystem=pe.OPTIONAL_HEADER.Subsystem,
                  image_base=hex(pe.OPTIONAL_HEADER.ImageBase),
                  imports=imports, delay_imports=delayed,
                  sections=[s.Name.rstrip(b'\0').decode() for s in pe.sections])
    if path.suffix.lower() == '.exe':
        (OUT / (path.name + '.strings.json')).write_text(
            json.dumps(strings(data), indent=2, ensure_ascii=False), encoding='utf8')
    return result

def inspect_coff(path):
    data = path.read_bytes()
    machine, nsec, timestamp, symptr, nsym, opt, flags = struct.unpack_from('<HHIIIHH', data)
    st = symptr + nsym * 18
    def cstring(offset):
        return data[offset:data.index(b'\0', offset)].decode(errors='replace')
    def name8(raw):
        if raw[:4] == b'\0' * 4:
            return cstring(st + struct.unpack_from('<I', raw, 4)[0])
        name = raw.rstrip(b'\0').decode(errors='replace')
        return cstring(st + int(name[1:])) if name.startswith('/') else name
    sections = []
    for i in range(nsec):
        off = 20 + opt + 40 * i
        raw, vs, va, size, ptr, rp, lp, nr, nl, chars = struct.unpack_from('<8sIIIIIIHHI', data, off)
        sections.append(dict(name=name8(raw), size=size, pointer=ptr,
                             relocation_pointer=rp, relocation_count=nr,
                             characteristics=chars))
    syms = {}
    i = 0
    while i < nsym:
        off = symptr + 18 * i
        raw, value, sec, typ, storage, aux = struct.unpack_from('<8sIhHBB', data, off)
        name = name8(raw)
        syms[i] = dict(name=name, demangled=demangle(name), value=value,
                       section=sec, type=typ, storage=storage)
        i += 1 + aux
    md = Cs(CS_ARCH_X86, CS_MODE_64)
    output = []
    for secidx, sec in enumerate(sections, 1):
        relocs = {}
        for j in range(sec['relocation_count']):
            addr, idx, typ = struct.unpack_from('<IIH', data, sec['relocation_pointer'] + 10*j)
            relocs[addr] = (syms.get(idx, {'demangled': '?'}), typ)
        sec['relocations'] = [{'offset': a, 'symbol': s['demangled'], 'type': t}
                              for a, (s, t) in relocs.items()]
        if not sec['characteristics'] & 0x20:
            continue
        labels = {s['value']: s['demangled'] for s in syms.values()
                  if s['section'] == secidx and s['type'] == 0x20}
        output.append('\nSECTION ' + sec['name'])
        for ins in md.disasm(data[sec['pointer']:sec['pointer']+sec['size']], 0):
            if ins.address in labels:
                output.append('\n' + labels[ins.address] + ':')
            comments = []
            for a in range(ins.address, ins.address + ins.size):
                if a in relocs:
                    sym, typ = relocs[a]
                    comment = f"{sym['demangled']} (reloc {typ:#x})"
                    if sym.get('section', 0) > 0 and a + 4 <= sec['size']:
                        target = sections[sym['section']-1]
                        addend = struct.unpack_from('<i', data, sec['pointer'] + a)[0]
                        offset = sym['value'] + addend
                        if 0 <= offset < target['size'] and not target['characteristics'] & 0x20:
                            raw = data[target['pointer']+offset:target['pointer']+min(offset+160, target['size'])]
                            text = raw.split(b'\0')[0]
                            comment += f" + {addend:#x}: {text!r} [hex {raw[:16].hex()}]"
                    comments.append(comment)
            output.append(f"{ins.address:08x} {ins.mnemonic:8} {ins.op_str:45}" +
                          (' ; ' + ' | '.join(comments) if comments else ''))
    (OUT / (path.name + '.asm.txt')).write_text('\n'.join(output), encoding='utf8')
    (OUT / (path.name + '.strings.json')).write_text(
        json.dumps(strings(data), indent=2, ensure_ascii=False), encoding='utf8')
    return dict(file=path.name, machine=hex(machine), sections=sections,
                symbols=list(syms.values()))

pes = [inspect_pe(p) for p in sorted(ROOT.rglob('*'))
       if p.suffix.lower() in ('.dll', '.exe') and '.git' not in p.parts]
coffs = [inspect_coff(p) for p in sorted(ROOT.glob('*.o'))]
(OUT / 'pe_inventory.json').write_text(json.dumps(pes, indent=2), encoding='utf8')
(OUT / 'coff_inventory.json').write_text(json.dumps(coffs, indent=2), encoding='utf8')
for pe in pes:
    print(pe['file'] + ': ' + ', '.join(pe['imports']))
for obj in coffs:
    if obj['file'] in ('main.o', 'mainwindow.o', 'settings.o', 'fft.o'):
        print('\n' + obj['file'])
        for sym in obj['symbols']:
            if sym['section'] > 0 and sym['type'] == 0x20:
                print('  ' + sym['demangled'])
