# Conversion de coordonnées géodésiques

Application Python (Tkinter) qui convertit des coordonnées géodésiques en coordonnées
cartésiennes 3D, et inversement, avec une visualisation interactive.

- **①** (φ, λ, h) → (X, Y, Z)
- **②** (X, Y, Z) → (φ, λ, h), par méthode **directe** ou **itérative**

Chaque point converti est affiché :

- sur un **schéma géodésique** pédagogique (ellipsoïde, axes X Y Z, normale, angles φ et λ,
  hauteur h, projections de P) ;
- sur un **globe terrestre 3D** que l'on fait tourner à la souris.

## Captures d'écran

### Conversion ① et schéma géodésique

![Conversion ① et schéma géodésique](images/schema.png)

### Conversion ① et vue Terre

![Conversion ① et vue Terre](images/terre.png)

### Conversion ② (X, Y, Z → φ, λ, h)

![Conversion ② et vue Terre](images/conversion2.png)

## Fonctionnalités

- Ellipsoïdes prédéfinis : Clarke 1880 (Merchich), GRS 80, WGS 84, Hayford 1909, ou **personnalisé** (a, b)
- Saisie des angles en degrés décimaux (`35.7595`) ou en DMS (`35 45 34.2 N`, `5°50'01"W`)
- Affichage du résultat en décimal et en DMS
- Liste des points convertis, cliquable pour recentrer la vue
- Grille latitude / longitude avec pas réglable (10°, 15°, 30°)
- 6 thèmes de couleurs : `sombre`, `clair`, `foret`, `violet`, `chaud`, `ocean`

## Formules utilisées

Avec e² = (a² − b²) / a² et N = a / √(1 − e² sin²φ) :

```
X = (N + h) cos φ cos λ
Y = (N + h) cos φ sin λ
Z = (N (1 − e²) + h) sin φ
```

Pour le sens inverse, λ = atan2(Y, X), puis φ et h sont obtenus soit par une formule
directe (sans boucle), soit par itération jusqu'à convergence.
