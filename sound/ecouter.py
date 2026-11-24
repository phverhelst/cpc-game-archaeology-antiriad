"""Fabrique les enregistrements : la musique de l'écran titre (une boucle, 115,6 s), la même après une partie, et le jingle de l'armure,
calculés par le pilote transcrit (pilote.py) puis rendus par ay.py. Usage : python3 ecouter.py"""
import os, subprocess
import pilote as P
from cpcarch import ay

ICI = os.path.dirname(os.path.abspath(__file__))
BIN = os.path.join(ICI, '..', 'build', 'antiriad_5400.bin')


def jouer(sons, tours):
    m = bytearray(open(BIN, 'rb').read())
    for voie, son in sons:
        P.lancer(m, voie, son)
    return [P.tour(m) for _ in range(tours)]


def sauver(nom, regs):
    w = os.path.join('/tmp', nom + '.wav')
    ay.ecrire_wav(w, ay.synthese(regs))
    sortie = os.path.join(ICI, nom + '.mp3')
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-i', w, '-b:a', '96k', sortie], check=True)
    return sortie


def titre_apres_partie():
    """La fin de la mise en route de l'armure lance le son 6 sur une « voie 3 » qui n'existe pas (&608C) : la
    fiche écrite en &7AE5 efface l'enveloppe de bruit et les instruments 0 à 2. Le titre rejoué ensuite change."""
    m = bytearray(open(BIN, 'rb').read())
    P.lancer(m, 2, 5); P.lancer(m, 3, 6)
    for voie, son in ((0, 1), (1, 2), (2, 3)):
        P.lancer(m, voie, son)
    return [P.tour(m) for _ in range(11560)]


if __name__ == '__main__':
    print(sauver('antiriad_titre_cpc', jouer([(0, 1), (1, 2), (2, 3)], 11560)))
    print(sauver('antiriad_titre_cpc_apres_une_partie', titre_apres_partie()))
    print(sauver('mise_en_route_armure', jouer([(0, 4)], 400)))
