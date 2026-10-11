# Conversion de coordonnées géodésiques

Application Python (Tkinter) qui convertit des coordonnées géodésiques en coordonnées
cartésiennes 3D, et inversement, avec une visualisation interactive.

- **①** (φ, λ, h) → (X, Y, Z)
- **②** (X, Y, Z) → (φ, λ, h), par méthode **directe** ou **itérative**

Chaque point converti est affiché :

- sur un **schéma géodésique** pédagogique (ellipsoïde, axes X Y Z, normale, angles φ et λ,
  hauteur h, projections de P) ;
- sur un **globe terrestre 3D** que l'on fait tourner à la souris.

  ### Captures de l'interface
  On saisit φ = 35.7595°, λ = -5.8337° et h = 60 m sur l'ellipsoïde Clarke 1880 (Merchich). Le programme calcule X = 5155038.6514 m, Y = -526693.2683 m et Z = 3706332.4660 m. Le schéma montre le point P1 sur l'ellipsoïde avec :

les axes X, Y, Z et le méridien du point (en jaune) ;
la normale à la surface, la hauteur h (en rose) et les angles φ et λ ;
les projections en pointillés qui donnent X, Y et Z ;
l'équateur en turquoise.
 
![Fenêtre principale](conversion2.png)

**Vue « Schéma géodésique » : normale, angles φ et λ, hauteur h, axes XYZ**

![Schéma géodésique](schema.png)

**Vue « Terre » : globe coloré avec les points convertis**

![Vue Terre](terre.png)



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



