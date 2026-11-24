"""From your own copy of the game to build/: the files every other script reads.

    python3 extract.py path/to/The_Sacred_Armour_of_Antiriad__2013-10-17__ENGLISH__CNGSOFT.dsk

Steps, each checked against checksums.sha256:
  1. read ANTIRIDE.BAS from the disk image (AMSDOS);
  2. run the CNGSoft loader in the Z80 simulator until it jumps to the game at &5400
     -> build/antiriad_5400.bin, the 64 KB memory at the game's entry point;
  3. run the game in the emulator, press fire on the title screen, stop at the start of the main loop
     (&54FA) -> build/antiriad_54FA.bin, the starting point of the playable sandbox.

Another release of the game (original tape, another conversion) will give different hashes: the scripts may
still work, but the addresses and figures in the documentation were established on this one.
"""
import hashlib, os, sys
from cpcarch.dsk import Disk
from cpcarch.loader import run_loader

ICI = os.path.dirname(os.path.abspath(__file__))
BUILD = os.path.join(ICI, 'build')
EXPECTED = {}
for line in open(os.path.join(ICI, 'checksums.sha256')):
    h, name = line.split()
    EXPECTED[os.path.basename(name)] = h


def save(name, data):
    open(os.path.join(BUILD, name), 'wb').write(data)
    h = hashlib.sha256(data).hexdigest()
    ok = h == EXPECTED.get(name)
    print('%-22s %7d bytes  %s' % (name, len(data), 'sha256 ok' if ok else 'sha256 DIFFERS: ' + h))
    return ok


if __name__ == '__main__':
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    image = open(sys.argv[1], 'rb').read()
    os.makedirs(BUILD, exist_ok=True)
    h = hashlib.sha256(image).hexdigest()
    same = h in EXPECTED.values()
    print('disk image            %s' % ('the release studied' if same else 'NOT the release studied (sha256 %s)' % h))
    data, header = Disk(image).read('ANTIRIDE.BAS')
    ok = save('ANTIRIDE.BAS', data)
    mem, regs, log = run_loader(data, load=0x0170, start=0x0190, entry=0x5400)
    ok = save('antiriad_5400.bin', mem) and ok
    sys.path.insert(0, os.path.join(ICI, 'enemies'))
    import trace as TR                                 # enemies/trace.py: start a game, stop at &54FA
    c = TR.depart()
    ok = save('antiriad_54FA.bin', bytes(c.mem)) and ok
    print('done' if ok else 'done, with differences: the documentation may not match your release')
