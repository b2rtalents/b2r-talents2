#!/usr/bin/env python3
"""B2R TALENTS — maintenance SEO idempotente du site statique.

Utilisation depuis la racine du dépôt :
  python scripts/seo_maintenance.py --apply [--regenerate]
  python scripts/seo_maintenance.py --check

N'utilise aucun service externe ; ne change jamais les pages métier.
"""
from __future__ import annotations

import argparse
from html.parser import HTMLParser
import posixpath
import re
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlsplit, unquote
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
DOMAIN = "b2r-talents.fr"  # Correspond au fichier CNAME du dépôt
SITE = f"https://{DOMAIN}"
WWW = f"https://www.{DOMAIN}"
OLD_ATELIER = "/atelier-trajectoires-professionnelles/"
NEW_ATELIER = "/atelier-cadres/"
OLD_SLUG = "lessh1greaterneurodiversite-en-entreprise-avant-dinclure-encore-faut-il-comprendrelessh1greater"
NEW_SLUG = "neurodiversite-en-entreprise-avant-dinclure-encore-faut-il-comprendre"
OLD_ARTICLE = f"/reflexions/publications/{OLD_SLUG}/"
NEW_ARTICLE = f"/reflexions/publications/{NEW_SLUG}/"
OLD_MD = ROOT / "reflexions/contenus/articles" / f"2026-10-06-{OLD_SLUG}.md"
NEW_MD = ROOT / "reflexions/contenus/articles" / f"2026-10-06-{NEW_SLUG}.md"

HTACCESS = r"""# Canonicalisation du domaine (Apache/OVH uniquement).
<IfModule mod_rewrite.c>
RewriteEngine On
RewriteCond %{HTTP_HOST} ^www\.b2r-talents\.fr$ [NC]
RewriteRule ^ https://b2r-talents.fr%{REQUEST_URI} [R=301,L,NE]
</IfModule>

# Permaliens conservés après refonte.
RedirectMatch 301 ^/atelier-trajectoires-professionnelles/?$ https://b2r-talents.fr/atelier-cadres/
RedirectMatch 301 ^/reflexions/publications/lessh1greaterneurodiversite-en-entreprise-avant-dinclure-encore-faut-il-comprendrelessh1greater/?$ https://b2r-talents.fr/reflexions/publications/neurodiversite-en-entreprise-avant-dinclure-encore-faut-il-comprendre/

ErrorDocument 404 /404.html
"""

ROBOTS = f"User-agent: *\nAllow: /\n\nSitemap: {SITE}/sitemap.xml\n"


class PageParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.canonicals: list[str] = []
        self.noindex = False
        self.links: list[tuple[str, str]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        a = {key.lower(): (value or "") for key, value in attrs}
        if tag == "meta" and a.get("name", "").lower() == "robots":
            self.noindex |= "noindex" in a.get("content", "").lower().replace(" ", "")
        if tag == "link" and "canonical" in a.get("rel", "").lower().split():
            self.canonicals.append(a.get("href", ""))
        if tag == "a" and a.get("href"):
            self.links.append(("a", a["href"]))
        if tag in ("img", "script", "source") and a.get("src"):
            self.links.append((tag, a["src"]))
        if tag == "link" and "stylesheet" in a.get("rel", "").lower().split() and a.get("href"):
            self.links.append((tag, a["href"]))


def parse_html(path: Path) -> PageParser:
    result = PageParser()
    result.feed(path.read_text(encoding="utf-8"))
    return result


def pages() -> list[Path]:
    """Pages de la racine, hors gabarits/archives cachées."""
    return sorted(
        (x for x in ROOT.rglob("index.html") if not any(
            part.startswith(".") or part in ("node_modules", "__pycache__", "publications.__tmp__")
            for part in x.relative_to(ROOT).parts
        )), key=lambda x: str(x)
    )


def permalink(path: Path) -> str:
    rel = path.relative_to(ROOT)
    return "/" if len(rel.parts) == 1 else "/" + "/".join(rel.parts[:-1]) + "/"


def bridge(target: str, title: str) -> str:
    absolute = SITE + target
    # Double compatibilité : GitHub Pages (HTML immédiat) et Apache (.htaccess 301).
    return f'''<!doctype html>
<html lang="fr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title} — redirection | B2R TALENTS</title>
<meta name="robots" content="noindex,follow"><link rel="canonical" href="{absolute}">
<meta http-equiv="refresh" content="0;url={absolute}">
<script>location.replace({absolute!r});</script></head>
<body><p>Cette page a changé d'adresse. <a href="{absolute}">Accéder à la page actuelle</a>.</p></body></html>
'''


def write_if_changed(path: Path, data: str, changed: list[str]) -> None:
    previous = path.read_text(encoding="utf-8") if path.is_file() else None
    if data != previous:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(data, encoding="utf-8")
        changed.append(str(path.relative_to(ROOT)))


def update_source(changed: list[str]) -> None:
    if OLD_MD.exists():
        if NEW_MD.exists():
            raise ValueError(f"Deux articles portent le même titre : {OLD_MD} / {NEW_MD}")
        OLD_MD.rename(NEW_MD)
        changed.extend([str(OLD_MD.relative_to(ROOT)) + " (renommé)", str(NEW_MD.relative_to(ROOT))])


def regenerate() -> None:
    script = ROOT / "scripts/generate_reflexions.py"
    if script.exists():
        subprocess.run([sys.executable, str(script)], cwd=ROOT, check=True)


def apply(changed: list[str], do_regenerate: bool) -> None:
    if not (ROOT / "CNAME").exists():
        raise ValueError("CNAME manquant : publication ou domaine à confirmer")
    cname = (ROOT / "CNAME").read_text(encoding="utf-8").strip()
    if cname != DOMAIN:
        raise ValueError(f"CNAME={cname!r}, attendu {DOMAIN!r}. Ne pas modifier aveuglément le domaine.")

    if OLD_MD.exists() and not do_regenerate:
        raise ValueError("La migration initiale du slug exige --regenerate pour préserver le contenu")
    update_source(changed)
    generator = ROOT / "scripts/generate_reflexions.py"
    if generator.is_file():
        source = generator.read_text(encoding="utf-8")
        # Le générateur doit produire directement des canoniques cohérentes.
        fixed = source.replace(f'SITE = "{WWW}"', f'SITE = "{SITE}"')
        if f'SITE = "{SITE}"' not in fixed:
            raise ValueError("Constante SITE introuvable dans generate_reflexions.py")
        write_if_changed(generator, fixed, changed)
    if do_regenerate:
        regenerate()

    write_if_changed(ROOT / ".htaccess", HTACCESS, changed)
    write_if_changed(ROOT / "robots.txt", ROBOTS, changed)

    for path in pages():
        original = path.read_text(encoding="utf-8")
        # Ne modifie ni le texte ni la structure : uniquement les URL publiques de B2R.
        updated = original.replace(WWW, SITE)
        write_if_changed(path, updated, changed)

    write_if_changed(ROOT / OLD_ATELIER.lstrip("/") / "index.html", bridge(NEW_ATELIER, "Atelier Trajectoire Cadres"), changed)
    write_if_changed(ROOT / OLD_ARTICLE.lstrip("/") / "index.html", bridge(NEW_ARTICLE, "Neurodiversité en entreprise"), changed)
    write_if_changed(ROOT / "sitemap.xml", make_sitemap(), changed)


def make_sitemap() -> str:
    urls: list[str] = []
    for path in pages():
        info = parse_html(path)
        if info.noindex:
            continue
        urls.append(SITE + permalink(path))
    # Évite les duplications et génère exactement les pages indexables présentes.
    urls = sorted(set(urls), key=lambda u: (u != SITE + "/", u))
    lines = ['<?xml version="1.0" encoding="UTF-8"?>',
             '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for url in urls:
        lines.append(f"  <url><loc>{url}</loc></url>")
    lines.append("</urlset>")
    return "\n".join(lines) + "\n"


def local_target(page: Path, raw: str) -> Path | None:
    if raw.startswith("//"):
        return None
    parsed = urlsplit(raw)
    if parsed.scheme or parsed.netloc or raw.startswith("#") or not parsed.path:
        return None
    raw_path = unquote(parsed.path)
    base = permalink(page)
    resolved = posixpath.normpath(raw_path if raw_path.startswith("/") else base + raw_path)
    if not resolved.startswith("/"):
        resolved = "/" + resolved
    candidate = ROOT / resolved.lstrip("/")
    if candidate.is_dir() or raw_path.endswith("/"):
        return candidate / "index.html"
    if candidate.is_file():
        return candidate
    if not candidate.suffix:
        return candidate / "index.html"
    return candidate


def check() -> list[str]:
    errors: list[str] = []
    if not (ROOT / "CNAME").is_file() or (ROOT / "CNAME").read_text().strip() != DOMAIN:
        errors.append("CNAME et domaine canonique incompatibles")
    if (ROOT / "robots.txt").read_text(encoding="utf-8") != ROBOTS:
        errors.append("robots.txt ne pointe pas vers le domaine canonique")
    if (ROOT / ".htaccess").read_text(encoding="utf-8") != HTACCESS:
        errors.append(".htaccess sans l'ensemble des redirections prévues")
    for old, new in ((OLD_ATELIER, NEW_ATELIER), (OLD_ARTICLE, NEW_ARTICLE)):
        legacy = ROOT / old.lstrip("/") / "index.html"
        if not legacy.is_file() or not parse_html(legacy).noindex or SITE + new not in legacy.read_text(encoding="utf-8"):
            errors.append(f"Ancienne URL sans passerelle : {old}")
    if OLD_MD.exists() or not NEW_MD.exists():
        errors.append("Slug ancien de l'article neurodiversité encore présent dans les sources")
    if not (ROOT / NEW_ARTICLE.lstrip("/") / "index.html").is_file():
        errors.append("Nouvelle page de l'article neurodiversité absente")
    generator = ROOT / "scripts/generate_reflexions.py"
    if generator.is_file() and f'SITE = "{SITE}"' not in generator.read_text(encoding="utf-8"):
        errors.append("Le générateur d'articles produit le mauvais domaine")

    for page in pages():
        info = parse_html(page)
        url = SITE + permalink(page)
        if not info.noindex and info.canonicals != [url]:
            errors.append(f"Canonique incorrecte : {page.relative_to(ROOT)} -> {info.canonicals} (attendu {url})")
        for tag, link in info.links:
            target = local_target(page, link)
            if target is not None and not target.is_file():
                errors.append(f"Lien interne absent : {page.relative_to(ROOT)} [{tag}] {link}")
        # Les anciennes URL ne doivent pas être utilisées dans les autres pages.
        if permalink(page) not in (OLD_ATELIER, OLD_ARTICLE):
            raw = page.read_text(encoding="utf-8")
            if OLD_ATELIER in raw or OLD_ARTICLE in raw:
                errors.append(f"Ancienne URL dans {page.relative_to(ROOT)}")
    sitemap = ROOT / "sitemap.xml"
    if not sitemap.is_file() or sitemap.read_text(encoding="utf-8") != make_sitemap():
        errors.append("sitemap.xml désynchronisé avec les pages indexables")
    else:
        try:
            ET.parse(sitemap)
        except ET.ParseError as exc:
            errors.append(f"XML sitemap invalide : {exc}")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--apply", action="store_true", help="Réaligner les fichiers SEO")
    action.add_argument("--check", action="store_true", help="Vérifier sans modifier")
    parser.add_argument("--regenerate", action="store_true", help="Regénérer les publications depuis les sources (avec --apply)")
    args = parser.parse_args()
    if args.regenerate and not args.apply:
        parser.error("--regenerate exige --apply")
    try:
        if args.apply:
            changed: list[str] = []
            apply(changed, args.regenerate)
            print("Fichiers ajustés :", ", ".join(changed) if changed else "aucun (déjà conforme)")
        problems = check()
        if problems:
            print("ÉCHEC — incohérences détectées :", file=sys.stderr)
            for item in problems:
                print(" -", item, file=sys.stderr)
            return 1
        print(f"OK — {len(pages())} pages examinées ; sitemap synchronisé ; canonicals, redirections et liens vérifiés.")
        return 0
    except (OSError, ValueError, subprocess.CalledProcessError) as exc:
        print(f"ÉCHEC : {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
