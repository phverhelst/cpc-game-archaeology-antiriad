"""Screens rendered by the emulator, each display line with the palette and mode of its interrupt slot.

Writes build/ecran_titre.png (title screen, used by intro/video.py) and build/ecran_jeu.png (first room
after pressing fire). Usage: python3 analysis/screens.py   (after extract.py)
"""
import os
from cpcarch.emu import CPC, KEY

ICI = os.path.dirname(os.path.abspath(__file__))
BUILD = os.path.join(ICI, '..', 'build')

if __name__ == '__main__':
    c = CPC(open(os.path.join(BUILD, 'antiriad_5400.bin'), 'rb').read(), 0x5400, 0xBFF0)
    c.run(500_000)
    c.shot_raster(os.path.join(BUILD, 'ecran_titre.png'))
    c.keys = {KEY['fire']}; c.run(500_000)
    c.keys = set(); c.run(1_000_000)
    c.shot_raster(os.path.join(BUILD, 'ecran_jeu.png'))
    print('build/ecran_titre.png, build/ecran_jeu.png')
