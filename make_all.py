"""Regenerate every product of the study and run every verification, from build/ (see extract.py).

    python3 make_all.py            everything
    python3 make_all.py generate   products only
    python3 make_all.py verify     verifications only

Each step runs in its own folder. External tools: ffmpeg (audio, video), rsvg-convert (score), node (JS checks).
"""
import os, subprocess, sys, time

ICI = os.path.dirname(os.path.abspath(__file__))
GENERATE = [
    ('analysis', ['python3', 'disassemble.py']),
    ('analysis', ['python3', 'screens.py']),
    ('movement', ['python3', 'tables.py']),
    ('movement', ['python3', 'trajectoires.py']),
    ('rooms', ['python3', 'capturer.py']),
    ('enemies', ['python3', 'extraire.py']),
    ('sound', ['python3', 'ecouter.py']),
    ('sound', ['python3', 'export.py']),
    ('sound', ['python3', 'gravure.py']),
    ('sandbox', ['python3', 'construire.py']),
    ('sandbox', ['python3', 'construire_armure.py']),
    ('sandbox', ['python3', 'construire_carte.py']),
    ('intro', ['python3', 'chargeur.py']),
    ('intro', ['python3', 'images.py']),
    ('intro', ['python3', 'rideau.py']),
    ('intro', ['python3', 'video.py']),
    ('intro', ['python3', 'fin.py']),
]
VERIFY = [
    ('movement', ['python3', 'verif.py']),
    ('movement', ['python3', 'verif_armure.py']),
    ('enemies', ['python3', 'verif.py']),
    ('sound', ['python3', 'verif.py']),
    ('sandbox', ['python3', 'verif_js.py']),
    ('sandbox', ['python3', 'verif_armure_js.py']),
    ('sandbox', ['python3', 'verif_monde_js.py']),
]

if __name__ == '__main__':
    what = sys.argv[1] if len(sys.argv) > 1 else 'all'
    steps = (GENERATE if what in ('all', 'generate') else []) + (VERIFY if what in ('all', 'verify') else [])
    failed = []
    for folder, cmd in steps:
        t = time.time()
        r = subprocess.run(cmd, cwd=os.path.join(ICI, folder), capture_output=True, text=True)
        last = (r.stdout.strip().splitlines() or [''])[-1]
        print('%-9s %-24s %6.1fs  %s' % (folder, cmd[-1], time.time() - t, 'ok  ' + last if r.returncode == 0 else 'FAILED'),
              flush=True)
        if r.returncode:
            print(r.stdout[-2000:], r.stderr[-2000:])
            failed.append('%s/%s' % (folder, cmd[-1]))
    print('all steps passed' if not failed else 'failed: ' + ', '.join(failed))
    sys.exit(1 if failed else 0)
