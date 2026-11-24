"""Salle d'essai du bac à sable, construite avec les règles de collision du jeu.

La zone de jeu fait 80 octets de large et va de la ligne &32 à la ligne &B9 : 17 rangées de 8 lignes.
La première ligne de chaque rangée a le rang 2 dans son bloc de huit (&32 & 7 == 2), la seule où le
jeu reconnaît un sol. Une case fait 4 octets sur 8 lignes.
  '.' vide
  '=' plateforme : ligne du haut en &CC (stylo 3, reconnu par le motif &8E1C), 3 lignes de corps en &C0 (stylo 1, inerte)
  '#' bloc : 8 lignes en &FC (stylo 7, reconnu comme mur par &67B6, et comme sol sur sa ligne du haut)
"""
PLAN = [
    "....................",
    "....................",
    "....................",
    "....................",
    "....................",
    "....................",
    "..=====.............",
    "....................",
    "....................",
    "..........=====.....",
    "....................",
    "=====...............",
    "...............#....",
    "...............#....",
    "......#........#....",
    "......#........#....",
    "====================",
]
HAUT_ZONE, COLONNES, LIGNES_CASE, OCTETS_CASE = 0x32, 80, 8, 4
OCTETS = {'=': [0xCC, 0xC0, 0xC0, 0xC0, 0, 0, 0, 0], '#': [0xFC] * 8, '.': [0] * 8}


def construire(plan=PLAN):
    ecran = [[0] * COLONNES for _ in range(256)]
    for r, rangee in enumerate(plan):
        for c, case in enumerate(rangee):
            for k, b in enumerate(OCTETS[case]):
                for i in range(OCTETS_CASE):
                    ecran[HAUT_ZONE + r * LIGNES_CASE + k][c * OCTETS_CASE + i] = b
    return ecran


class EcranSalle:
    """Même interface que movement/tal.EcranMemoire. Hors de la salle, l'octet lu vaut 0."""
    def __init__(self, plan=PLAN):
        self.e = construire(plan)

    def octet(self, ligne, colonne):
        if 0 <= ligne < 256 and 0 <= colonne < COLONNES:
            return self.e[ligne][colonne]
        return 0
