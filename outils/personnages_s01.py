#!/usr/bin/env python3
"""Personnages du souvenir n°1, dessinés pixel par pixel (grille du décor : 192 × 128).

Chaque personnage est une fonction qui dessine une pose dans une petite image RGBA, pieds en bas.
Le script écrit une planche par personnage (une image par pose, côte à côte) et un fichier JSON
qui donne au jeu la taille des images, l'ordre des poses et le point d'ancrage (les pieds).

  python outils/personnages_s01.py      # écrit jeu/assets/s01/persos.png + persos.json
"""
import json
from pathlib import Path

from PIL import Image, ImageDraw

RACINE = Path(__file__).resolve().parent.parent
DEST = RACINE / 'jeu' / 'assets' / 's01'

C = {  # palette des personnages : tons plats, une ombre, un liseré chaud côté lampe
    'lisere': (246, 186, 116),
    # la femme qui porte
    'f_cheveux': (58, 36, 32), 'f_pull': (62, 74, 92), 'f_pull_o': (44, 52, 68), 'f_jupe': (52, 38, 46),
    'f_peau': (176, 116, 92), 'f_chaussure': (34, 24, 26),
    # Yoann, deux ou trois ans
    'y_cheveux': (176, 122, 72), 'y_cheveux_o': (140, 94, 56), 'y_peau': (226, 168, 132), 'y_peau_o': (196, 136, 108),
    'y_pull': (168, 58, 58), 'y_pull_o': (124, 42, 48), 'y_pantalon': (196, 160, 112), 'y_chaussure': (90, 54, 40),
    'y_oeil': (72, 128, 210),
    # la mamie
    'm_cheveux': (196, 188, 178), 'm_cheveux_o': (146, 140, 134), 'm_peau': (214, 156, 126), 'm_peau_o': (182, 126, 104),
    'm_gilet': (204, 172, 130), 'm_gilet_o': (160, 130, 98), 'm_corsage': (196, 104, 104), 'm_jupe': (92, 58, 42),
    'm_bas': (164, 120, 100), 'm_chaussure': (42, 28, 24), 'm_bouche': (110, 40, 44), 'm_oeil': (52, 34, 34),
    # le frère, quatre ans
    'b_cheveux': (104, 66, 40), 'b_cheveux_o': (78, 48, 30), 'b_peau': (220, 160, 126), 'b_peau_o': (190, 132, 104),
    'b_tshirt': (122, 154, 184), 'b_tshirt_o': (92, 118, 148), 'b_pantalon': (104, 74, 50), 'b_chaussure': (40, 40, 48),
    'b_blanc': (236, 232, 226), 'b_oeil': (64, 120, 204),
    # le jouet
    'j_blanc': (244, 240, 230), 'j_gris': (170, 166, 160), 'j_gris_f': (120, 116, 112), 'j_rouge': (196, 48, 48),
    'j_vitre': (52, 64, 88),
}


class Pinceau:
    def __init__(self, w, h, miroir=False):
        self.im = Image.new('RGBA', (w, h), (0, 0, 0, 0))
        self.d = ImageDraw.Draw(self.im)
        self.w, self.h, self.miroir = w, h, miroir

    def _x(self, x):
        return self.w - 1 - x if self.miroir else x

    def px(self, x, y, c):
        if 0 <= x < self.w and 0 <= y < self.h:
            self.im.putpixel((self._x(x), y), C[c] + (255,))

    def rect(self, x0, y0, x1, y1, c):  # bornes incluses
        for y in range(y0, y1 + 1):
            for x in range(x0, x1 + 1):
                self.px(x, y, c)

    def ovale(self, x0, y0, x1, y1, c):
        cx, cy, rx, ry = (x0 + x1) / 2, (y0 + y1) / 2, (x1 - x0 + 1) / 2, (y1 - y0 + 1) / 2
        for y in range(y0, y1 + 1):
            for x in range(x0, x1 + 1):
                if ((x + .5 - cx - .5) / rx) ** 2 + ((y + .5 - cy - .5) / ry) ** 2 <= 1.0:
                    self.px(x, y, c)

    def poly(self, pts, c):
        if self.miroir:
            pts = [(self.w - 1 - x, y) for x, y in pts]
        self.d.polygon(pts, fill=C[c] + (255,))

    def trait(self, pts, c):
        if self.miroir:
            pts = [(self.w - 1 - x, y) for x, y in pts]
        self.d.line(pts, fill=C[c] + (255,), width=1)

    def estomper(self, y_haut, y_bas):
        """La tête de la femme se perd : de plus en plus transparente vers le haut, en trois paliers."""
        a = self.im.load()
        for y in range(0, y_bas + 1):
            t = 0.0 if y <= y_haut else (y - y_haut) / max(1, (y_bas - y_haut))
            al = 70 if t < .4 else 140 if t < .8 else 210
            for x in range(self.w):
                r, g, b, v = a[x, y]
                if v: a[x, y] = (r, g, b, min(v, al))

    def lisere(self, cote='droite', force=.55):
        """Liseré chaud sur le bord tourné vers la lampe (après le miroir, en coordonnées de l'image)."""
        a = self.im.load()
        pris = []
        for y in range(self.h):
            for x in range(self.w):
                if a[x, y][3] == 0: continue
                vx = x + 1 if cote == 'droite' else x - 1
                if not (0 <= vx < self.w) or a[vx, y][3] == 0: pris.append((x, y))
        for x, y in pris:
            r, g, b, al = a[x, y]; l = C['lisere']
            a[x, y] = (int(r + (l[0] - r) * force), int(g + (l[1] - g) * force), int(b + (l[2] - b) * force), al)

    def effacer_haut(self, y_haut, y_bas):
        """La tête de la femme se perd : tramage de plus en plus transparent vers le haut."""
        bayer = [0, 8, 2, 10, 12, 4, 14, 6, 3, 11, 1, 9, 15, 7, 13, 5]
        a = self.im.load()
        for y in range(0, y_bas + 1):
            t = 1.0 if y <= y_haut else (y_bas - y) / max(1, (y_bas - y_haut))  # 1 = effacé
            for x in range(self.w):
                if a[x, y][3] and bayer[(y % 4) * 4 + (x % 4)] / 16 < t * .82:
                    a[x, y] = (0, 0, 0, 0)


# ------------------------------------------------------------------ le jouet, en petit (dans les mains)
def petit_avion(p, x, y):
    """Avion de 9 × 5 pixels, nez à droite. (x, y) = coin haut gauche."""
    p.px(x, y, 'j_gris'); p.px(x, y + 1, 'j_gris')        # dérive
    p.rect(x, y + 2, x + 7, y + 3, 'j_blanc')             # fuselage
    p.px(x + 8, y + 3, 'j_blanc')                         # nez
    p.px(x + 6, y + 2, 'j_vitre')                         # cockpit
    p.rect(x + 2, y + 3, x + 3, y + 3, 'j_rouge')         # liseré rouge
    p.rect(x + 3, y + 4, x + 5, y + 4, 'j_gris')          # aile


def petit_robot(p, x, y):
    """Robot de 6 × 6 pixels (ailes comprises). (x, y) = coin haut gauche du torse."""
    p.rect(x + 1, y, x + 2, y, 'j_blanc'); p.px(x + 2, y, 'j_vitre')         # tête et visière
    p.rect(x, y + 1, x + 3, y + 3, 'j_blanc'); p.px(x + 1, y + 2, 'j_rouge')  # torse
    p.px(x - 1, y + 1, 'j_gris'); p.px(x + 4, y + 1, 'j_gris')               # ailes repliées
    p.px(x + 1, y + 4, 'j_blanc'); p.px(x + 2, y + 4, 'j_blanc')
    p.px(x + 1, y + 5, 'j_gris'); p.px(x + 2, y + 5, 'j_gris')               # jambes


# ------------------------------------------------------------------ la femme qui porte Yoann
FEMME_W, FEMME_H = 44, 70


def femme(pose='regarde', souffle=0, jouet='avion'):
    """La femme de profil vers la droite, Yoann assis sur son avant-bras, tourné vers la droite.
    Poses de Yoann : regarde (l'avion devant les yeux), tend (vers la mamie), serre (contre lui),
    baisse (vers son frère)."""
    p = Pinceau(FEMME_W, FEMME_H)
    s = -souffle  # le haut du corps monte d'un pixel à l'inspiration
    # jambes et chaussures (pieds vers la droite)
    p.rect(15, 60, 17, 66, 'f_jupe'); p.rect(19, 60, 21, 66, 'f_jupe')
    p.rect(15, 67, 19, 69, 'f_chaussure'); p.rect(19, 67, 23, 69, 'f_chaussure')
    # jupe longue
    p.poly([(13, 38 + s), (23, 38 + s), (24, 61), (12, 61)], 'f_jupe')
    # buste et bras arrière (côté ombre)
    p.rect(13, 18 + s, 23, 39 + s, 'f_pull')
    p.rect(13, 18 + s, 14, 39 + s, 'f_pull_o')
    # tête (sans visage) et cheveux : elle se perdra dans le tramage
    p.ovale(14, 5 + s, 23, 15 + s, 'f_peau')
    p.ovale(13, 3 + s, 22, 14 + s, 'f_cheveux')
    p.rect(13, 9 + s, 16, 19 + s, 'f_cheveux')           # cheveux mi-longs dans le dos
    p.rect(18, 15 + s, 21, 17 + s, 'f_peau')             # cou
    p.estomper(4 + s, 17 + s)                            # on ne sait plus qui c'était
    # --- Yoann ---
    y0 = 2 + s
    # cuisses posées sur l'avant-bras, jambes qui pendent, pieds vers la droite
    p.rect(24, 30 + y0, 32, 33 + y0, 'y_pantalon')
    p.rect(30, 34 + y0, 32, 39 + y0, 'y_pantalon')
    p.rect(30, 40 + y0, 34, 41 + y0, 'y_chaussure')
    # buste
    p.rect(23, 19 + y0, 30, 31 + y0, 'y_pull'); p.rect(23, 19 + y0, 24, 31 + y0, 'y_pull_o')
    # tête : grosse tête d'enfant
    tete_y = 9 + y0 + (2 if pose == 'baisse' else 0)
    p.ovale(23, tete_y, 32, tete_y + 10, 'y_peau')
    p.ovale(22, tete_y - 1, 31, tete_y + 5, 'y_cheveux')
    p.rect(22, tete_y + 2, 24, tete_y + 7, 'y_cheveux')
    p.px(23, tete_y + 8, 'y_cheveux_o')
    p.rect(26, tete_y + 4, 27, tete_y + 6, 'y_peau_o')   # oreille
    oeil = (30, tete_y + (6 if pose == 'baisse' else 5))
    p.px(*oeil, 'y_oeil')
    p.px(33, tete_y + 6, 'y_peau')                       # nez
    # bras et jouet
    def tenir(hx, hy):  # le jouet posé au-dessus des mains (hx, hy = mains)
        if jouet == 'avion': petit_avion(p, hx - 3, hy - 5)
        else: petit_robot(p, hx - 1, hy - 6)
    if pose == 'regarde':
        p.trait([(28, 22 + y0), (33, 19 + y0)], 'y_pull'); p.trait([(28, 23 + y0), (33, 20 + y0)], 'y_pull')
        tenir(35, 18 + y0); p.rect(33, 18 + y0, 35, 19 + y0, 'y_peau')
    elif pose == 'tend':
        p.rect(28, 21 + y0, 37, 23 + y0, 'y_pull')
        tenir(40, 21 + y0); p.rect(38, 21 + y0, 40, 22 + y0, 'y_peau')
    elif pose == 'serre':
        petit_avion(p, 24, 21 + y0) if jouet == 'avion' else petit_robot(p, 27, 20 + y0)
        p.rect(25, 26 + y0, 32, 27 + y0, 'y_pull'); p.rect(31, 25 + y0, 32, 26 + y0, 'y_peau')
    else:  # baisse : il montre le jouet à son frère, plus bas
        p.trait([(28, 25 + y0), (34, 28 + y0)], 'y_pull'); p.trait([(28, 26 + y0), (34, 29 + y0)], 'y_pull')
        tenir(36, 29 + y0); p.rect(34, 28 + y0, 36, 29 + y0, 'y_peau')
    # avant-bras de la femme sous Yoann, main sur sa jambe
    p.rect(20, 20 + s, 22, 33 + s, 'f_pull_o')
    p.rect(20, 32 + s, 29, 34 + s, 'f_pull')
    p.rect(29, 32 + s, 30, 34 + s, 'f_peau')
    p.lisere('droite', .5)
    return p.im


# ------------------------------------------------------------------ la mamie au chignon
MAMIE_W, MAMIE_H = 34, 66


def mamie(pose='sourit', souffle=0):
    """La mamie de profil vers la gauche (dessinée vers la droite puis retournée)."""
    p = Pinceau(MAMIE_W, MAMIE_H, miroir=True)
    s = -souffle
    p.rect(14, 58, 15, 62, 'm_bas'); p.rect(18, 58, 19, 62, 'm_bas')
    p.rect(14, 63, 17, 65, 'm_chaussure'); p.rect(18, 63, 21, 65, 'm_chaussure')
    p.poly([(11, 40 + s), (22, 40 + s), (24, 58), (10, 58)], 'm_jupe')
    p.rect(11, 21 + s, 22, 41 + s, 'm_gilet'); p.rect(11, 21 + s, 12, 41 + s, 'm_gilet_o')
    p.rect(20, 21 + s, 21, 30 + s, 'm_corsage')            # le corsage à fleurs, juste une bande
    # tête penchée en avant, accueillante
    p.ovale(13, 7 + s, 23, 19 + s, 'm_peau')
    p.ovale(11, 5 + s, 21, 14 + s, 'm_cheveux')
    p.rect(11, 9 + s, 14, 16 + s, 'm_cheveux')
    p.ovale(8, 4 + s, 12, 8 + s, 'm_cheveux_o')           # le chignon
    p.px(9, 5 + s, 'm_cheveux')
    p.rect(15, 18 + s, 18, 20 + s, 'm_peau_o')            # cou
    p.px(24, 13 + s, 'm_peau')                            # nez
    if pose == 'sourit':
        p.px(21, 11 + s, 'm_oeil')
        for x, y in [(19, 15), (20, 16), (21, 16), (22, 15)]: p.px(x, y + s, 'm_bouche')
        p.rect(18, 33 + s, 23, 35 + s, 'm_gilet_o'); p.rect(23, 33 + s, 25, 35 + s, 'm_peau')  # mains jointes
    else:  # rit : yeux fermés, bouche ouverte, une main sur la poitrine
        p.px(20, 11 + s, 'm_oeil'); p.px(21, 10 + s, 'm_oeil'); p.px(22, 11 + s, 'm_oeil')
        p.rect(20, 15 + s, 22, 16 + s, 'm_bouche'); p.px(21, 17 + s, 'm_bouche')
        p.rect(18, 27 + s, 22, 29 + s, 'm_gilet_o'); p.rect(21, 25 + s, 23, 27 + s, 'm_peau')
    p.lisere('gauche', .5)  # la lampe est à sa gauche à l'écran
    return p.im


# ------------------------------------------------------------------ le grand frère
FRERE_W, FRERE_H = 26, 46


def frere(pose='attend', souffle=0):
    """Le frère de trois quarts vers la droite. Yeux bleus, l'œil gauche (le plus loin) tourné vers l'intérieur."""
    p = Pinceau(FRERE_W, FRERE_H, miroir=True)  # tourné vers la gauche, vers Yoann et le jouet
    s = -souffle
    pointe = 2 if pose == 'tend' else 0  # sur la pointe des pieds : le corps monte
    h = s - pointe
    if pointe:
        p.rect(8, 41, 10, 43, 'b_pantalon'); p.rect(13, 41, 15, 43, 'b_pantalon')
        p.rect(9, 43, 12, 45, 'b_chaussure'); p.rect(14, 43, 17, 45, 'b_chaussure')
    else:
        p.rect(9, 43, 13, 45, 'b_chaussure'); p.rect(14, 43, 18, 45, 'b_chaussure')
    p.rect(8, 31 + h, 10, 42 if not pointe else 41, 'b_pantalon'); p.rect(13, 31 + h, 15, 42 if not pointe else 41, 'b_pantalon')
    p.rect(6, 19 + h, 17, 32 + h, 'b_tshirt'); p.rect(6, 19 + h, 7, 32 + h, 'b_tshirt_o')
    p.rect(4, 20 + h, 5, 29 + h, 'b_tshirt_o'); p.rect(4, 30 + h, 5, 31 + h, 'b_peau_o')          # bras du fond
    if pose == 'tend':
        for k in range(3): p.trait([(15 + k, 21 + h), (21 + k, 11 + h)], 'b_tshirt')            # bras tendu vers le jouet
        p.rect(22, 8 + h, 24, 10 + h, 'b_peau')
    else:
        p.rect(17, 20 + h, 18, 29 + h, 'b_tshirt'); p.rect(17, 30 + h, 18, 31 + h, 'b_peau')
    # tête, levée vers le jouet
    p.ovale(6, 5 + h, 17, 18 + h, 'b_peau')
    p.ovale(5, 3 + h, 16, 10 + h, 'b_cheveux')
    p.rect(5, 6 + h, 8, 13 + h, 'b_cheveux'); p.rect(5, 12 + h, 6, 14 + h, 'b_cheveux_o')
    p.rect(9, 9 + h, 10, 11 + h, 'b_peau_o')              # oreille
    # les yeux : œil proche regarde vers le haut à droite, œil lointain tourné vers le nez
    p.px(12, 11 + h, 'b_blanc'); p.px(13, 11 + h, 'b_oeil')
    p.px(15, 11 + h, 'b_oeil'); p.px(16, 11 + h, 'b_blanc')
    p.px(17, 13 + h, 'b_peau')                            # nez
    p.rect(14, 15 + h, 15, 15 + h, 'm_bouche')
    p.lisere('gauche', .45)
    return p.im


# ------------------------------------------------------------------ le jouet en gros plan (mini-jeu)
JOUET_W, JOUET_H = 64, 40


def mains(p, gauche, droite, haut):
    """Les deux petites mains de Yoann qui enserrent le jouet : paume en dessous, doigts par-dessus."""
    for x0 in (gauche, droite):
        p.ovale(x0, haut + 2, x0 + 10, haut + 12, 'y_peau')
        p.rect(x0 + 1, haut + 9, x0 + 9, haut + 12, 'y_peau_o')
        for k in range(4):  # quatre doigts posés sur le jouet
            p.rect(x0 + 1 + k * 2 + (k > 1), haut, x0 + 2 + k * 2 + (k > 1), haut + 2, 'y_peau')
            p.px(x0 + 2 + k * 2 + (k > 1), haut + 3, 'y_peau_o')


def jouet(etat='avion'):
    p = Pinceau(JOUET_W, JOUET_H)
    if etat == 'avion':
        p.poly([(9, 19), (5, 7), (11, 7), (18, 19)], 'j_gris')       # dérive
        p.ovale(7, 16, 53, 25, 'j_blanc')                            # fuselage
        p.rect(12, 25, 48, 25, 'j_gris')                             # ventre dans l'ombre
        p.poly([(51, 17), (59, 21), (51, 24)], 'j_blanc'); p.px(59, 21, 'j_gris')  # nez
        p.ovale(40, 14, 49, 18, 'j_vitre')                           # verrière
        p.rect(13, 21, 47, 21, 'j_rouge')                            # liseré rouge
        p.poly([(25, 22), (19, 31), (31, 31), (36, 22)], 'j_gris')   # aile
        mains(p, 12, 38, 23)
    elif etat == 'plie':  # les ailes se relèvent, le nez s'ouvre
        p.poly([(10, 18), (52, 15), (56, 19), (52, 24), (10, 25)], 'j_blanc')
        p.ovale(39, 12, 47, 16, 'j_vitre')
        p.rect(14, 21, 46, 21, 'j_rouge')
        p.poly([(18, 17), (12, 4), (19, 4), (26, 17)], 'j_gris')     # dérive qui se replie
        p.poly([(27, 16), (25, 2), (32, 2), (34, 16)], 'j_gris_f')   # aile relevée
        p.poly([(52, 16), (58, 11), (59, 14), (55, 19)], 'j_gris')   # le nez qui pivote
        mains(p, 12, 38, 23)
    else:  # robot
        p.poly([(22, 10), (16, 2), (22, 2), (27, 10)], 'j_gris')     # ailes repliées dans le dos
        p.poly([(41, 10), (47, 2), (41, 2), (36, 10)], 'j_gris')
        p.rect(26, 9, 37, 22, 'j_blanc')                             # torse
        p.ovale(28, 1, 35, 9, 'j_blanc'); p.rect(29, 4, 34, 6, 'j_vitre')  # tête et visière
        p.rect(31, 13, 32, 18, 'j_rouge')                            # liseré rouge
        p.rect(28, 11, 35, 13, 'j_vitre')                            # le cockpit devenu poitrine
        p.rect(21, 11, 24, 20, 'j_blanc'); p.rect(39, 11, 42, 20, 'j_blanc')  # bras
        p.rect(28, 23, 30, 30, 'j_blanc'); p.rect(33, 23, 35, 30, 'j_blanc')  # jambes
        p.rect(27, 31, 30, 32, 'j_gris'); p.rect(33, 31, 36, 32, 'j_gris')    # pieds
        mains(p, 14, 38, 20)
    return p.im


# ------------------------------------------------------------------ planches
def planche(nom, images):
    w, h = images[0][1].size
    feuille = Image.new('RGBA', (w * len(images), h), (0, 0, 0, 0))
    for i, (_, im) in enumerate(images): feuille.paste(im, (i * w, 0))
    feuille.save(DEST / f'{nom}.png', optimize=True)
    return {'w': w, 'h': h, 'poses': [n for n, _ in images]}


def main():
    DEST.mkdir(parents=True, exist_ok=True)
    info = {}
    info['femme'] = planche('femme', [(f'{po}_{j}_{s}', femme(po, s, j)) for j in ('avion', 'robot')
                                      for po in ('regarde', 'tend', 'serre', 'baisse') for s in (0, 1)])
    info['mamie'] = planche('mamie', [(f'{po}_{s}', mamie(po, s)) for po in ('sourit', 'rit') for s in (0, 1)])
    info['frere'] = planche('frere', [(f'{po}_{s}', frere(po, s)) for po in ('attend', 'tend') for s in (0, 1)])
    info['jouet'] = planche('jouet', [(e, jouet(e)) for e in ('avion', 'plie', 'robot')])
    (DEST / 'persos.json').write_text(json.dumps(info, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    print(json.dumps({k: (v['w'], v['h'], len(v['poses'])) for k, v in info.items()}))


if __name__ == '__main__':
    main()
