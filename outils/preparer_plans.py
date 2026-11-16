#!/usr/bin/env python3
"""Prépare les images d'un souvenir pour le jeu (direction artistique « fragments qui flottent »).

- décors opaques : convertis en WebP, légers pour le téléphone ;
- personnages et objets : fond magenta retiré (bords doux, sans liseré rose), recadrés au plus juste ;
- l'avion : ramené au blanc pur, la seule couleur pure du souvenir ;
- la grand-mère : le haut du visage tramé (« son visage n'est pas entièrement défini »), le sourire reste net ;
- l'avion est aussi découpé dans l'image des deux garçons, pour rester seul à l'écran à la fin.

  python outils/preparer_plans.py      # lit images/generees/s01, écrit jeu/assets/s01/ + plans.json
"""
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter

RACINE = Path(__file__).resolve().parent.parent
SRC = RACINE / 'images' / 'generees' / 's01'
DST = RACINE / 'jeu' / 'assets' / 's01'


def detourer(rgb):
    """Alpha doux à partir de la proximité au magenta, puis retrait de la teinte rose sur les bords."""
    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    proche = np.clip(((r + b) / 2 - g - 50) / 90, 0, 1) * (1 - np.clip(np.abs(r - b) / 110, 0, 1))
    alpha = 1 - proche
    alpha[alpha < .08] = 0
    spill = np.clip(np.minimum(r, b) - g, 0, None)  # rose/magenta : rouge ET bleu au-dessus du vert (aucune couleur du souvenir)
    out = rgb.copy()
    out[..., 0] = r - spill; out[..., 2] = b - spill
    # pixels francs : une petite érosion de l'alpha sur un pixel pour chasser le dernier liseré
    a_img = Image.fromarray((alpha * 255).astype(np.uint8)).filter(ImageFilter.MinFilter(3))
    alpha = np.minimum(alpha, np.asarray(a_img) / 255 + .35)
    alpha[alpha < .2] = 0
    # on ne garde que la zone principale : les grains isolés du fond sont effacés
    plein = Image.fromarray(((alpha > .5) * 255).astype(np.uint8)).filter(ImageFilter.MinFilter(5)).filter(ImageFilter.MaxFilter(25))
    alpha = alpha * (np.asarray(plein) > 0)
    return np.clip(out, 0, 255), np.clip(alpha, 0, 1)


def blanchir(rgb, alpha, zone=None, seuil=120, sat_max=255):
    """Ramène l'avion vers un blanc pur (les ombres restent grises, le liseré rouge reste rouge)."""
    out = rgb.copy()
    lum = rgb @ np.array([.299, .587, .114])
    sat = rgb.max(-1) - rgb.min(-1)
    rouge = (rgb[..., 0] > 120) & (rgb[..., 0] - rgb[..., 1] > 70)
    masque = (alpha > .5) & (lum > seuil) & ~rouge & (sat < sat_max)
    if zone is not None:
        z = np.zeros_like(masque); x0, y0, x1, y1 = zone; z[y0:y1, x0:x1] = True; masque &= z
    gris = np.clip(lum * 1.12 + 22, 0, 255)[..., None].repeat(3, -1)
    k = np.clip(1 - sat / 160, .35, 1)[..., None] * .85
    out[masque] = (rgb * (1 - k) + gris * k)[masque]
    return out, masque


def recadrer(rgb, alpha, marge=8):
    ys, xs = np.where(alpha > .02)
    x0, y0 = max(0, xs.min() - marge), max(0, ys.min() - marge)
    x1, y1 = min(alpha.shape[1], xs.max() + marge + 1), min(alpha.shape[0], ys.max() + marge + 1)
    return rgb[y0:y1, x0:x1], alpha[y0:y1, x0:x1], [int(x0), int(y0), int(x1), int(y1)]


def sauver(rgb, alpha, nom):
    if alpha is None:
        Image.fromarray(rgb.astype(np.uint8), 'RGB').save(DST / f'{nom}.webp', 'WEBP', quality=86, method=6)
    else:
        im = Image.fromarray(np.dstack([rgb, alpha * 255]).astype(np.uint8), 'RGBA')
        im.save(DST / f'{nom}.webp', 'WEBP', quality=88, alpha_quality=90, method=6)


def tramer_visage(rgb, alpha, zone, bloc=22):
    """Mosaïque fondue sur le haut du visage : on devine les yeux sans les voir."""
    x0, y0, x1, y1 = zone
    morceau = Image.fromarray(rgb[y0:y1, x0:x1].astype(np.uint8))
    w, h = morceau.size
    mosa = morceau.resize((max(1, w // bloc), max(1, h // bloc)), Image.BOX).resize((w, h), Image.NEAREST)
    m = np.asarray(mosa, dtype=np.float32)
    # fondu sur les bords de la zone, pour ne pas voir de rectangle
    yy, xx = np.mgrid[0:h, 0:w]
    fx = np.clip(np.minimum(xx, w - 1 - xx) / (w * .22), 0, 1)
    fy = np.clip(np.minimum(yy, h - 1 - yy) / (h * .30), 0, 1)
    k = (fx * fy * .9)[..., None]
    out = rgb.copy()
    out[y0:y1, x0:x1] = rgb[y0:y1, x0:x1] * (1 - k) + m * k
    return out


def main():
    DST.mkdir(parents=True, exist_ok=True)
    info = {}
    lire = lambda n: np.asarray(Image.open(SRC / f'{n}.png').convert('RGB'), dtype=np.float32)

    for n in ('fragment', 'entree_basse'):
        rgb = lire(n); sauver(rgb, None, n); info[n] = {'w': rgb.shape[1], 'h': rgb.shape[0]}

    # les deux garçons, et l'avion découpé à part
    rgb, a = detourer(lire('garcons'))
    ys, xs = np.where(a > .5)
    # l'avion : pixels clairs et peu colorés, dans le quart gauche des personnages, à hauteur des mains
    gx0, gx1, gy0, gy1 = xs.min(), xs.max(), ys.min(), ys.max()
    x0, y0 = int(gx0), int(gy0 + (gy1 - gy0) * .44)
    x1, y1 = int(gx0 + (gx1 - gx0) * .30), int(gy0 + (gy1 - gy0) * .64)
    # l'avion se distingue des mains par sa teinte : crème (vert et bleu hauts), la peau est plus orangée
    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    creme = (r > 165) & (g / np.maximum(r, 1) > .755) & (b / np.maximum(r, 1) > .46) & (a > .5)
    z = np.zeros_like(creme); z[y0:y1, x0:x1] = True; creme &= z
    ferme = Image.fromarray((creme * 255).astype(np.uint8)).filter(ImageFilter.MaxFilter(3)).filter(ImageFilter.MinFilter(3))
    m_avion = (np.asarray(ferme) > 0) & (a > .5)
    lum = rgb @ np.array([.299, .587, .114])
    blanc = np.clip(lum * 1.15 + 25, 0, 255)[..., None].repeat(3, -1)
    rgb = np.where(m_avion[..., None], rgb * .2 + blanc * .8, rgb)
    av_rgb, av_a, av_box = recadrer(rgb, a * m_avion, marge=2)
    # l'image des garçons sans l'avion (bouché à partir des pixels voisins) : l'avion est posé par-dessus et peut bouger
    import cv2
    trou = cv2.dilate((m_avion * 255).astype(np.uint8), np.ones((5, 5), np.uint8))
    rgb = cv2.inpaint(np.clip(rgb, 0, 255).astype(np.uint8), trou, 6, cv2.INPAINT_TELEA).astype(np.float32)
    g_rgb, g_a, g_box = recadrer(rgb, a)
    sauver(g_rgb, g_a, 'garcons'); sauver(av_rgb, av_a, 'avion_seul')
    info['garcons'] = {'w': g_rgb.shape[1], 'h': g_rgb.shape[0], 'box': g_box}
    info['avion_seul'] = {'w': av_rgb.shape[1], 'h': av_rgb.shape[0], 'box': av_box}

    # l'avion en gros plan, sous trois angles
    for n in ('avion_gauche', 'avion_profil', 'avion_droite'):
        rgb, a = detourer(lire(n)); rgb, _ = blanchir(rgb, a, seuil=90)
        rgb, a, box = recadrer(rgb, a, marge=16)
        sauver(rgb, a, n); info[n] = {'w': rgb.shape[1], 'h': rgb.shape[0], 'box': box}

    # la grand-mère : haut du visage tramé
    rgb, a = detourer(lire('grand_mere'))
    ys, xs = np.where(a > .5)
    x0, x1, y0, y1 = xs.min(), xs.max(), ys.min(), ys.max()
    hw = x1 - x0
    visage = (int(x0 + hw * .22), int(y0 + (y1 - y0) * .13), int(x0 + hw * .78), int(y0 + (y1 - y0) * .33))
    rgb = tramer_visage(rgb, a, visage)
    rgb, a, box = recadrer(rgb, a)
    sauver(rgb, a, 'grand_mere'); info['grand_mere'] = {'w': rgb.shape[1], 'h': rgb.shape[0], 'box': box, 'visage': visage}

    (DST / 'plans.json').write_text(json.dumps(info, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    print(json.dumps(info))


if __name__ == '__main__':
    main()
