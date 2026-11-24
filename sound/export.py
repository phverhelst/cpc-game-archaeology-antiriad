"""Exporte la musique du titre en MusicXML (pour MuseScore, Finale, Sibelius…) et en MIDI.
Durées : 8 divisions par noire (l'unité du jeu est la triple croche). Percussions (bruit du AY) : têtes en
croix dans la même portée en MusicXML, canal 10 en MIDI (grosse caisse, caisse claire, charleston selon la
période du bruit).
Usage : python3 export.py
"""
import os, struct
import musique as M
import partition as P

ICI = os.path.dirname(os.path.abspath(__file__))
NOMS = ['Voix 1', 'Voix 2', 'Voix 3']
CLEFS = [('G', 2), ('G', 2), ('F', 4)]


def perc_hauteur(p, cle):
    if cle == 'F':
        return ('A', 2) if p >= 20 else ('E', 3) if p >= 6 else ('B', 3)
    return ('F', 4) if p >= 20 else ('C', 5) if p >= 6 else ('G', 5)


def musicxml():
    m = P.memoire()
    parties, tempos = [], []
    for son in (1, 2, 3):
        evs, t, total = M.evenements(m, son)
        tempos += t
        parties.append(M.voix_en_mesures(evs, total))
    x = ['<?xml version="1.0" encoding="UTF-8"?>',
         '<!DOCTYPE score-partwise PUBLIC "-//Recordare//DTD MusicXML 3.1 Partwise//EN" "http://www.musicxml.org/dtds/partwise.dtd">',
         '<score-partwise version="3.1"><work><work-title>Antiriad — musique du titre (Amstrad CPC)</work-title></work>',
         '<identification><creator type="composer">Richard Joseph</creator><rights>Palace Software 1986 ; relevé du code du jeu</rights></identification>',
         '<part-list>']
    for i, n in enumerate(NOMS):
        x.append('<score-part id="P%d"><part-name>%s</part-name></score-part>' % (i + 1, n))
    x.append('</part-list>')
    for i, (ms, res) in enumerate(parties):
        x.append('<part id="P%d">' % (i + 1))
        for k, (a, L) in enumerate(ms):
            x.append('<measure number="%d">' % (k + 1))
            h, b = M.chiffrage(L)
            if k == 0:
                x.append('<attributes><divisions>8</divisions><key><fifths>-2</fifths><mode>minor</mode></key>'
                         '<time><beats>%d</beats><beat-type>%d</beat-type></time><clef><sign>%s</sign><line>%d</line></clef></attributes>'
                         % ((h, b) + CLEFS[i]))
            elif L != ms[k - 1][1]:
                x.append('<attributes><time><beats>%d</beats><beat-type>%d</beat-type></time></attributes>' % (h, b))
            if i == 0:
                for (tt, v) in tempos:
                    if a <= tt < a + L:
                        x.append('<direction placement="above"><direction-type><metronome><beat-unit>quarter</beat-unit>'
                                 '<per-minute>%d</per-minute></metronome></direction-type><sound tempo="%.2f"/></direction>'
                                 % (round(M.tempo_reel(v)), M.tempo_reel(v)))
            for f in res[k]:
                typ, points = M.TYPES[f['val']]
                if f['genre'] == 'silence':
                    x.append('<note><rest/><duration>%d</duration><type>%s</type>%s</note>' % (f['val'], typ, '<dot/>' * points))
                    continue
                if f['genre'] == 'perc':
                    st, oc = perc_hauteur(f['valeur'], CLEFS[i][0])
                    x.append('<note><pitch><step>%s</step><octave>%d</octave></pitch>'
                             '<duration>%d</duration><type>%s</type>%s<notehead>x</notehead></note>' % (st, oc, f['val'], typ, '<dot/>' * points))
                    continue
                lettre, alt, octave = M.orthographe(f['valeur'])
                lie_av = f.get('lie_av')
                x.append('<note><pitch><step>%s</step>%s<octave>%d</octave></pitch><duration>%d</duration>%s%s<type>%s</type>%s%s</note>' % (
                    lettre, '<alter>%d</alter>' % alt if alt else '', octave, f['val'],
                    '<tie type="stop"/>' if lie_av else '', '<tie type="start"/>' if f['lie'] else '', typ, '<dot/>' * points,
                    '<notations>%s%s</notations>' % ('<tied type="stop"/>' if lie_av else '', '<tied type="start"/>' if f['lie'] else '')
                    if (f['lie'] or lie_av) else ''))
            x.append('</measure>')
        x.append('</part>')
    x.append('</score-partwise>')
    return '\n'.join(x)


def marquer_liaisons():
    """Ajoute 'lie_av' aux figures qui prolongent la précédente (pour la fin des liaisons en MusicXML)."""
    orig = M.voix_en_mesures

    def avec(evs, total):
        ms, res = orig(evs, total)
        prec = None
        for mesure in res:
            for f in mesure:
                f['lie_av'] = bool(prec and prec['lie'])
                prec = f
        return ms, res
    M.voix_en_mesures = avec


def vlq(n):
    o = [n & 0x7F]
    n >>= 7
    while n:
        o.insert(0, (n & 0x7F) | 0x80); n >>= 7
    return bytes(o)


def midi():
    m = P.memoire()
    ppq = 8
    pistes = []
    tempo_ev = []
    for son, canal in ((1, 0), (2, 1), (3, 2)):
        evs, tempos, total = M.evenements(m, son)
        tempo_ev += tempos
        ev = []
        for (t, d, g, v) in evs:
            if g == 'note':
                ev.append((t, 0x90 | canal, v, 90)); ev.append((t + d, 0x80 | canal, v, 0))
            elif g == 'perc':
                n = 36 if v >= 20 else 38 if v >= 6 else 42
                ev.append((t, 0x99, n, 90)); ev.append((t + max(1, d), 0x89, n, 0))
        ev.sort(key=lambda e: (e[0], e[1] & 0xF0 == 0x90))
        data, prec = bytearray(), 0
        data += vlq(0) + bytes([0xC0 | canal, 80 if canal < 2 else 38])   # carré, basse synthétique
        for (t, st, n, vel) in ev:
            data += vlq(t - prec) + bytes([st, n, vel]); prec = t
        data += vlq(0) + b'\xFF\x2F\x00'
        pistes.append(bytes(data))
    data, prec = bytearray(), 0
    for (t, bpm) in sorted(tempo_ev):
        us = round(60_000_000 / M.tempo_reel(bpm))
        data += vlq(t - prec) + b'\xFF\x51\x03' + us.to_bytes(3, 'big'); prec = t
    data += vlq(0) + b'\xFF\x58\x04\x03\x02\x18\x08' + vlq(0) + b'\xFF\x2F\x00'
    pistes.insert(0, bytes(data))
    out = b'MThd' + struct.pack('>IHHH', 6, 1, len(pistes), ppq)
    for p in pistes:
        out += b'MTrk' + struct.pack('>I', len(p)) + p
    return out


if __name__ == '__main__':
    marquer_liaisons()
    open(os.path.join(ICI, 'antiriad_titre_cpc.musicxml'), 'w', encoding='utf-8').write(musicxml())
    open(os.path.join(ICI, 'antiriad_titre_cpc.mid'), 'wb').write(midi())
    print('antiriad_titre_cpc.musicxml, antiriad_titre_cpc.mid')
