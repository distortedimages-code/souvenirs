#!/usr/bin/env python3
"""Transforme les images générées en calques de décor prêts pour le jeu.

- le fond magenta des calques avant est retiré (transparence nette, sans liseré rose) ;
- chaque calque est ramené sur une vraie grille de pixels (1536 × 1024 → 384 × 256 par défaut) ;
- tous les calques d'un souvenir partagent la palette du fond, pour s'accorder entre eux et avec les personnages.

  python outils/preparer_decor.py s01            # lit images/generees/s01, écrit jeu/assets/s01
"""
import json, sys
from pathlib import Path

import numpy as np
from PIL import Image

RACINE = Path(__file__).resolve().parent.parent
FACTEUR = 4          # 1 pixel du jeu = 4 × 4 pixels de l'image générée
COULEURS = 64        # taille de la palette commune d'un souvenir


def masque_magenta(rgb):
    """1.0 = objet, 0.0 = fond magenta. Tolérant aux légères variations laissées par le modèle."""
    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    proche = (r - g > 60) & (b - g > 60) & (np.abs(r - b) < 90) & (b > 120)
    return (~proche).astype(np.float32)


def reduire(rgb, alpha, f):
    """Moyenne par blocs f × f, pondérée par l'alpha : le magenta ne déteint pas sur les bords."""
    h, w = alpha.shape
    h2, w2 = h // f, w // f
    rgb = rgb[:h2 * f, :w2 * f].reshape(h2, f, w2, f, 3)
    a = alpha[:h2 * f, :w2 * f].reshape(h2, f, w2, f)
    somme_a = a.sum(axis=(1, 3))
    couleur = (rgb * a[..., None]).sum(axis=(1, 3)) / np.maximum(somme_a, 1e-6)[..., None]
    return couleur, somme_a / (f * f)


def vers_palette(rgb, palette_img):
    im = Image.fromarray(np.clip(rgb, 0, 255).astype(np.uint8), 'RGB')
    return np.array(im.quantize(palette=palette_img, dither=Image.Dither.NONE).convert('RGB'))


def main():
    souvenir = sys.argv[1] if len(sys.argv) > 1 else 's01'
    src = RACINE / 'images' / 'generees' / souvenir
    dst = RACINE / 'jeu' / 'assets' / souvenir
    dst.mkdir(parents=True, exist_ok=True)
    plan = json.loads((RACINE / 'images' / 'plan.json').read_text(encoding='utf-8'))
    calques = [e for e in plan['images'] if e['image'].startswith(souvenir + '/')]

    # 1) tous les calques réduits sur la grille ; 2) une palette commune apprise sur tous leurs pixels visibles
    reduits = []
    for e in calques:
        nom = e['image'].split('/', 1)[1]
        f = src / (nom + '.png')
        if not f.is_file():
            print(f'absent : {f}'); continue
        rgb = np.asarray(Image.open(f).convert('RGB'), dtype=np.float32)
        alpha = masque_magenta(rgb) if e.get('magenta') else np.ones(rgb.shape[:2], np.float32)
        petit, a = reduire(rgb, alpha, FACTEUR)
        reduits.append((nom, petit, a))
    visibles = np.concatenate([p[a >= 0.5] for _, p, a in reduits])[:, None, :]
    palette = Image.fromarray(visibles.astype(np.uint8), 'RGB').quantize(COULEURS, method=Image.Quantize.MEDIANCUT, kmeans=3)
    infos = {}
    for nom, petit, a in reduits:
        petit = vers_palette(petit, palette)
        a = (a >= 0.5).astype(np.uint8) * 255
        sortie = np.dstack([petit.astype(np.uint8), a])
        Image.fromarray(sortie, 'RGBA').save(dst / (nom + '.png'), optimize=True)
        couverture = float((a > 0).mean())
        infos[nom] = {'taille': [int(sortie.shape[1]), int(sortie.shape[0])], 'opaque': round(couverture, 3)}
        print(f'{nom}: {sortie.shape[1]}×{sortie.shape[0]}, {couverture:.0%} opaque')
    (dst / 'calques.json').write_text(json.dumps(infos, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


if __name__ == '__main__':
    main()
