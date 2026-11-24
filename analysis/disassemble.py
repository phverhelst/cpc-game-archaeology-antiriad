"""Recursive disassembly of the game as it stands at its entry point.

Entry points: &5400 (start), &6EF2 (interrupt handler, installed at &0038), &7923 (keyboard routine, reached
through a table). Writes build/antiriad.asm (not committed: it reproduces the game's code).
Usage: python3 analysis/disassemble.py   (after extract.py)
"""
import os
from cpcarch.rdis import analyse, emit

ICI = os.path.dirname(os.path.abspath(__file__))
BUILD = os.path.join(ICI, '..', 'build')

if __name__ == '__main__':
    mem = open(os.path.join(BUILD, 'antiriad_5400.bin'), 'rb').read()
    code, labels, calls, xrefs = analyse(mem, [0x5400, 0x6EF2, 0x7923])
    open(os.path.join(BUILD, 'antiriad.asm'), 'w').write(emit(mem, code, labels, 0x0000, 0x10000))
    print('build/antiriad.asm: %d instructions, %d routines' % (len(code), len(calls)))
