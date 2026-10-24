# B2R TALENTS — Maintenance SEO intégrale

## Installation

L'archive reproduit **les chemins exacts du dépôt GitHub `b2rtalents/b2r-talents2`**.
Décompresser à la racine du dépôt, conserver l'arborescence, remplacer les fichiers existants portant le même nom, puis envoyer le contenu sur la branche `main`.
Sur GitHub, l'action **B2R | Maintenance SEO intégrale** démarre à l'ajout du nouveau workflow/du script (si GitHub Actions est autorisé à écrire). On peut également la lancer via **Actions → B2R | Maintenance SEO intégrale → Run workflow**.

## Contenu du correctif

- `scripts/seo_maintenance.py` : migration des URL historiques, unification des URL canoniques sur `b2r-talents.fr` (conformément au CNAME existant), réconciliation des articles, détection des liens internes manquants, sitemap exhaustif excluant les pages `noindex`.
- `.github/workflows/seo-maintenance.yml` : exécution automatique au dépôt initial et lancement manuel ultérieur ; régénération des pages à partir des sources, contrôles et commit des corrections uniquement si les vérifications réussissent.
- `.github/workflows/publish-reflexions.yml` : ajoute la reconstruction du sitemap et le contrôle de l'intégrité SEO à la publication des Réflexions (sans supprimer le flux Pages CMS existant).
- `.htaccess` : redirections HTTP 301 si Apache sert le site (sur GitHub Pages, `.htaccess` n'est pas interprété).
- `atelier-trajectoires-professionnelles/index.html` : redirection HTML immédiate pour GitHub Pages.
- `reflexions/publications/lessh1greater.../index.html` : conservation de l'ancienne URL d'article en passerelle vers le nouveau slug.
- `robots.txt` et `sitemap.xml` : version canonique cohérente et 18 URL prévues.
- `tests/test_seo_maintenance.py` : vérifications de migration idempotente, `noindex`, et détection des liens cassés.

## Contrôles automatiques

1. Vérifie que CNAME = `b2r-talents.fr` et ne change jamais le fichier CNAME.
2. Renomme le fichier source Markdown mal nommé et **régénère** les pages et médias à partir du CMS source.
3. Préserve les deux anciennes URL au lieu de les laisser répondre 404.
4. Normalise les URL internes absolues et balises canoniques sur le domaine déclaré.
5. Régénère `sitemap.xml` à partir des fichiers HTML réellement présents, en excluant les pages `noindex` (juridique, 404 et anciennes URL).
6. Vérifie liens internes, canoniques et sitemap. En cas d'anomalie, le workflow échoue **avant le commit**.

## Prérequis et limite

Le dépôt nécessite l'autorisation GitHub Actions **Read and write permissions** pour que le workflow publie automatiquement son résultat. Si cette autorisation est bloquée, le workflow échouera sans publier de corrections. Le connecteur GitHub de cette conversation a renvoyé HTTP 403 à la création d'une branche : aucun fichier n'a été modifié sur le dépôt distant par l'assistant.

Ce livrable a été vérifié par 3 tests Python et par un contrôle des liens référencés dans les 21 pages HTML indexables ou juridiques accessibles dans le dépôt GitHub. Il reste à valider la publication et les réponses HTTP sur le domaine en production ; aucun succès de déploiement n'est présumé.
