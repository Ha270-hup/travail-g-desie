# Conversion de coordonnées géodésiques

Application Python (Tkinter) qui convertit des coordonnées géodésiques en coordonnées
cartésiennes 3D, et inversement, avec une visualisation interactive.

- **①** (φ, λ, h) → (X, Y, Z)
- **②** (X, Y, Z) → (φ, λ, h), par méthode **directe** ou **itérative**

Chaque point converti est affiché :

- sur un **schéma géodésique** pédagogique (ellipsoïde, axes X Y Z, normale, angles φ et λ,
  hauteur h, projections de P) ;
- sur un **globe terrestre 3D** que l'on fait tourner à la souris.

## Fonctionnalités

- Ellipsoïdes prédéfinis : Clarke 1880 (Merchich), GRS 80, WGS 84, Hayford 1909, ou **personnalisé** (a, b)
- Saisie des angles en degrés décimaux (`35.7595`) ou en DMS (`35 45 34.2 N`, `5°50'01"W`)
- Affichage du résultat en décimal et en DMS
- Liste des points convertis, cliquable pour recentrer la vue
- Grille latitude / longitude avec pas réglable (10°, 15°, 30°)
- 6 thèmes de couleurs : `sombre`, `clair`, `foret`, `violet`, `chaud`, `ocean`

## Installation

Aucune dépendance externe : seulement la bibliothèque standard de Python (3.8+) avec Tkinter.

```bash
git clone https://github.com/<votre-compte>/<votre-depot>.git
cd <votre-depot>
python conversion_geodesique_commente.py
```

Pour choisir un thème :

```bash
python conversion_geodesique_commente.py clair
```

> Sous Linux, si Tkinter est absent : `sudo apt install python3-tk`

## Formules utilisées

Avec e² = (a² − b²) / a² et N = a / √(1 − e² sin²φ) :

```
X = (N + h) cos φ cos λ
Y = (N + h) cos φ sin λ
Z = (N (1 − e²) + h) sin φ
```

Pour le sens inverse, λ = atan2(Y, X), puis φ et h sont obtenus soit par une formule
directe (sans boucle), soit par itération jusqu'à convergence.

## Limites

- Le cas des pôles (X = Y = 0) n'est pas traité.
- Les contours des continents sont très simplifiés : ils servent uniquement de repère visuel.
- Sur le schéma, l'aplatissement est exagéré ×40 ; seul le dessin est exagéré, les valeurs
  calculées sont exactes.

## Licence

À définir (par exemple MIT).
