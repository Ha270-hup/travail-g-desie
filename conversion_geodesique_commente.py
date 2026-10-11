# HANAE EL KHIATI 
"""
Conversion de coordonnées géodésiques + visualisation intelligente (schéma 3D et Terre)
  ①  (phi, lambda, h)  ->  (X, Y, Z)
  ②  (X, Y, Z)         ->  (phi, lambda, h)
Chaque point converti est placé sur la Terre (globe 3D, glisser pour tourner).
"""
#  je convertis des coordonnées géographiques (latitude φ, longitude λ, hauteur h)
# en coordonnées cartésiennes (X, Y, Z), et aussi dans l'autre sens.
# J'ai ajouté un dessin pour voir le résultat : un schéma 3D de l'ellipsoïde et la Terre.
#
# Une chose à retenir : dans les calculs je travaille en radians et en mètres, mais
# l'utilisateur voit et tape des degrés, parce que c'est plus facile à lire.
import math
import random
import re
import sys
import time
import unittest
import tkinter as tk
from tkinter import ttk

# calcul:
# La Terre n'est pas une sphère parfaite, elle est un peu aplatie aux pôles. Je la représente
# donc par un ellipsoïde, défini par deux longueurs en mètres :
#   a = le demi-grand axe (le rayon à l'équateur)
#   b = le demi-petit axe (le rayon aux pôles)
# Clarke 1880 est l'ellipsoïde du système Merchich, celui qu'on utilise au Maroc.
ELLIPSOIDES = {
    "Clarke 1880 (Merchich)": (6378249.145, 6356515.0),
    "GRS 80": (6378137.0, 6356752.314),
    "WGS 84": (6378137.0, 6356752.314245),
    "Hayford 1909": (6378388.0, 6356911.946),
}


# e² s'appelle l'excentricité au carré : plus elle est grande, plus l'ellipsoïde est aplati.
# Je l'utilise dans presque toutes les formules, donc je la calcule une fois ici.
def e2_of(a, b):
    return (a * a - b * b) / (a * a)


# N est le rayon de courbure du premier vertical. Pour moi, c'est la distance entre un point
# de l'ellipsoïde et l'axe des pôles, mesurée le long de la normale (la perpendiculaire à la
# surface). Sur une sphère ce serait juste le rayon, mais ici N dépend de la latitude.
def N_of(phi, a, e2):
    return a / math.sqrt(1 - e2 * math.sin(phi) ** 2)


# CONVERSION ① : je connais φ, λ et h et je veux X, Y, Z (un repère 3D dont l'origine est le
# centre de la Terre). Les angles arrivent déjà en radians.
def geo_to_cart(phi, lam, h, a, b):
    e2 = e2_of(a, b)
    # Je calcule d'abord N à la latitude du point, parce que X, Y et Z en dépendent.
    N = N_of(phi, a, e2)
    # Pour X et Y : je pars de (N + h), je le ramène dans le plan de l'équateur avec cos φ, puis
    # je le tourne autour de l'axe des pôles avec cos λ et sin λ.
    # Pour Z : sin φ donne la hauteur par rapport à l'équateur. Le facteur (1 - e²) vient de
    # l'aplatissement : sur un ellipsoïde la normale ne passe pas par le centre de la Terre.
    return ((N + h) * math.cos(phi) * math.cos(lam),
            (N + h) * math.cos(phi) * math.sin(lam),
            (N * (1 - e2) + h) * math.sin(phi))


# CONVERSION ② (méthode directe) : je connais X, Y, Z et je cherche φ, λ, h.
# Le problème, c'est que φ et h dépendent l'un de l'autre. Avec cette méthode je m'en sors
# grâce à une formule toute faite qui donne φ directement, sans boucle.
def cart_to_geo_directe(X, Y, Z, a, b):
    # J'ai besoin de e² et de l'aplatissement f = (a - b) / a.
    e2, f = e2_of(a, b), (a - b) / a
    # p = distance entre le point et l'axe des pôles (comme si je regardais la Terre de dessus).
    # r = distance entre le point et le centre de la Terre.
    p, r = math.hypot(X, Y), math.sqrt(X * X + Y * Y + Z * Z)
    # µ est un angle intermédiaire. C'est déjà une très bonne estimation de la latitude, je m'en
    # sers seulement pour calculer φ correctement à la ligne suivante.
    mu = math.atan((Z / p) * ((1 - f) + a * e2 / r))
    # Avec µ, j'obtiens la latitude géodésique φ en un seul calcul.
    phi = math.atan((Z * (1 - f) + e2 * a * math.sin(mu) ** 3)
                    / ((1 - f) * (p - e2 * a * math.cos(mu) ** 3)))
    # Maintenant que je connais φ, je peux trouver la hauteur h au-dessus de l'ellipsoïde.
    # La longitude, elle, est simple : atan2(Y, X). J'utilise atan2 plutôt que arctan(Y/X) parce
    # qu'il tient compte des signes de X et Y et donne tout de suite le bon quadrant.
    h = p * math.cos(phi) + Z * math.sin(phi) - a * math.sqrt(1 - e2 * math.sin(phi) ** 2)
    return phi, math.atan2(Y, X), h


# CONVERSION ② (méthode itérative) : je pars d'une valeur approchée de φ et je l'améliore
# à chaque tour de boucle, jusqu'à ce qu'elle ne bouge presque plus.
# Je la trouve plus facile à comprendre que la formule directe, car on voit φ se stabiliser.
def cart_to_geo_iterative(X, Y, Z, a, b, eps=1e-12):
    e2 = e2_of(a, b)
    p = math.hypot(X, Y)
    # Premier essai : je fais comme si le point était sur une sphère et j'oublie h.
    # Ce n'est pas exact, mais c'est un bon point de départ.
    phi = math.atan2(Z, p)
    # Avec ce premier φ, je calcule N et une première valeur de h (même fausse, ça me suffit
    # pour démarrer la boucle).
    N = N_of(phi, a, e2)
    h = p / math.cos(phi) - N
    # Je répète 50 fois au maximum, mais en vrai 4 ou 5 tours suffisent.
    for _ in range(50):
        # Je recalcule φ en utilisant le N et le h que je viens de trouver : c'est la correction.
        new = math.atan((Z / p) / (1 - e2 * N / (N + h)))
        # Je mets à jour N et h avec ce nouveau φ, pour le tour suivant.
        N = N_of(new, a, e2)
        h = p / math.cos(new) - N
        # Je regarde de combien φ a changé. Si c'est minuscule (moins de eps), je considère que la
        # valeur est stable et j'arrête la boucle.
        done = abs(new - phi) < eps * max(abs(new), 1e-12)
        phi = new
        if done:
            break
    return phi, math.atan2(Y, X), h


# Cette fonction lit un angle tapé par l'utilisateur. Il peut l'écrire en degrés décimaux
# (35.7595) ou en degrés-minutes-secondes (35 45 34.2 N). Elle renvoie toujours des degrés
# décimaux.
def parse_angle(txt):
    """Décimal (35.7595) ou DMS (35 45 34.2 N, 5°50'01"W)."""
    s = txt.strip().upper().replace(",", ".")
    # S (sud), W (ouest) ou O (ouest en français) veulent dire que l'angle est négatif.
    neg = bool(re.search(r"[SWO]", s))
    # Je récupère les nombres écrits dans le texte : un seul si c'est décimal, trois si c'est
    # degrés, minutes, secondes.
    nums = re.findall(r"[-+]?\d+(?:\.\d+)?", re.sub(r"[NSEWO]", " ", s))
    if not 1 <= len(nums) <= 3:
        raise ValueError(f"angle illisible : « {txt} »")
    neg = neg or nums[0].startswith("-")
    # Je passe en degrés décimaux : degrés + minutes/60 + secondes/3600.
    # (Le diviseur 60**i vaut 1, puis 60, puis 3600, selon la place du nombre.)
    v = sum(abs(float(n)) / 60 ** i for i, n in enumerate(nums))
    return -v if neg else v


# Le contraire : je transforme des degrés décimaux en degrés, minutes, secondes pour que
# l'affichage soit plus lisible.
def dms(x):
    sg, x = ("-" if x < 0 else ""), abs(x)
    d = int(x)
    m = int((x - d) * 60)
    return f"{sg}{d}° {m:02d}' {(x - d - m / 60) * 3600:06.3f}\""


#  continents (contours simplifiés lon, lat):
# Pour dessiner la Terre, j'ai noté à la main des contours très simplifiés des continents
# (des points longitude, latitude). Ce n'est pas précis du tout, c'est juste pour se repérer.
CONTINENTS = [
    # Afrique
    [(-17, 21), (-13, 28), (-9.5, 32), (-6, 35.8), (-2, 35), (3, 36.8), (10, 37.2), (11, 33), (15, 32),
     (20, 31), (25, 32), (32, 31.2), (34, 28), (37, 22), (39, 16), (43, 12), (51, 12), (48, 5), (41, -2),
     (39, -7), (40, -15), (35, -24), (32, -29), (27, -34), (20, -35), (18, -32), (14, -23), (12, -14),
     (13, -6), (9, -1), (9.5, 4), (5, 6), (-2, 5), (-8, 4.5), (-13, 8), (-17, 14.5)],
    # Eurasie
    [(-9, 37), (-9, 43), (-2, 43.5), (-1.5, 46), (-4.5, 48.5), (2, 51), (5, 53.5), (8, 55), (10, 57.5),
     (12, 56), (14, 54.5), (20, 54.5), (24, 57), (30, 60), (23, 60), (21, 64), (25, 65.5), (18, 69),
     (28, 71), (40, 67), (44, 68), (60, 69), (70, 73), (90, 76), (110, 77), (130, 72), (160, 70),
     (180, 69), (180, 65), (170, 60), (163, 58), (156, 51), (142, 59), (135, 54), (141, 48), (130, 42),
     (129, 35), (126, 35), (125, 40), (121, 40), (122, 37), (119, 35), (122, 31), (121, 28), (117, 23),
     (110, 21), (107, 17), (109, 12), (105, 9), (101, 13), (100, 7), (103, 2), (98, 8), (97, 17),
     (94, 17), (92, 22), (88, 22), (80, 15), (77, 8), (73, 17), (72, 21), (67, 24), (62, 25), (57, 26),
     (56.5, 27), (52, 28), (48, 30), (50, 27), (56, 25), (59, 22.5), (55, 17), (52, 16), (45, 13),
     (43, 13), (39, 21), (35, 28), (34.5, 31), (36, 36), (30, 36.5), (27, 37), (26, 40), (23, 40.5),
     (23, 37), (21, 38), (19.5, 41), (13.5, 45.5), (12.3, 44.5), (16, 41.5), (18.5, 40), (16, 38),
     (15.5, 40), (12, 42), (9, 44.3), (4, 43.4), (3, 42), (0, 39), (-1, 37.5), (-5, 36)],
    # Amérique du Nord
    [(-168, 66), (-165, 69), (-155, 71), (-140, 70), (-128, 70), (-115, 68), (-95, 72), (-85, 69),
     (-82, 63), (-93, 59), (-92, 57), (-85, 55), (-80, 51), (-78, 58), (-78, 62), (-70, 60), (-65, 60),
     (-62, 57), (-56, 52), (-60, 47), (-66, 45), (-70, 43), (-70, 41.5), (-74, 40), (-76, 37), (-76, 35),
     (-81, 31), (-80, 26), (-81, 25.5), (-83, 29), (-85, 30), (-90, 29), (-94, 29.5), (-97, 27),
     (-97.5, 22), (-95, 18.5), (-91, 19), (-90, 21), (-87, 21), (-88, 16), (-84, 15.5), (-83, 11),
     (-80, 9), (-77.5, 8.5), (-80, 7.5), (-82, 8), (-85, 10), (-87, 13), (-92, 14.5), (-96, 15.7),
     (-102, 18), (-105.5, 20), (-105.5, 23), (-109, 26), (-112.5, 29.5), (-114.5, 31), (-113, 28),
     (-110, 23), (-112, 25), (-115, 28), (-117, 32.5), (-120.5, 34.5), (-122.5, 37.5), (-124, 40.5),
     (-124, 46), (-124.5, 48), (-128, 51), (-133, 55), (-138, 59), (-145, 60.5), (-152, 59), (-158, 57),
     (-163, 55), (-158, 58.5), (-162, 60), (-165, 62), (-161, 64.5)],
    # Amérique du Sud
    [(-77, 8.5), (-72, 12), (-65, 10.5), (-60, 8.5), (-52, 5), (-50, 0), (-44, -2.5), (-35, -5.5),
     (-35, -9), (-39, -15), (-41, -22), (-48, -26), (-48.5, -28), (-53, -34), (-58, -34.5), (-57, -38),
     (-62, -39), (-65, -41), (-64, -45), (-67.5, -46.5), (-69, -51), (-68.5, -54), (-72, -53.5),
     (-75, -50), (-74, -44), (-73.5, -37), (-71.5, -30), (-70.5, -18), (-76, -14), (-81, -5), (-80, -1),
     (-78.5, 2), (-77.5, 7)],
    # Australie
    [(114, -22), (122, -18), (130, -12), (136, -12), (137, -16), (141, -12), (143, -14), (146, -19),
     (153, -26), (151, -34), (150, -37.5), (146, -39), (141, -38), (138, -35), (135, -34.5), (131, -31.5),
     (124, -33.5), (115, -34), (115, -30), (113, -26)],
    # Groenland
    [(-73, 78), (-60, 82), (-30, 83.5), (-20, 80), (-18, 75), (-22, 70), (-33, 66), (-42, 60), (-50, 63),
     (-54, 67), (-58, 75)],
]


# Cette fonction répond à : « ce point est-il dans ce contour ? ». L'astuce : je trace une
# droite horizontale depuis le point et je compte combien de fois elle coupe le contour.
# Nombre impair = dedans, nombre pair = dehors.
def _inside(lon, lat, poly):
    ins, j = False, len(poly) - 1
    for i in range(len(poly)):
        xi, yi = poly[i]
        xj, yj = poly[j]
        if (yi > lat) != (yj > lat) and lon < (xj - xi) * (lat - yi) / (yj - yi) + xi:
            ins = not ins
        j = i
    return ins


# Je quadrille toute la Terre avec des points régulièrement espacés et je garde seulement
# ceux qui tombent sur un continent. Ce sont eux que j'affiche sur le globe.
def build_land_dots(step=2.2):
    """Grille régulière de points terrestres (vecteurs unitaires)."""
    dots = []
    lat = -88.0
    while lat <= 88:
        # Près des pôles les méridiens se rapprochent, donc je mets moins de points sur les hautes
        # latitudes, sinon ils seraient tous collés.
        n = max(1, int(360 / step * math.cos(math.radians(lat))))
        for i in range(n):
            lon = -180 + 360 * (i + 0.5) / n
            # Un point est sur terre s'il est dans un continent, ou en Antarctique (au sud de 72°, que je
            # n'ai pas dessiné en détail).
            if lat < -72 or any(_inside(lon, lat, p) for p in CONTINENTS):
                la, lo = math.radians(lat), math.radians(lon)
                dots.append((math.cos(la) * math.cos(lo), math.cos(la) * math.sin(lo), math.sin(la)))
        lat += step
    return dots


# interface:
# Thèmes de couleurs. Pour changer l'apparence du programme, il suffit de modifier
# THEME juste en dessous, ou de lancer le programme avec le nom du thème :
#     python mon_fichier.py clair
# Thèmes disponibles : sombre, clair, foret, violet, chaud, ocean
# Chaque thème donne une couleur à tous les éléments : fond, cartes, champs, texte,
# couleur d'accent, globe, axes X Y Z, quadrillage, etc.
# ----------------------------------------------------------------------
THEMES = {
    "sombre": dict(BG="#0f172a", CARD="#1b2740", FIELD="#0b1220", LINE="#334155", FG="#e5e9f0",
                   MUTED="#94a3b8", ACC="#2dd4bf", ERR="#f87171", OK="#34d399",
                   PALETTE=["#fbbf24", "#f472b6", "#60a5fa", "#a78bfa", "#34d399", "#fb923c"],
                   SPACE="#070d1a", SEL="#1f3a66", STAR="#9fb3d9", ACC_TXT="#04201c", HINT="#5b6b8c",
                   GRID="#5aa2d8", GRID_BACK="#1f3a5e", AX_X="#f87171", AX_Y="#4ade80", AX_Z="#60a5fa",
                   GUIDE="#8ea0c0", DISK="#0c1c38", DISK_EDGE="#2b4a7a", HILITE="#fbbf24",
                   HCOL="#ec4899", HALO="#38bdf8", GREENWICH="#f59e0b", LBL="#bfe0ff",
                   LABEL_BG="#0b1426", LAND_LO="#16424a", LAND_HI="#7ff0dc"),
    "clair": dict(BG="#eef2f7", CARD="#ffffff", FIELD="#f1f5f9", LINE="#cbd5e1", FG="#0f172a",
                  MUTED="#64748b", ACC="#0d9488", ERR="#dc2626", OK="#059669",
                  PALETTE=["#d97706", "#db2777", "#2563eb", "#7c3aed", "#059669", "#ea580c"],
                  SPACE="#dde7f5", SEL="#cfe3fb", STAR="#7b93bd", ACC_TXT="#ffffff", HINT="#64748b",
                  GRID="#6f9bd1", GRID_BACK="#c5d3ea", AX_X="#dc2626", AX_Y="#16a34a", AX_Z="#2563eb",
                  GUIDE="#64748b", DISK="#cfe0f7", DISK_EDGE="#8fb0dc", HILITE="#d97706",
                  HCOL="#db2777", HALO="#7fb4ee", GREENWICH="#c2410c", LBL="#1e3a5f",
                  LABEL_BG="#ffffff", LAND_LO="#b6d9d3", LAND_HI="#0f766e"),
    "foret": dict(BG="#0c1a14", CARD="#14271e", FIELD="#0a1510", LINE="#2c4a3b", FG="#e6f2ea",
                  MUTED="#8fb09f", ACC="#4ade80", ERR="#f87171", OK="#86efac",
                  PALETTE=["#facc15", "#f472b6", "#38bdf8", "#c084fc", "#fb923c", "#2dd4bf"],
                  SPACE="#06100b", SEL="#22503a", STAR="#a7d4b8", ACC_TXT="#052e16", HINT="#5f8573",
                  GRID="#4fa57a", GRID_BACK="#1c3a2c", AX_X="#f87171", AX_Y="#a3e635", AX_Z="#38bdf8",
                  GUIDE="#8fb09f", DISK="#0f2a1f", DISK_EDGE="#2f6b4d", HILITE="#facc15",
                  HCOL="#f472b6", HALO="#34d399", GREENWICH="#fb923c", LBL="#cdeedb",
                  LABEL_BG="#0a1510", LAND_LO="#1a5a3a", LAND_HI="#a7f3c4"),
    "violet": dict(BG="#14101f", CARD="#211a35", FIELD="#0f0b19", LINE="#3d3260", FG="#ece8f7",
                   MUTED="#a79fc4", ACC="#c084fc", ERR="#fb7185", OK="#86efac",
                   PALETTE=["#fbbf24", "#f472b6", "#60a5fa", "#34d399", "#fb923c", "#2dd4bf"],
                   SPACE="#0b0814", SEL="#3b2d66", STAR="#c4b5fd", ACC_TXT="#2e1065", HINT="#7a6fa3",
                   GRID="#8b6fd0", GRID_BACK="#2e2450", AX_X="#fb7185", AX_Y="#4ade80", AX_Z="#60a5fa",
                   GUIDE="#a79fc4", DISK="#1b1433", DISK_EDGE="#5b46a3", HILITE="#fbbf24",
                   HCOL="#f472b6", HALO="#a78bfa", GREENWICH="#fb923c", LBL="#e0d7fb",
                   LABEL_BG="#0f0b19", LAND_LO="#3a2a6b", LAND_HI="#d8b4fe"),
    "chaud": dict(BG="#1c1410", CARD="#2a1e17", FIELD="#150f0b", LINE="#4d3a2c", FG="#f5ece4",
                  MUTED="#b8a595", ACC="#fb923c", ERR="#f87171", OK="#a3e635",
                  PALETTE=["#fde047", "#f472b6", "#60a5fa", "#a78bfa", "#34d399", "#2dd4bf"],
                  SPACE="#0f0a07", SEL="#5a3d27", STAR="#e8c9ab", ACC_TXT="#2b1300", HINT="#8c7561",
                  GRID="#c08a5c", GRID_BACK="#3a2a1f", AX_X="#f87171", AX_Y="#a3e635", AX_Z="#60a5fa",
                  GUIDE="#b8a595", DISK="#241a13", DISK_EDGE="#7a5632", HILITE="#fde047",
                  HCOL="#f472b6", HALO="#fdba74", GREENWICH="#38bdf8", LBL="#fde8d2",
                  LABEL_BG="#150f0b", LAND_LO="#5a3a22", LAND_HI="#fdba74"),
    "ocean": dict(BG="#071a2b", CARD="#0e2a43", FIELD="#061422", LINE="#1e4d6e", FG="#e6f4fb",
                  MUTED="#8ab4cc", ACC="#22d3ee", ERR="#f87171", OK="#4ade80",
                  PALETTE=["#fde047", "#fb7185", "#a78bfa", "#4ade80", "#fb923c", "#f0abfc"],
                  SPACE="#030d17", SEL="#1b4a6b", STAR="#a5d8f0", ACC_TXT="#022b33", HINT="#5f8ba6",
                  GRID="#3b9ac4", GRID_BACK="#17405a", AX_X="#fb7185", AX_Y="#4ade80", AX_Z="#facc15",
                  GUIDE="#8ab4cc", DISK="#0a2540", DISK_EDGE="#2a6f9e", HILITE="#fde047",
                  HCOL="#fb7185", HALO="#22d3ee", GREENWICH="#fb923c", LBL="#c8ecfa",
                  LABEL_BG="#061422", LAND_LO="#14532d", LAND_HI="#86efac"),
}
THEME = "ocean"                                   # <- thème utilisé par défaut
if len(sys.argv) > 1 and sys.argv[1] in THEMES:   # ou celui donné en argument
    THEME = sys.argv[1]
globals().update(THEMES[THEME])                   # BG, CARD, FG, ACC... deviennent des variables


# Mélange deux couleurs : avec t = 0 j'ai la première, avec t = 1 la seconde, et entre les
# deux un dégradé. Je m'en sers pour les halos et les effets de fondu.
def blend(c1, c2, t):
    a = [int(c1[i:i + 2], 16) for i in (1, 3, 5)]
    b = [int(c2[i:i + 2], 16) for i in (1, 3, 5)]
    return "#%02x%02x%02x" % tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


# Je prépare 12 nuances à l'avance : les points au centre du globe sont plus clairs, ceux
# des bords plus sombres, ça donne un petit effet de relief.
LAND_SHADES = [blend(LAND_LO, LAND_HI, i / 11) for i in range(12)]


# La classe App est la fenêtre du programme : à gauche je saisis et je calcule, à droite je
# vois le résultat dessiné.
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Conversion de coordonnées géodésiques")
        self.configure(bg=BG, padx=16, pady=14)
        self.var_ell = tk.StringVar(value="Clarke 1880 (Merchich)")
        self.var_a, self.var_b = tk.StringVar(), tk.StringVar()
        self.var_meth = tk.StringVar(value="Itérative")

        # état du globe
        # --- Tout ce qui sert au dessin ---
        self.land = build_land_dots()
        # À chaque conversion j'ajoute un point à cette liste (latitude, longitude en radians et une
        # couleur). Je garde aussi h et X, Y, Z à côté, pour les afficher sur le schéma.
        self.points = []            # (phi, lam, couleur)
        self.hs, self.xyz = [], []
        # Ces deux nombres disent comment je regarde le globe : spin = je le fais tourner autour de
        # l'axe des pôles, tilt = je l'incline vers moi ou vers l'arrière.
        self.spin, self.tilt = random.uniform(0, 6.28), 0.3
        # follow = la vue se tourne toute seule vers le point choisi.
        # dragging = je suis en train de tirer le globe avec la souris.
        self.follow, self.dragging = False, False
        self.focus = None
        self._last = (0, 0)
        self.cw = self.ch = 440
        self.born = 0.0

        # Je règle le style des listes déroulantes pour qu'elles aient les mêmes couleurs que le reste.
        st = ttk.Style(self)
        st.theme_use("clam")
        st.configure("TCombobox", fieldbackground=FIELD, background=CARD, foreground=FG,
                     arrowcolor=ACC, bordercolor=LINE, lightcolor=CARD, darkcolor=CARD)
        st.map("TCombobox", fieldbackground=[("readonly", FIELD)], foreground=[("readonly", FG)])
        self.option_add("*TCombobox*Listbox.background", FIELD)
        self.option_add("*TCombobox*Listbox.foreground", FG)

        # ellipsoïde
        # Barre du haut : c'est là que je choisis l'ellipsoïde et que je vois ses valeurs a et b.
        top = tk.Frame(self, bg=BG)
        top.pack(fill="x", pady=(0, 12))
        tk.Label(top, text="Ellipsoïde", bg=BG, fg=MUTED).pack(side="left")
        cb = ttk.Combobox(top, textvariable=self.var_ell, state="readonly", width=22,
                          values=list(ELLIPSOIDES) + ["Personnalisé"])
        cb.pack(side="left", padx=(8, 18))
        cb.bind("<<ComboboxSelected>>", lambda e: self.maj_ell())
        tk.Label(top, text="a", bg=BG, fg=MUTED).pack(side="left")
        self.e_a = self.entry(top, 13, self.var_a)
        self.e_a.pack(side="left", padx=(5, 12))
        tk.Label(top, text="b", bg=BG, fg=MUTED).pack(side="left")
        self.e_b = self.entry(top, 13, self.var_b)
        self.e_b.pack(side="left", padx=5)

        cols = tk.Frame(self, bg=BG)
        cols.pack()
        left = tk.Frame(cols, bg=BG)
        left.pack(side="left", anchor="n")
        right = tk.Frame(cols, bg=BG)
        right.pack(side="left", anchor="n", padx=(12, 0))

        # bloc 1
        # Bloc ① : je tape φ, λ, h et j'obtiens X, Y, Z.
        c1 = self.card(left, "①  (φ, λ, h)  →  (X, Y, Z)")
        c1.pack(side="left", padx=(0, 10), anchor="n")
        self.phi = self.field(c1, "φ  (°)", self.calc1)
        self.lam = self.field(c1, "λ  (°)", self.calc1)
        self.h = self.field(c1, "h  (m)", self.calc1)
        self.button(c1, "Calculer X, Y, Z", self.calc1)
        self.X = self.result(c1, "X  (m)")
        self.Y = self.result(c1, "Y  (m)")
        self.Z = self.result(c1, "Z  (m)")
        tk.Label(c1, text="Décimal ou DMS (35 45 34.2 N)", bg=CARD, fg=MUTED,
                 font=("Segoe UI", 8)).pack(anchor="w", pady=(6, 0))

        # bloc 2
        # Bloc ② : je tape X, Y, Z et j'obtiens φ, λ, h (avec la méthode choisie).
        c2 = self.card(left, "②  (X, Y, Z)  →  (φ, λ, h)")
        c2.pack(side="left", anchor="n")
        self.iX = self.field(c2, "X  (m)", self.calc2)
        self.iY = self.field(c2, "Y  (m)", self.calc2)
        self.iZ = self.field(c2, "Z  (m)", self.calc2)
        m = tk.Frame(c2, bg=CARD)
        m.pack(fill="x", pady=2)
        tk.Label(m, text="Méthode", bg=CARD, fg=MUTED, width=8, anchor="w").pack(side="left")
        ttk.Combobox(m, textvariable=self.var_meth, state="readonly", width=12,
                     values=["Directe", "Itérative"]).pack(side="left")
        self.button(c2, "Calculer φ, λ, h", self.calc2)
        self.oPhi = self.result(c2, "φ  (°)")
        self.oLam = self.result(c2, "λ  (°)")
        self.oH = self.result(c2, "h  (m)")
        self.dms_lbl = tk.Label(c2, text="", bg=CARD, fg=MUTED, font=("Consolas", 9),
                                justify="left", anchor="w")
        self.dms_lbl.pack(anchor="w", pady=(6, 0))

        # ---- globe
        # À droite : la partie dessin (schéma ou Terre) et la liste des points convertis.
        gf = tk.Frame(right, bg=CARD, highlightbackground=LINE, highlightthickness=1)
        gf.pack()
        self.mode = tk.StringVar(value="schema")
        mb = tk.Frame(gf, bg=CARD)
        mb.pack(fill="x", padx=8, pady=(6, 2))
        for txt, val in (("Schéma géodésique", "schema"), ("Terre", "terre")):
            tk.Radiobutton(mb, text=txt, variable=self.mode, value=val, indicatoron=0, bg=CARD,
                           fg=MUTED, selectcolor=SEL, activebackground=CARD, relief="flat",
                           bd=0, padx=10, pady=3, cursor="hand2").pack(side="left", padx=(0, 6))
        self.var_grid = tk.BooleanVar(value=True)
        self.var_pas = tk.StringVar(value="15°")
        tk.Checkbutton(mb, text="Lat / Long", variable=self.var_grid, bg=CARD, fg=FG,
                       selectcolor=FIELD, activebackground=CARD, activeforeground=ACC, bd=0,
                       highlightthickness=0).pack(side="left", padx=(10, 4))
        ttk.Combobox(mb, textvariable=self.var_pas, values=["10°", "15°", "30°"], width=4,
                     state="readonly").pack(side="left")
        # Le canvas est la zone où je dessine.
        self.canvas = tk.Canvas(gf, width=440, height=440, bg=SPACE, highlightthickness=0,
                                cursor="fleur")
        self.canvas.pack()
        self.canvas.bind("<ButtonPress-1>", self._press)
        self.canvas.bind("<B1-Motion>", self._drag)
        self.canvas.bind("<ButtonRelease-1>", lambda e: setattr(self, "dragging", False))
        # Je sème quelques étoiles au hasard dans le fond. C'est juste pour la déco.
        for x, y, s in [(random.random(), random.random(), random.random()) for _ in range(70)]:
            r = 0.6 + s
            self.canvas.create_oval(x * 440 - r, y * 440 - r, x * 440 + r, y * 440 + r,
                                    fill=blend(SPACE, STAR, 0.25 + 0.5 * s), width=0)
        bar = tk.Frame(gf, bg=CARD)
        bar.pack(fill="x", padx=8, pady=(6, 2))
        tk.Label(bar, text="Points convertis", bg=CARD, fg=ACC,
                 font=("Segoe UI", 10, "bold")).pack(side="left")
        tk.Button(bar, text="Effacer", command=self.effacer, bg=CARD, fg=MUTED, relief="flat",
                  bd=0, cursor="hand2", activebackground=CARD).pack(side="right")
        # La liste où s'écrivent les points déjà convertis.
        self.lb = tk.Listbox(gf, height=5, bg=FIELD, fg=FG, relief="flat", bd=0,
                             font=("Consolas", 9), selectbackground=SEL, selectforeground=FG,
                             highlightthickness=0, activestyle="none")
        self.lb.pack(fill="x", padx=8, pady=(0, 8))
        self.lb.bind("<<ListboxSelect>>", self._select)

        self.status = tk.Label(self, text="", bg=BG, fg=MUTED, anchor="w")
        self.status.pack(fill="x", pady=(10, 0))
        self.maj_ell()
        # Je lance l'animation.
        self.tick()

    # ------------------------------------------------------------ helpers graphiques
    # --- Petites fonctions pour ne pas répéter le même code à chaque fois que je crée un champ,
    # un bouton, etc. ---
    def entry(self, parent, width, var=None):
        return tk.Entry(parent, width=width, textvariable=var, bg=FIELD, fg=FG, relief="flat",
                        insertbackground=ACC, font=("Consolas", 11), highlightthickness=1,
                        highlightbackground=LINE, highlightcolor=ACC)

    def card(self, parent, titre):
        f = tk.Frame(parent, bg=CARD, padx=14, pady=12, highlightbackground=LINE,
                     highlightthickness=1)
        tk.Label(f, text=titre, bg=CARD, fg=ACC, font=("Segoe UI", 11, "bold")).pack(
            anchor="w", pady=(0, 8))
        return f

    def field(self, parent, label, cmd):
        r = tk.Frame(parent, bg=CARD)
        r.pack(fill="x", pady=2)
        tk.Label(r, text=label, bg=CARD, fg=MUTED, width=8, anchor="w").pack(side="left")
        e = self.entry(r, 20)
        e.pack(side="left", ipady=3)
        e.bind("<Return>", lambda ev: cmd())
        return e

    def result(self, parent, label):
        r = tk.Frame(parent, bg=CARD)
        r.pack(fill="x", pady=2)
        tk.Label(r, text=label, bg=CARD, fg=MUTED, width=8, anchor="w").pack(side="left")
        e = tk.Entry(r, width=20, state="readonly", readonlybackground=FIELD, fg=ACC,
                     relief="flat", font=("Consolas", 11, "bold"), highlightthickness=1,
                     highlightbackground=LINE)
        e.pack(side="left", ipady=3)
        return e

    def button(self, parent, text, cmd):
        tk.Button(parent, text=text, command=cmd, bg=ACC, fg=ACC_TXT, relief="flat",
                  font=("Segoe UI", 10, "bold"), cursor="hand2", pady=6,
                  activebackground=blend(ACC, "#ffffff", 0.3)).pack(fill="x", pady=(10, 8))

    @staticmethod
    def put(e, txt):
        e.config(state="normal")
        e.delete(0, "end")
        e.insert(0, txt)
        e.config(state="readonly")

    def say(self, msg, ok=True):
        self.status.config(text=("✔ " if ok else "✖ ") + msg, fg=OK if ok else ERR)

    # ------------------------------------------------------------ logique
    # Quand je change d'ellipsoïde dans la liste, j'affiche ses valeurs a et b. Je ne peux les
    # modifier à la main que si je choisis « Personnalisé ».
    def maj_ell(self):
        nom = self.var_ell.get()
        if nom in ELLIPSOIDES:
            a, b = ELLIPSOIDES[nom]
            self.var_a.set(repr(a))
            self.var_b.set(repr(b))
            for e in (self.e_a, self.e_b):
                e.config(state="readonly", readonlybackground=FIELD, fg=MUTED)
        else:
            for e in (self.e_a, self.e_b):
                e.config(state="normal", fg=FG)

    # Je lis a et b et je vérifie qu'ils ont un sens (a plus grand que b, et les deux positifs).
    def ab(self):
        try:
            a = float(self.var_a.get().replace(",", "."))
            b = float(self.var_b.get().replace(",", "."))
        except ValueError:
            raise ValueError("a et b doivent être numériques")
        if not a > b > 0:
            raise ValueError("il faut a > b > 0")
        return a, b

    @staticmethod
    def num(e):
        try:
            return float(e.get().replace(",", ".").strip())
        except ValueError:
            raise ValueError("valeur numérique invalide")

    # Bouton du bloc ① : je lis φ, λ, h, je calcule X, Y, Z, je les affiche et j'ajoute le point
    # sur le dessin.
    def calc1(self):
        try:
            a, b = self.ab()
            phi, lam = parse_angle(self.phi.get()), parse_angle(self.lam.get())
            h = self.num(self.h)
            if abs(phi) > 90 or abs(lam) > 180:
                raise ValueError("φ ∈ [-90°, 90°] et λ ∈ [-180°, 180°]")
            # L'utilisateur tape des degrés mais mes formules veulent des radians : je convertis.
            X, Y, Z = geo_to_cart(math.radians(phi), math.radians(lam), h, a, b)
        except ValueError as err:
            return self.say(f"① {err}", False)
        for e, v in zip((self.X, self.Y, self.Z), (X, Y, Z)):
            self.put(e, f"{v:.4f}")
        self.ajouter_point(math.radians(phi), math.radians(lam), "①", h, (X, Y, Z))
        self.say("Conversion ① effectuée.")

    # Bouton du bloc ② : je lis X, Y, Z, je calcule φ, λ, h avec la méthode choisie, je les
    # affiche et j'ajoute le point.
    def calc2(self):
        try:
            a, b = self.ab()
            X, Y, Z = self.num(self.iX), self.num(self.iY), self.num(self.iZ)
            # Si X et Y valent 0, le point est pile sur l'axe des pôles et la longitude n'a plus de sens.
            # Je refuse ce cas avec un message.
            if math.hypot(X, Y) < 1e-6:
                raise ValueError("cas des pôles (X = Y = 0) non traité")
            # Je choisis la fonction selon la méthode sélectionnée : directe ou itérative.
            f = cart_to_geo_directe if self.var_meth.get() == "Directe" else cart_to_geo_iterative
            phi, lam, h = f(X, Y, Z, a, b)
        except ValueError as err:
            return self.say(f"② {err}", False)
        p, l = math.degrees(phi), math.degrees(lam)
        self.put(self.oPhi, f"{p:.9f}")
        self.put(self.oLam, f"{l:.9f}")
        self.put(self.oH, f"{h:.4f}")
        self.dms_lbl.config(text=f"φ = {dms(p)}\nλ = {dms(l)}")
        self.ajouter_point(phi, lam, "②", h, (X, Y, Z))
        self.say("Conversion ② effectuée.")

    # ------------------------------------------------------------ points sur la Terre
    # J'enregistre le point converti : je lui donne une couleur, je l'ajoute à la liste sous le
    # dessin, et je tourne la vue vers lui.
    def ajouter_point(self, phi, lam, op, h=0.0, xyz=(0.0, 0.0, 0.0)):
        col = PALETTE[len(self.points) % len(PALETTE)]
        self.points.append((phi, lam, col))
        self.hs.append(h)
        self.xyz.append(xyz)
        n = len(self.points)
        self.lb.insert("end", f"{n:>2} {op}  φ={math.degrees(phi):9.4f}°  λ={math.degrees(lam):10.4f}°")
        self.lb.itemconfig("end", fg=col)
        self.lb.see("end")
        self.focus, self.follow, self.born = n - 1, True, time.time()

    # Je vide la liste et j'enlève les points du dessin.
    def effacer(self):
        self.points.clear()
        self.hs.clear()
        self.xyz.clear()
        self.lb.delete(0, "end")
        self.focus, self.follow = None, False

    # Quand je clique sur une ligne de la liste, la vue se tourne vers ce point.
    def _select(self, ev):
        s = self.lb.curselection()
        if s:
            self.focus, self.follow, self.born = s[0], True, time.time()

    # Je viens d'appuyer sur la souris : j'arrête le suivi automatique pour pouvoir tourner le
    # globe moi-même.
    def _press(self, ev):
        self.dragging, self._last, self.follow = True, (ev.x, ev.y), False

    # Quand je bouge la souris en gardant le bouton appuyé, le globe tourne : de gauche à droite
    # autour de l'axe des pôles, de haut en bas il s'incline.
    def _drag(self, ev):
        dx, dy = ev.x - self._last[0], ev.y - self._last[1]
        self._last = (ev.x, ev.y)
        self.spin += dx * 0.01
        self.tilt = max(-1.4, min(1.4, self.tilt + dy * 0.01))

    # ------------------------------------------------------------ dessin du globe
    # Je calcule une seule fois par image les cosinus et sinus de la rotation, pour ne pas les
    # refaire à chaque point.
    def _rot(self):
        return (math.cos(self.spin), math.sin(self.spin), math.cos(self.tilt), math.sin(self.tilt))

    @staticmethod
    # Cette fonction transforme un point 3D en position sur l'écran (2D). Je fais d'abord tourner
    # le point autour de l'axe Z, puis je l'incline, puis je garde x et z comme position à l'écran.
    # La 3e valeur (la profondeur) me dit si le point est devant le globe (y2 < 0) ou derrière.
    def _proj(x, y, z, r, k, cx, cy):
        cs, sn, ct, st = r
        xp, yp = x * cs - y * sn, x * sn + y * cs
        return cx + k * xp, cy - k * (yp * st + z * ct), yp * ct - z * st

    # Je trace une ligne en gardant seulement la partie visible, celle qui est sur la face du
    # globe tournée vers nous.
    def _lines(self, c, pts_list, front_col, back_col, wf=1):
        for pts in pts_list:
            cur, vis = [], None
            for x, y, d in pts:
                v = d < 0
                if vis is None:
                    cur, vis = [(x, y)], v
                elif v == vis:
                    cur.append((x, y))
                else:
                    cur.append((x, y))
                    if vis:
                        c.create_line(*[q for p in cur for q in p], fill=front_col, width=wf, tags="fx")
                    cur, vis = [(x, y)], v
            if len(cur) > 1 and vis:
                c.create_line(*[q for p in cur for q in p], fill=front_col, width=wf, tags="fx")

    # Je redessine la vue choisie : schéma géodésique ou Terre.
    def draw(self):
        (self.draw_schema if self.mode.get() == "schema" else self.draw_terre)()

    # Le schéma pour comprendre : pour un point P, il montre l'ellipsoïde, les axes X Y Z, la
    # normale, les angles φ et λ, la hauteur h et les projections de P sur les axes.
    def draw_schema(self):
        """Schéma pédagogique : P, normale, h, φ, λ, axes X Y Z et projections."""
        c = self.canvas
        c.delete("fx")
        cx, cy, k = 220, 218, 150
        if not self.points:
            c.create_text(cx, cy, fill=HINT, font=("Segoe UI", 11), tags="fx", justify="center",
                          text="Faites une conversion ① ou ②\npour voir le point sur l'ellipsoïde")
            return
        i = self.focus if self.focus is not None else len(self.points) - 1
        phi, lam, col = self.points[i]
        hh, (X, Y, Z) = self.hs[i], self.xyz[i]
        try:
            a, b = self.ab()
        except ValueError:
            return
        f = (a - b) / a
        # Pour le dessin je prends un ellipsoïde de rayon 1 et j'exagère son aplatissement ×40, sinon
        # on ne verrait pas qu'il est aplati (il ne l'est que de 0,3 %).
        # Attention : seul le dessin est exagéré, les nombres affichés sont exacts.
        bd = max(0.4, 1 - 40 * f)                       # aplatissement exagéré x40
        e2d = 1 - bd * bd
        # Le même N que plus haut, mais pour l'ellipsoïde dessiné.
        Nd = 1 / math.sqrt(1 - e2d * math.sin(phi) ** 2)
        # La normale en P : la direction perpendiculaire à la surface, écrite avec φ et λ.
        n = (math.cos(phi) * math.cos(lam), math.cos(phi) * math.sin(lam), math.sin(phi))
        # P0 = le point sur la surface de l'ellipsoïde (c'est la conversion ① avec h = 0).
        P0 = tuple(Nd * n[j] * ((1 - e2d) if j == 2 else 1) for j in range(3))
        # P = P0 décalé le long de la normale de la hauteur h. Sur le dessin je prends toujours la
        # même petite longueur, sinon h serait invisible.
        P = tuple(P0[j] + 0.16 * n[j] for j in range(3))
        r = self._rot()
        pr = lambda v: self._proj(v[0], v[1], v[2], r, k, cx, cy)
        WIRE, BACK, CX, CY, CZ = GRID, GRID_BACK, AX_X, AX_Y, AX_Z
        GREY = GUIDE

        # Petite aide : trace une ligne brisée, en distinguant la partie devant et la partie derrière.
        def seg(pts, fc, bc, wf=1.0, only=None):
            prev = None
            for q in pts:
                if prev:
                    A, B = pr(prev), pr(q)
                    fr = (A[2] + B[2]) / 2 < 0
                    if only is None or only == fr:
                        c.create_line(A[0], A[1], B[0], B[1], fill=fc if fr else bc,
                                      width=wf if fr else 1, tags="fx")
                prev = q

        # Petite aide : trace un segment entre deux points 3D.
        def ln(p1, p2, colr, wd=1.0, dash=None):
            A, B = pr(p1), pr(p2)
            c.create_line(A[0], A[1], B[0], B[1], fill=colr, width=wd, dash=dash, tags="fx")

        # Petite aide : écrit un texte à côté d'un point 3D.
        def tx(t, v, colr, dx=6, dy=-6, size=10):
            A = pr(v)
            c.create_text(A[0] + dx, A[1] + dy, text=t, fill=colr, anchor="w",
                          font=("Segoe UI", size, "bold"), tags="fx")

        # mer(L) = un méridien (ligne de longitude), fait de plein de petits points.
        mer = lambda L: [(math.cos(math.radians(t)) * math.cos(L), math.cos(math.radians(t)) * math.sin(L),
                          bd * math.sin(math.radians(t))) for t in range(-90, 91, 4)]
        # par(t) = un parallèle (ligne de latitude).
        par = lambda t: [(math.cos(math.radians(t)) * math.cos(math.radians(L)),
                          math.cos(math.radians(t)) * math.sin(math.radians(L)),
                          bd * math.sin(math.radians(t))) for L in range(0, 361, 5)]
        c.create_oval(cx - k, cy - k * math.sqrt((bd * math.cos(self.tilt)) ** 2 + math.sin(self.tilt) ** 2),
                      cx + k, cy + k * math.sqrt((bd * math.cos(self.tilt)) ** 2 + math.sin(self.tilt) ** 2),
                      fill=DISK, outline=DISK_EDGE, tags="fx")
        # Le pas du quadrillage choisi par l'utilisateur : 10°, 15° ou 30°.
        st = int(self.var_pas.get().rstrip("°"))
        grid = ([mer(math.radians(L)) for L in range(0, 360, st)]
                + [par(t) for t in range(-90 + st, 90, st)]) if self.var_grid.get() else []
        for g in grid:
            seg(g, WIRE, BACK, only=False)
        # Les trois axes X, Y, Z, chacun avec sa couleur.
        for ax, ay, az, t, cc in ((1.38, 0, 0, "X", CX), (0, 1.38, 0, "Y", CY), (0, 0, 1.3, "Z", CZ)):
            ln((0, 0, 0), (ax, ay, az), cc, 1.6)
            tx(t, (ax * 1.05, ay * 1.05, az * 1.05), cc, 3, 3, 12)
        for g in grid:
            seg(g, WIRE, BACK, only=True)
        # L'équateur.
        seg(par(0), ACC, ACC, 2, only=True)
        seg(mer(lam), HILITE, HILITE, 2.2)                         # méridien de P
        seg([(math.cos(t * lam / 90), math.sin(t * lam / 90), 0) for t in range(91)], ACC, ACC, 3)  # arc λ
        tx("λ", (.55 * math.cos(lam / 2), .55 * math.sin(lam / 2), 0), ACC, 0, -6, 12)
        # normale, φ, h
        # Point intéressant : la normale ne passe pas par le centre de la Terre ! Elle coupe l'axe des
        # pôles un peu plus bas, à z = -N·e²·sin φ. C'est de ce point que je dessine l'angle φ.
        ez = -Nd * e2d * math.sin(phi)
        A0, u = (0, 0, ez), (math.cos(lam), math.sin(lam), 0)
        ln(A0, P, HILITE, 2)
        ln(P0, P, HCOL, 4)
        seg([(A0[0] + .22 * math.cos(phi * j / 24) * u[0], A0[1] + .22 * math.cos(phi * j / 24) * u[1],
              ez + .22 * math.sin(phi * j / 24)) for j in range(25)], HILITE, HILITE, 2.5)
        ln(A0, (A0[0] + .3 * u[0], A0[1] + .3 * u[1], ez), GREY, 1, (3, 3))
        tx("φ", (A0[0] + .28 * math.cos(phi / 2) * u[0], A0[1] + .28 * math.cos(phi / 2) * u[1],
                 ez + .28 * math.sin(phi / 2)), HILITE, 2, 4, 12)
        ln((0, 0, 0), P0, GREY, 1.3, (5, 4))
        tx("ψ", tuple(.35 * v for v in P0), GREY, 4, -4, 11)
        # projections de P sur les axes
        # Les pointillés montrent comment on lit X, Y et Z : on descend de P jusqu'au plan de
        # l'équateur, puis on rejoint chaque axe.
        pe = (P0[0], P0[1], 0)
        ln(P0, pe, GREY, 1, (2, 3))
        ln(pe, (P0[0], 0, 0), GREY, 1, (2, 3))
        ln(pe, (0, P0[1], 0), GREY, 1, (2, 3))
        ln(P0, (0, 0, P0[2]), GREY, 1, (2, 3))
        tx(f"X={X:,.0f}".replace(",", " "), (P0[0], 0, 0), CX, -30, 14, 9)
        tx(f"Y={Y:,.0f}".replace(",", " "), (0, P0[1], 0), CY, 6, 14, 9)
        tx(f"Z={Z:,.0f}".replace(",", " "), (0, 0, P0[2]), CZ, -80, -4, 9)
        # point P
        px, py, _ = pr(P)
        # Petit effet visuel : le marqueur de P grossit et rétrécit en continu.
        pulse = 0.5 + 0.5 * math.sin((time.time() - self.born) * 5)
        c.create_oval(px - 7 - 5 * pulse, py - 7 - 5 * pulse, px + 7 + 5 * pulse, py + 7 + 5 * pulse,
                      outline=blend(DISK, col, 0.7 * (1 - pulse)), width=2, tags="fx")
        c.create_oval(px - 5, py - 5, px + 5, py + 5, fill=col, outline="white", tags="fx")
        tx(f"P{i + 1}", P, col, 9, -9, 11)
        tx("h", tuple((P0[j] + P[j]) / 2 for j in range(3)), HCOL, 8, 10, 10)
        c.create_text(10, 424, anchor="sw", fill=HINT, font=("Segoe UI", 8), tags="fx",
                      text=f"P{i + 1} :  φ {math.degrees(phi):.4f}°  λ {math.degrees(lam):.4f}°  h {hh:.2f} m"
                           "  ·  ×40")

    # La vue Terre : les continents (en points), les lignes de latitude et de longitude, et les
    # points convertis.
    def draw_terre(self):
        c = self.canvas
        c.delete("fx")
        w = h = 440
        cx, cy, k = w / 2, h / 2 - 2, 178
        r = self._rot()
        # halo + disque
        for g, t in ((16, 0.05), (10, 0.09), (5, 0.15)):
            c.create_oval(cx - k - g, cy - k - g, cx + k + g, cy + k + g,
                          fill=blend(SPACE, HALO, t), width=0, tags="fx")
        c.create_oval(cx - k, cy - k, cx + k, cy + k, fill=DISK, outline=DISK_EDGE, tags="fx")

        # continents (points)
        cs, sn, ct, st = r
        # Je parcours tous les points de terre. Chacun est une direction (un vecteur de longueur 1).
        # J'applique la même rotation que dans _proj, mais directement ici pour aller plus vite.
        # Si le point est devant (y2 < 0) je le dessine : plus il est au centre, plus il est clair.
        for x, y, z in self.land:
            yp = x * sn + y * cs
            y2 = yp * ct - z * st
            if y2 < 0:
                xp = x * cs - y * sn
                z2 = yp * st + z * ct
                px, py = cx + k * xp, cy - k * z2
                c.create_rectangle(px - 1.0, py - 1.0, px + 1.0, py + 1.0,
                                   fill=LAND_SHADES[min(11, int(-y2 * 12))], width=0, tags="fx")

        # lignes de latitude et de longitude (étiquetées)
        P = lambda x, y, z: self._proj(x, y, z, r, k, cx, cy)
        sph = lambda bb, L: P(math.cos(math.radians(bb)) * math.cos(math.radians(L)),
                              math.cos(math.radians(bb)) * math.sin(math.radians(L)),
                              math.sin(math.radians(bb)))
        if self.var_grid.get():
            st_ = int(self.var_pas.get().rstrip("°"))
            lons = list(range(-180, 180, st_))
            lats = [bb for bb in range(-90 + st_, 90, st_) if bb != 0]
            GR = GRID
            self._lines(c, [[sph(bb, L) for bb in range(-90, 91, 3)] for L in lons if L != 0], GR, None)
            self._lines(c, [[sph(bb, L) for L in range(-180, 181, 3)] for bb in lats], GR, None)
            self._lines(c, [[sph(bb, 0) for bb in range(-90, 91, 3)]], GREENWICH, None, 2)   # Greenwich
            self._lines(c, [[sph(0, L) for L in range(-180, 181, 3)]], ACC, None, 2)          # équateur
            fnt = ("Consolas", 8, "bold")
            for L in lons:
                x, y, d = sph(0, L)
                if d < -0.2:
                    t = f"{abs(L)}°{'E' if L > 0 else 'W' if L < 0 else ''}"
                    c.create_text(x, y + 9, text=t, fill=GREENWICH if L == 0 else LBL,
                                  font=fnt, tags="fx")
            lc = math.degrees(-math.pi / 2 - self.spin)          # longitude face à l'observateur
            for bb in lats + [0]:
                x, y, d = sph(bb, lc)
                if d < -0.2:
                    t = "0° (équateur)" if bb == 0 else f"{abs(bb)}°{'N' if bb > 0 else 'S'}"
                    c.create_text(x + 5, y - 7, text=t, fill=ACC if bb == 0 else LBL,
                                  font=fnt, anchor="w", tags="fx")
            if self.focus is not None and self.points:       # méridien et parallèle du point choisi
                fp, fl, fc = self.points[self.focus]
                self._lines(c, [[sph(bb, math.degrees(fl)) for bb in range(-90, 91, 3)]], fc, None, 2)
                self._lines(c, [[sph(math.degrees(fp), L) for L in range(-180, 181, 3)]], fc, None, 2)

        # points convertis
        # Même effet de pulsation que sur le schéma, pour le point sélectionné.
        pulse = 0.5 + 0.5 * math.sin((time.time() - self.born) * 5)
        for i, (phi, lam, col) in enumerate(self.points):
            n = (math.cos(phi) * math.cos(lam), math.cos(phi) * math.sin(lam), math.sin(phi))
            px, py, d = self._proj(*n, r, k, cx, cy)
            last = i == len(self.points) - 1 or i == self.focus
            if d < 0:
                if last:
                    rr = 7 + 6 * pulse
                    c.create_oval(px - rr, py - rr, px + rr, py + rr,
                                  outline=blend(DISK, col, 0.7 * (1 - pulse)), width=2, tags="fx")
                c.create_oval(px - 5, py - 5, px + 5, py + 5, fill=col, outline="white", tags="fx")
                c.create_text(px, py - 14, text=str(i + 1), fill=col,
                              font=("Segoe UI", 9, "bold"), tags="fx")
                if i == self.focus:
                    txt = f"{i + 1}   φ {math.degrees(phi):.4f}°   λ {math.degrees(lam):.4f}°"
                    tx = min(max(px + 12, 6), w - 250)
                    ty = min(max(py + 20, 18), h - 20)
                    c.create_rectangle(tx - 5, ty - 10, tx + 240, ty + 10, fill=LABEL_BG,
                                       outline=col, tags="fx")
                    c.create_text(tx, ty, text=txt, fill=col, anchor="w",
                                  font=("Consolas", 9, "bold"), tags="fx")
            else:  # face cachée : cercle creux
                c.create_oval(px - 4, py - 4, px + 4, py + 4,
                              outline=blend(DISK, col, 0.35), tags="fx")

        c.create_text(10, h - 8, anchor="sw", fill=HINT, font=("Segoe UI", 8),
                      text="Glisser pour faire tourner  ·  équateur en turquoise", tags="fx")

    # Cette fonction tourne en boucle (environ 30 fois par seconde) : elle met à jour
    # l'orientation du globe puis le redessine. C'est ça qui crée l'animation.
    def tick(self):
        if self.follow and self.focus is not None and not self.dragging and self.points:
            phi, lam, _ = self.points[self.focus]
            # Je tourne le globe pour que la longitude du point arrive face à moi. Dans le schéma, j'ajoute
            # 1 radian pour avoir une vue de biais, plus lisible.
            schema = self.mode.get() == "schema"
            target = -math.pi / 2 - lam + (1.0 if schema else 0.0)   # schéma : vue oblique
            d = (target - self.spin + math.pi) % (2 * math.pi) - math.pi
            self.spin += d * 0.10
            tt = 0.45 if schema else max(-0.3, min(1.1, 0.3 + 0.5 * phi))
            self.tilt += (tt - self.tilt) * 0.08
        # Tant qu'il n'y a aucun point, je laisse le globe tourner doucement tout seul.
        elif not self.points and not self.dragging:
            self.spin += 0.006          # rotation lente tant qu'aucun point n'existe
        self.draw()
        self.after(33, self.tick)


# TEST UNITAIRE : le point Merchich
# Pour le lancer :   python conversion_geodesique_avec_tests.py --test
# Le but : vérifier que mes deux conversions sont justes sur le vrai point Merchich du cours,
# avec l'ellipsoïde Clarke 1880.
# 
class TestPointMerchich(unittest.TestCase):
    # Les coordonnées géodésiques du point Merchich, telles qu'elles sont données dans le cours :
    #   latitude  = 33°26'59.672" Nord
    #   longitude =  7°33'27.295" Ouest
    #   hauteur   = 243.419 m au sol, et 243.730 m au sommet du pilier
    LAT_DMS, LON_DMS = "33 26 59.672 N", "7 33 27.295 W"

    # Pour chaque hauteur : (h, X attendu, Y attendu, Z attendu), en mètres.
    # Le cours ne donne pas X, Y, Z : je les ai calculés avec mon programme et recoupés avec une
    # autre formule (latitude réduite), l'écart entre les deux est de l'ordre du nanomètre.
    CAS = [
        (243.419, 5281240.024, -700688.767, 3495569.845),   # au sol
        (243.730, 5281240.281, -700688.801, 3495570.017),   # au sommet du pilier
    ]

    def test_point_merchich(self):
        a, b = ELLIPSOIDES["Clarke 1880 (Merchich)"]

        # Je lis la latitude et la longitude exactement comme le fait l'application :
        # avec parse_angle, qui transforme le DMS en degrés décimaux (Ouest = négatif).
        lat = parse_angle(self.LAT_DMS)
        lon = parse_angle(self.LON_DMS)
        self.assertAlmostEqual(lat, 33.449908889, places=8)
        self.assertAlmostEqual(lon, -7.557581944, places=8)

        for h, X, Y, Z in self.CAS:
            with self.subTest(hauteur=h):
                # Étape 1 : je pars de (φ, λ, h), je calcule (X, Y, Z) et je compare avec ce que
                # j'attends. J'accepte 1 mm d'écart (à cause des valeurs arrondies).
                x, y, z = geo_to_cart(math.radians(lat), math.radians(lon), h, a, b)
                self.assertAlmostEqual(x, X, delta=0.001)
                self.assertAlmostEqual(y, Y, delta=0.001)
                self.assertAlmostEqual(z, Z, delta=0.001)

                # Étape 2 : je fais le chemin inverse avec mes deux méthodes (directe et
                # itérative) et je dois retrouver φ, λ et h de départ.
                for methode in (cart_to_geo_directe, cart_to_geo_iterative):
                    phi, lam, hh = methode(X, Y, Z, a, b)
                    self.assertAlmostEqual(math.degrees(phi), lat, places=7)
                    self.assertAlmostEqual(math.degrees(lam), lon, places=7)
                    self.assertAlmostEqual(hh, h, delta=0.005)


if __name__ == "__main__":
    # Si je lance le fichier avec --test, ça exécute le test ; sinon ça ouvre l'application.
    if "--test" in sys.argv:
        unittest.main(argv=[sys.argv[0], "-v"])
    else:
        App().mainloop()
