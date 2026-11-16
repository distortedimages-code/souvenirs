#!/usr/bin/env python3
"""Génère les décors du jeu « Souvenirs » avec l'API Images d'OpenAI.

Le script lit plan.json, génère les images qui manquent (ou dont le prompt a changé), et les range
dans generees/. En simulation, aucun appel à l'API : des images factices vont dans simulation/.

Exemples :
  python generer.py --simulation                 # gratuit, teste tout le circuit
  python generer.py --souvenir s01 --plafond 5   # les images du souvenir n°1, budget total 5 $
  python generer.py --refaire s01/fond           # régénère une image précise
"""
import argparse, base64, datetime, hashlib, io, json, os, random, sys
from pathlib import Path

from PIL import Image, ImageDraw

ICI = Path(__file__).resolve().parent

# Tarifs (dollars par million de jetons), repris du circuit de L'Express de Minuit (novembre 2026).
TARIFS = {'texte': 5.0, 'image_entree': 8.0, 'image_sortie': 30.0}
ESTIMATION = {'low': 0.03, 'medium': 0.09, 'high': 0.25, 'xhigh': 0.40}  # dollars par image, avant la première vraie facture
PAR_REFERENCE = 0.03

CONSIGNES = "Generate one single image: one frame. No collage, no split screen, no grid, no border, no caption."
REFERENCE = ("The attached image is a reference for palette, lighting, perspective, pixel size and scale only. "
             "Do not copy its content; draw only what is described above, so it can be layered on top of it.")
REFERENCE_PERSO = ("The first attached image is the background of the scene: use it only for palette, lighting, pixel size "
                   "and scale, and do not draw it. Any other attached image shows a character or object that must stay "
                   "exactly the same (face, hair, clothes, colours, proportions), as described above.")
MAGENTA = ("Everything that is not part of the described objects must be a perfectly flat, solid magenta (#FF00FF), "
           "with no gradient, no shadow and no texture, so it can be removed.")


def lire(p):
    return Path(p).read_text(encoding='utf-8').strip()


def ecrire_json(p, d):
    p = Path(p); p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix('.tmp'); tmp.write_text(json.dumps(d, ensure_ascii=False, indent=2) + '\n', encoding='utf-8'); tmp.replace(p)


def maintenant():
    return datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%d %H:%M UTC')


def construire_prompt(e):
    perso = e.get('type') == 'personnage'
    style = 'style_personnages.txt' if perso else 'style_commun.txt'
    negatif = 'prompt_negatif_personnages.txt' if perso else 'prompt_negatif.txt'
    morceaux = [lire(ICI / style), lire(ICI / e['prompt'])]
    if e.get('magenta'): morceaux.append(MAGENTA)
    morceaux.append('Avoid: ' + lire(ICI / negatif) + '.')
    morceaux.append(CONSIGNES)
    if e.get('references'): morceaux.append(REFERENCE_PERSO if perso else REFERENCE)
    return '\n\n'.join(morceaux)


def empreinte(texte, e):
    return hashlib.sha256((texte + '|' + e.get('taille', '') + '|' + ','.join(e.get('references', []))).encode()).hexdigest()[:16]


def ajuster(im, w, h):
    """Ramène l'image au format demandé sans la déformer : recadrage centré, puis mise à l'échelle."""
    if im.size == (w, h): return im
    sw, sh = im.size
    if sw / sh > w / h:
        nw = round(sh * w / h); x = (sw - nw) // 2; im = im.crop((x, 0, x + nw, sh))
    else:
        nh = round(sw * h / w); y = (sh - nh) // 2; im = im.crop((0, y, sw, y + nh))
    return im.resize((w, h), Image.LANCZOS)


class Generateur:
    def __init__(self, args):
        self.args = args; self.client = None
        if not args.simulation:
            if not os.environ.get('OPENAI_API_KEY'):
                sys.exit('La clé OPENAI_API_KEY est absente : ajoutez le secret dans le dépôt, ou lancez en simulation.')
            from openai import OpenAI
            self.client = OpenAI(timeout=600, max_retries=2)

    def cout(self, usage):
        if not usage: return 0.0
        d = getattr(usage, 'input_tokens_details', None)
        txt = getattr(d, 'text_tokens', None) if d else None
        img = getattr(d, 'image_tokens', None) if d else None
        if txt is None and img is None: txt, img = getattr(usage, 'input_tokens', 0) or 0, 0
        sortie = getattr(usage, 'output_tokens', 0) or 0
        return ((txt or 0) * TARIFS['texte'] + (img or 0) * TARIFS['image_entree'] + sortie * TARIFS['image_sortie']) / 1e6

    def produire(self, e, prompt, refs):
        if self.args.simulation:
            return self.simuler(e), ESTIMATION[self.args.qualite] + PAR_REFERENCE * len(refs)
        params = dict(model=self.args.modele, prompt=prompt, size=e['taille'], quality=self.args.qualite, output_format='png', n=1)
        fichiers = [open(r, 'rb') for r in refs]
        try:
            rep = self.client.images.edit(image=fichiers, **params) if fichiers else self.client.images.generate(**params)
        finally:
            for f in fichiers: f.close()
        im = Image.open(io.BytesIO(base64.b64decode(rep.data[0].b64_json))); im.load()
        return im, self.cout(getattr(rep, 'usage', None))

    def simuler(self, e):
        """Image factice (jamais un vrai décor) : sert à tester le circuit sans rien payer."""
        w, h = map(int, e['taille'].split('x'))
        rnd = random.Random(e['image'])
        im = Image.new('RGB', (w, h), (255, 0, 255) if e.get('magenta') else (40, 28, 24))
        d = ImageDraw.Draw(im)
        for _ in range(30):
            x, y = rnd.randrange(w), rnd.randrange(h); s = rnd.randrange(16, 160)
            d.rectangle([x, y, x + s, y + s // 2], fill=(rnd.randrange(80, 230), rnd.randrange(50, 160), rnd.randrange(30, 120)))
        d.text((20, 20), 'SIMULATION ' + e['image'], fill=(255, 255, 255))
        return im


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--souvenir', default='', help='ne traiter que les images qui commencent par ce préfixe (ex. s01)')
    ap.add_argument('--refaire', default='', help='régénérer ces images même si elles existent (séparées par des virgules)')
    ap.add_argument('--plafond', type=float, default=5.0, help='budget total en dollars, toutes séances confondues')
    ap.add_argument('--qualite', default='high', choices=sorted(ESTIMATION))
    ap.add_argument('--modele', default='gpt-image-2.5-sunburst')
    ap.add_argument('--simulation', action='store_true', help='aucun appel à l’API : images factices, coûts estimés')
    args = ap.parse_args()

    plan = json.loads((ICI / 'plan.json').read_text(encoding='utf-8'))
    images = plan['images']
    noms = [e['image'] for e in images]
    for e in images:
        e.setdefault('taille', plan.get('taille', '1536x1024'))
        for r in e.get('references', []):
            if r not in noms or noms.index(r) > noms.index(e['image']):
                sys.exit(f'Plan invalide : la référence {r} doit précéder {e["image"]}.')

    sortie = ICI / ('simulation' if args.simulation else 'generees')
    f_etat = ICI / ('etat-simulation.json' if args.simulation else 'etat.json')
    etat = json.loads(f_etat.read_text(encoding='utf-8')) if f_etat.exists() else {'total': 0.0, 'images': {}}
    resume = []
    def dire(l=''):
        print(l, flush=True); resume.append(l)

    refaire = [t.strip() for t in args.refaire.split(',') if t.strip()]
    selection = [e for e in images if e['image'].startswith(args.souvenir)] if args.souvenir else images
    a_faire = []
    for e in selection:
        prompt = construire_prompt(e); h = empreinte(prompt, e)
        connu = etat['images'].get(e['image'], {})
        present = (sortie / (e['image'] + '.png')).is_file()
        if e['image'] in refaire or not present or connu.get('empreinte') != h:
            a_faire.append((e, prompt, h))

    mode = 'SIMULATION gratuite' if args.simulation else f'RÉEL — {args.modele}, qualité {args.qualite}'
    dire(f'## Souvenirs — décors — {mode}')
    dire()
    prevu = sum(ESTIMATION[args.qualite] + PAR_REFERENCE * len(e.get('references', [])) for e, _, _ in a_faire)
    dire(f'À générer : **{len(a_faire)}** image(s), environ **{prevu:.2f} $**. Déjà dépensé : {etat["total"]:.2f} $ sur un plafond de {args.plafond:.2f} $.')
    if not a_faire:
        dire('Rien à générer : tout est à jour.')
    elif etat['total'] + prevu > args.plafond:
        dire(f'**Arrêt** : ce lot ferait dépasser le plafond. Relevez-le ou générez un seul souvenir.')
        a_faire = []

    gen = Generateur(args) if a_faire else None
    faites, echecs = [], []
    for e, prompt, h in a_faire:
        nom = e['image']
        refs = [sortie / (r + '.png') for r in e.get('references', [])]
        manque = [str(r) for r in refs if not r.is_file()]
        if manque:
            echecs.append(nom); dire(f'- `{nom}` — reportée : image de référence absente'); continue
        print(f'→ {nom}', flush=True)
        try:
            im, cout = gen.produire(e, prompt, refs)
        except Exception as ex:
            msg = str(ex).replace(os.environ.get('OPENAI_API_KEY') or '\0', '***')[:240]
            echecs.append(nom); dire(f'- `{nom}` — **échec** : {msg}'); continue
        w, h_ = map(int, e['taille'].split('x'))
        recue = f'{im.size[0]}x{im.size[1]}'
        im = ajuster(im.convert('RGB'), w, h_)
        dest = sortie / (nom + '.png'); dest.parent.mkdir(parents=True, exist_ok=True); im.save(dest, 'PNG', optimize=True)
        etat['total'] = round(etat['total'] + cout, 4)
        etat['images'][nom] = {'empreinte': h, 'cout': round(cout, 4), 'recue': recue, 'date': maintenant()}
        ecrire_json(f_etat, etat); faites.append(nom)
        dire(f'- `{nom}.png` — ok, {cout:.3f} $')

    dire()
    dire(f'Bilan : {len(faites)} image(s) générée(s), {len(echecs)} échec(s). Total dépensé : **{etat["total"]:.2f} $**'
         + (' (estimation de simulation)' if args.simulation else '') + '.')
    if os.environ.get('GITHUB_STEP_SUMMARY'):
        with open(os.environ['GITHUB_STEP_SUMMARY'], 'a', encoding='utf-8') as f: f.write('\n'.join(resume) + '\n')
    if echecs and not faites: sys.exit(1)


if __name__ == '__main__':
    main()
