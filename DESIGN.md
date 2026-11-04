# Meridian — direction artistique

Ce document fixe les choix visuels de Meridian. Il s'applique à **tout nouvel élément**, qu'il soit créé à la main ou par une IA (Cursor, Claude, etc.) : landing, application, e-mails, documents.

En cas de doute, on regarde la landing (`apps/web/app/(site)/`) : c'est la référence vivante.

---

## 1. L'intention

**Light premium SaaS, product-led.** Le produit est le héros visuel : on donne envie d'utiliser l'outil en le montrant, pas en le décrivant.

- **Ambiance :** précise, fiable, haut de gamme. Technique sans être froide, sûre d'elle sans en faire trop.
- **Niveau de finition visé :** Stripe, et Linear en version claire.
- **À distinguer de Meteoria**, le concurrent : pas de photos de paysages, pas de tons pastel, pas de boutons noirs.

## 2. Les cinq règles qui priment sur tout

1. **Un seul accent : l'orange `#FF4F1A`.** Il est réservé à **la marque du client** (ses données, son rang, son score) et à **l'action principale** d'un écran. Une seule action orange par écran.
2. **Dans toute comparaison, le client est la seule donnée en couleur.** Les concurrents restent en gris.
3. **Pas de vert ni de rouge.** Un état (réussi, à corriger, erreur) se lit par une icône, un libellé et une forme, jamais par une couleur.
4. **Une seule famille de caractères : Satoshi**, en 500 et 600 uniquement, avec des chiffres tabulaires pour les données.
5. **Seul le produit bouge, le texte ne bouge jamais.** Les animations montrent des données qui arrivent ; elles ne décorent pas.

---

## 3. Couleurs

| Rôle | Valeur | Tailwind (app) | Usage |
|---|---|---|---|
| Fond | `#FFFFFF` | `bg-background` | Fond des pages et des cartes |
| Surface | `#F6F7F9` | `bg-muted` | Sections alternées, fonds de zones, barre latérale (`#FBFBFC`) |
| Bordure | `#E7E9EE` | `border-border` | Filets de 1 px |
| Texte | `#111318` | `text-foreground` | Texte principal, erreurs |
| Texte secondaire | `#6B7280` | `text-muted-foreground` | Légendes, métadonnées (4,9:1 sur blanc) |
| Bord de champ | `#8A909A` | `border-input` | Champs de formulaire (3,2:1) |
| Gris concurrents | `#8A909A`, `#AEB3BB`, `#C9CDD4`, `#DDE0E5` | `grey`, `grey-soft` | Séries des concurrents, du plus foncé au plus clair |
| Accent | `#FF4F1A` | `bg-primary` | Marque du client, action principale |
| Accent survol | `#FF6A3D` | `bg-primary-hover` | Survol du bouton principal |
| Accent doux | `rgb(255 79 26 / 0.10)` | `bg-primary-soft` | Surlignage de la marque, pastille de rang |
| Méridiens | `#E2E5EA` sur blanc, `#DCDFE5` sur surface | — | Motif du globe |

**Contrastes à respecter (WCAG AA) :**

- **Texte sur l'orange :** toujours en encre `#111318` (5,7:1). Jamais en blanc (3,3:1, échoue).
- **L'orange n'est jamais une couleur de texte** sur fond clair (3,3:1). Pour signaler une valeur du client, on met le texte en encre et on ajoute une pastille ou un trait orange.
- **Champs de formulaire :** le bord est `#8A909A` (3,2:1), pas `#E7E9EE`, sinon le champ est invisible pour une partie des utilisateurs.

## 4. Typographie

- **Famille :** Satoshi, auto-hébergée (`apps/web/app/fonts/Satoshi-Variable.woff2`, licence Fontshare), chargée une fois dans `app/layout.tsx`. N'ajoutez ni Inter, ni Geist, ni police mono.
- **Graisses :** 500 pour le texte courant, 600 pour les titres, les boutons et les chiffres clés. Rien d'autre.
- **Chiffres :** `tabular-nums` partout où des nombres s'alignent ou changent (tableaux, KPI, prix, compteurs).
- **Titres serrés :** `letter-spacing: -0.03em` à partir de 32 px, `-0.02em` de 20 à 24 px.

| Rôle | Taille / interligne |
|---|---|
| Hero | 40 → 72 px, fluide |
| Titre de section | 32 → 56 px, fluide |
| Titre de page (app) | 30 → 36 px |
| Titre de bloc | 24 → 32 px |
| Chapeau | 18 / 28 |
| Texte courant | 16 / 24 |
| Interface produit | 14 / 20 |
| Axes, pastilles | 12 / 16 |

**Interdits :** les petits labels en capitales espacées au-dessus d'un titre (« eyebrows »). Une précision de contexte (semaine, secteur) se met **sous** le titre, en texte secondaire.

## 5. Espacements, rayons, ombres

- **Grille de 8 px :** 8, 16, 24, 32, 40, 48, 64, 80, 96, 128. Le demi-pas de 4 px est réservé à l'interface dense.
- **Rayons :** 8 px pour les champs et petites pastilles carrées, 12 px pour les cartes, 16 px pour les fenêtres d'application et les cartes flottantes, pilule (`rounded-full`) pour les boutons et les pastilles.
- **Ombres en couches, teintées d'encre**, jamais grises ni noires pures :
  - `shadow-xs` : boutons secondaires, cartes au repos ;
  - `shadow-md` : cartes mises en avant, survol ;
  - `shadow-float` : cartes flottantes, menus.
- **Bordures :** 1 px `#E7E9EE`. Pas de bordures épaisses, pas de bordures colorées.

## 6. Composants

Dans l'application, partez toujours des composants de `apps/web/components/ui/` : ils appliquent déjà ces règles.

- **Boutons (`Button`)** : en pilule, graisse 600.
  - `default` (orange) : l'action principale de l'écran, une seule par écran.
  - `outline` : toutes les autres actions.
  - `ghost` : actions discrètes dans une liste (retirer, annuler).
- **Cartes (`Card`)** : fond blanc, filet de 1 px, rayon de 12 px, `shadow-xs`. Évitez les grilles de cartes toutes identiques : variez les tailles et le contenu.
- **Champs (`Input`, `Textarea`)** : bord `#8A909A`, contour encre au focus, libellé visible au-dessus (`Label`). Un placeholder n'est pas un libellé.
- **Pastilles (`Badge`)** :
  - `good` (réussi) : surface et filet ;
  - `warn` (à surveiller) : contour encre ;
  - `bad` (à corriger) : fond encre, texte blanc ;
  - `brand` (donnée du client) : orange doux ;
  - `neutral` : information.

  Ajoutez une icône quand l'état compte (coche, cercle d'alerte).
- **Erreurs** : texte en encre, en semi-gras, avec une icône si possible. Jamais en rouge.
- **Tableaux** : en-têtes en 12 px, graisse 500, gris secondaire, sans capitales. Cellules en 14 px, chiffres tabulaires, lignes séparées par un filet.
- **Sélection (onglets, filtres)** : l'élément actif est en encre (`bg-foreground text-background`) ou en blanc sur fond de surface. Jamais en orange.
- **Liens** : en encre, soulignés au survol (ou soulignés d'un filet clair au repos dans un texte courant).

## 7. Graphiques et données

- **La marque du client est la seule série en orange.** Les concurrents utilisent les gris, du plus foncé au plus clair. Quand plusieurs séries décrivent le client lui-même, la principale est en orange, les autres en encre puis en gris pointillé.
- **Traits de 2 px**, extrémités de barres arrondies à 4 px du côté de la valeur, grilles `#EEF0F3`, axes sans ligne.
- **Le texte reste en encre ou en gris**, jamais dans la couleur de la série. Une pastille ou un trait coloré à côté porte l'identité.
- **Une légende dès qu'il y a deux séries**, et des étiquettes directes en bout de courbe quand c'est lisible.
- **Pas de double axe**, pas de camembert à plus de cinq parts (regroupez en « Autres »).
- **Les valeurs des gris clairs (`#C9CDD4`, `#DDE0E5`) sont toujours écrites en clair**, car ces gris n'atteignent pas 3:1.
- Les graphiques de l'app sont dans `apps/web/components/charts.tsx` : réutilisez leurs constantes.

## 8. Imagerie et motif

- **Uniquement des fragments d'interface crédibles :** fenêtres d'application, graphiques, réponses d'IA, tableaux, pastilles. Les données d'exemple sont fictives et cohérentes entre elles : voir `apps/web/components/landing/data.ts`, avec Orvalis comme client et Notafix, Kalcéo, Spendia et Fraisgo comme concurrents.
- **Motif signature :** les méridiens d'un globe (`components/landing/globe.tsx`), en filets très clairs, utilisés avec retenue : un ou deux par page au plus.
- **Logo :** le globe à méridiens et le mot « Meridian » en Satoshi 600, en encre. Le logo n'est jamais orange.
- **À éviter :**
  - photos d'ambiance ;
  - robots, cerveaux, étincelles ou dégradés violet-bleu pour représenter l'IA ;
  - logos officiels de ChatGPT, Perplexity ou Gemini (on écrit leurs noms en texte) ;
  - emojis utilisés comme icônes (on utilise `lucide-react`) ;
  - mode sombre générique.

## 9. Mouvement

**Seul le produit bouge, le texte ne bouge jamais.** Les titres, paragraphes et cartes sont là dès l'arrivée. Ce qui s'anime, ce sont les données qui prouvent ce que dit le texte : une réponse qui s'écrit, un chiffre qui se calcule, une courbe qui se dessine, une liste qui se trie.

**Une bibliothèque courte, partout la même :**

- **Deux courbes :**
  - `--ease-out`, `cubic-bezier(0.33, 1, 0.68, 1)`, pour ce qui apparaît ou se dessine ;
  - `--ease-in-out`, `cubic-bezier(0.65, 0, 0.35, 1)`, pour ce qui se déplace d'une place à une autre.
- **Trois durées :** 300 ms pour les survols, 600 ms pour les apparitions, 1,2 s pour les données. Décalage de 90 ms entre les éléments d'une même liste.
- **Quatre gestes :** fondu, fondu avec 4 px de montée, croissance (barres, surlignage), tracé de SVG.
- **Interdits :** changements d'échelle, rebonds, parallaxe, défilement lissé forcé, curseur personnalisé, animations en boucle (sauf la rotation très lente du globe), apparition en fondu de chaque section.
- **Une séquence se joue une seule fois**, quand son bloc entre à l'écran, puis reste dans son état final.
- **On n'anime que `transform`, `opacity` et le tracé des SVG.** Pour un survol qui doit se combiner avec une animation, on utilise `translate` plutôt que `transform`.
- **L'état final est le rendu par défaut.** Sans JavaScript ou avec `prefers-reduced-motion`, tout s'affiche directement. Sur la landing, c'est la classe `lp-motion` qui active les états de départ (voir `components/landing/motion.tsx`).
- **Survols :** les cartes répondent par leur ombre et ne montent que de 1 px ; les liens se soulignent ; la flèche des boutons avance de 2 px.

## 10. Rédaction

- Textes en français, clairs et directs, sans jargon marketing creux.
- Les chiffres d'exemple sont crédibles et cohérents d'un écran à l'autre.
- On écrit « ChatGPT, Perplexity et Gemini » en texte, jamais avec leurs logos.

## 11. Accessibilité

- Contraste AA partout (voir §3), cibles tactiles d'au moins 40 px de haut.
- Focus visible : contour encre de 2 px décalé de 2 px.
- Les maquettes d'interface décoratives portent `aria-hidden` et un résumé texte (`visually-hidden` ou `figcaption`).
- Responsive « mobile first » ; vérifiez à 375, 768, 1024 et 1440 px.

---

## Où vivent les tokens

| Fichier | Contenu |
|---|---|
| `apps/web/app/globals.css` | Tokens de l'application (Tailwind v4, `@theme`) |
| `apps/web/app/(site)/landing.css` | Tokens et styles de la landing, scopés sous `.landing` |
| `apps/web/components/ui/` | Composants de base déjà conformes |
| `apps/web/components/charts.tsx` | Couleurs et réglages des graphiques |
| `apps/web/components/landing/globe.tsx` | Globe et logo |

**Si une valeur change, changez-la dans `globals.css` et dans `landing.css`, puis ici.**

## Liste de contrôle avant de livrer un nouvel élément

- [ ] L'orange n'apparaît que pour la marque du client ou pour l'action principale, et une seule action est orange.
- [ ] Aucun vert, rouge, violet ou bleu ; les états se lisent par une icône et un libellé.
- [ ] Satoshi uniquement, en 500 et 600 ; les chiffres sont tabulaires.
- [ ] Aucun label en capitales au-dessus d'un titre.
- [ ] Les espacements tombent sur la grille de 8 px ; les rayons sont de 8, 12, 16 px ou en pilule.
- [ ] Les composants de `components/ui` sont réutilisés plutôt que recréés.
- [ ] Le contraste AA est respecté, y compris le bord des champs.
- [ ] Une éventuelle animation montre une donnée, utilise la bibliothèque de mouvement et respecte `prefers-reduced-motion`.
- [ ] L'élément a été vérifié en mobile et en desktop.
