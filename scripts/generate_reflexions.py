#!/usr/bin/env python3
from __future__ import annotations

import argparse
import html
import json
import re
import shutil
import sys
import unicodedata
from pathlib import Path

import yaml
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
CONTENT_ROOT = ROOT / "reflexions" / "contenus"
PUBLICATIONS_ROOT = ROOT / "reflexions" / "publications"
JSON_OUT = ROOT / "reflexions" / "contenus.json"
SITE = "https://www.b2r-talents.fr"

REQUIRED_ARTICLE = ("title", "date", "status", "category", "summary")
REQUIRED_REGARD = ("title", "date", "status", "category", "source", "url", "summary")
REQUIRED_VIDEO = ("title", "date", "status", "category", "url", "summary")


def fail(msg: str) -> None:
    print(f"ERREUR: {msg}", file=sys.stderr)
    raise SystemExit(1)


def slugify(value: str) -> str:
    value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    value = value.lower()
    value = re.sub(r"[^a-z0-9]+", "-", value).strip("-")
    return value or "contenu"


def parse_entry(path: Path) -> tuple[dict, str]:
    raw = path.read_text(encoding="utf-8")
    if not raw.startswith("---"):
        fail(f"{path}: front matter YAML manquant.")
    parts = raw.split("---", 2)
    if len(parts) < 3:
        fail(f"{path}: front matter YAML invalide.")
    data = yaml.safe_load(parts[1]) or {}
    body = parts[2].strip()
    return data, body


def check_required(data: dict, required: tuple[str, ...], path: Path) -> None:
    missing = [k for k in required if data.get(k) in (None, "", [])]
    if missing:
        fail(f"{path}: champ(s) requis manquant(s): {', '.join(missing)}")


def normalize_date(value) -> str:
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return str(value)


def clean_text(markup: str) -> str:
    text = re.sub(r"<[^>]+>", " ", markup)
    text = html.unescape(text)
    return re.sub(r"\s+", " ", text).strip()


def reading_minutes(markup: str) -> int:
    words = len(clean_text(markup).split())
    return max(1, round(words / 220))


def calloutify(markup: str) -> str:
    pattern = re.compile(r"<p>\s*<strong>(.*?)</strong>\s*</p>", re.I | re.S)
    return pattern.sub(r'<div class="callout">\1</div>', markup)


def optimize_image(image_url: str | None, slug: str, publication_root: Path) -> str:
    if not image_url:
        return ""
    rel = image_url.lstrip("/")
    src = ROOT / rel
    if not src.exists():
        fail(f"Illustration introuvable: {image_url}")
    out_dir = publication_root / "_media"
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / f"{slug}.webp"
    with Image.open(src) as im:
        im = im.convert("RGB")
        if im.width > 1600:
            h = round(im.height * (1600 / im.width))
            im = im.resize((1600, h), Image.Resampling.LANCZOS)
        im.save(out, "WEBP", quality=82, method=6)
    return f"/reflexions/publications/_media/{out.name}"


def article_html(data: dict, body: str, slug: str, image_url: str) -> str:
    title = str(data["title"])
    summary = str(data["summary"])
    category = str(data["category"])
    date = normalize_date(data["date"])
    mins = reading_minutes(body)
    canonical = f"{SITE}/reflexions/publications/{slug}/"
    og_image = f"{SITE}{image_url}" if image_url else f"{SITE}/assets/official/logo-b2r-talents.png"
    body = calloutify(body)
    structured = {
        "@context": "https://schema.org",
        "@type": "Article",
        "headline": title,
        "description": summary,
        "datePublished": date,
        "dateModified": date,
        "author": {"@type": "Organization", "name": "B2R TALENTS"},
        "publisher": {"@type": "Organization", "name": "B2R TALENTS"},
        "mainEntityOfPage": canonical,
        "image": [og_image],
        "articleSection": category,
    }
    cover = (
        f'<div class="cover-wrap"><img class="cover" src="{html.escape(image_url)}" '
        f'alt="Illustration de l’article {html.escape(title)}"></div>'
        if image_url else ""
    )
    return f'''<!doctype html>
<html lang="fr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(title)} | B2R TALENTS</title>
<meta name="description" content="{html.escape(summary, quote=True)}">
<link rel="canonical" href="{canonical}">
<link rel="icon" href="/favicon.ico">
<meta property="og:locale" content="fr_FR">
<meta property="og:type" content="article">
<meta property="og:site_name" content="B2R TALENTS">
<meta property="og:title" content="{html.escape(title, quote=True)}">
<meta property="og:description" content="{html.escape(summary, quote=True)}">
<meta property="og:url" content="{canonical}">
<meta property="og:image" content="{og_image}">
<meta name="twitter:card" content="summary_large_image">
<script type="application/ld+json">{json.dumps(structured, ensure_ascii=False)}</script>
<style>
:root{{--marine:#07315B;--blue:#1858AA;--ink:#18324a;--muted:#617b93;--line:#dbe6ef;--soft:#f6f9fc;--gold:#d9a93a}}
*{{box-sizing:border-box}}html{{scroll-behavior:smooth}}body{{margin:0;font-family:Arial,Helvetica,sans-serif;background:#f3f7fb;color:var(--ink)}}a{{color:inherit}}
.topbar{{background:#fff;border-bottom:1px solid var(--line)}}.nav{{max-width:1180px;margin:auto;padding:14px 24px;display:flex;align-items:center;gap:28px}}
.logo img{{display:block;width:210px;height:auto}}.navlinks{{display:flex;gap:20px;font-size:14px;color:#385b7b;flex-wrap:wrap}}.navlinks a{{text-decoration:none}}.navlinks a.active{{font-weight:700;color:var(--marine)}}
.hero{{background:#fff}}.hero-wrap{{max-width:1180px;margin:auto;padding:48px 24px 28px}}.eyebrow{{font-size:12px;letter-spacing:.14em;font-weight:800;color:var(--blue);text-transform:uppercase;margin-bottom:14px}}
h1{{font-size:48px;line-height:1.05;color:var(--marine);margin:0;max-width:980px;letter-spacing:-.02em}}.lead{{font-size:21px;line-height:1.55;color:#476b8b;max-width:900px;margin:24px 0 0}}
.meta{{display:flex;flex-wrap:wrap;gap:12px;margin-top:24px;font-size:13px;color:#6a8399}}.meta span{{background:#edf4fb;border-radius:999px;padding:8px 12px}}
.cover-wrap{{max-width:1180px;margin:0 auto;padding:0 24px 30px}}.cover{{width:100%;aspect-ratio:16/9;object-fit:cover;border-radius:18px;display:block;box-shadow:0 14px 36px rgba(7,49,91,.12)}}
.layout{{max-width:1180px;margin:auto;padding:34px 24px 70px;display:grid;grid-template-columns:minmax(0,760px) 260px;gap:64px;align-items:start}}
.article{{background:#fff;border:1px solid var(--line);border-radius:18px;padding:52px 58px;box-shadow:0 12px 30px rgba(7,49,91,.05)}}.article p{{font-size:18px;line-height:1.78;margin:0 0 22px}}
.article h2{{font-size:30px;line-height:1.18;color:var(--marine);margin:52px 0 20px}}.article h3{{font-size:23px;color:var(--marine);margin:38px 0 16px}}.article strong{{color:#0f4f91}}
.article ul,.article ol{{font-size:18px;line-height:1.7;padding-left:26px}}.article blockquote{{margin:30px 0;padding:18px 24px;border-left:4px solid var(--blue);background:#f7fbff;color:#294f72}}
.callout{{margin:34px -8px;padding:26px 28px;border-left:5px solid var(--gold);background:#f8fbfe;border-radius:0 12px 12px 0;font-size:21px;line-height:1.55;font-weight:700;color:var(--marine)}}
.article-footer{{margin-top:50px;padding-top:28px;border-top:1px solid var(--line)}}.article-footer h3{{color:var(--marine);margin:0 0 12px}}.article-footer p{{font-size:14px;color:var(--muted);line-height:1.6}}
.sidebar{{position:sticky;top:24px}}.sidecard{{background:#fff;border:1px solid var(--line);border-radius:16px;padding:22px;margin-bottom:18px}}.sidecard h3{{margin:0 0 10px;color:var(--marine);font-size:18px}}.sidecard p{{margin:0;color:var(--muted);font-size:14px;line-height:1.55}}
.cta{{display:block;text-align:center;margin-top:16px;background:var(--marine);color:#fff;text-decoration:none;font-weight:700;border-radius:10px;padding:13px 16px}}.back{{display:inline-block;margin-top:12px;color:var(--blue);font-size:14px;font-weight:700;text-decoration:none}}
.footer{{background:var(--marine);color:#fff}}.footer-wrap{{max-width:1180px;margin:auto;padding:26px 24px;font-size:13px;display:flex;justify-content:space-between;gap:20px;flex-wrap:wrap}}
@media(max-width:900px){{h1{{font-size:38px}}.lead{{font-size:19px}}.layout{{grid-template-columns:1fr;gap:24px}}.sidebar{{position:static}}}}
@media(max-width:640px){{.nav{{align-items:flex-start;flex-direction:column;gap:12px}}.navlinks{{gap:11px 16px}}.hero-wrap{{padding-top:30px}}h1{{font-size:33px}}.lead{{font-size:18px}}.article{{padding:32px 22px}}.article p{{font-size:17px;line-height:1.72}}.article h2{{font-size:26px;margin-top:42px}}.callout{{font-size:19px;margin-left:0;margin-right:0}}}}
</style>
</head>
<body>
<header class="topbar"><div class="nav">
<a class="logo" href="/"><img src="/assets/official/logo-b2r-talents.png" alt="B2R TALENTS"></a>
<nav class="navlinks" aria-label="Navigation principale">
<a href="/">Accueil</a><a href="/#services">Recrutement &amp; Executive Search</a><a href="/neurodiversite-b2b/">Neurodiversité B2B</a><a class="active" href="/reflexions/">Réflexions</a><a href="/about/">À propos</a><a href="/contact/">Contact</a>
</nav></div></header>
<section class="hero"><div class="hero-wrap">
<div class="eyebrow">Réflexion B2R • {html.escape(category)}</div>
<h1>{html.escape(title)}</h1>
<p class="lead">{html.escape(summary)}</p>
<div class="meta"><span>{html.escape(date)}</span><span>Lecture : ~{mins} min</span><span>B2R TALENTS</span></div>
</div>{cover}</section>
<main class="layout"><article class="article">
{body}
<div class="article-footer"><h3>À propos de B2R TALENTS</h3>
<p>B2R TALENTS intervient en recrutement, chasse et Executive Search, avec une attention particulière portée aux environnements Défense, Industrie et aux profils rares ou stratégiques.</p>
<a class="back" href="/reflexions/">← Retour aux Réflexions</a></div>
</article>
<aside class="sidebar"><div class="sidecard"><h3>Une réflexion vous interpelle ?</h3><p>Échangeons autour de vos enjeux de recrutement, de compétences et de trajectoires professionnelles.</p>
<a class="cta" href="https://cal.com/b2r-talents/echangepro?overlayCalendar=true">Prendre rendez-vous</a></div>
<div class="sidecard"><h3>Catégorie</h3><p>{html.escape(category)}</p></div></aside></main>
<footer class="footer"><div class="footer-wrap"><span>© 2026 B2R TALENTS</span><span>Recrutement • Chasse • Executive Search</span></div></footer>
</body></html>'''


def build(require_published: str | None = None) -> None:
    if require_published:
        req = ROOT / require_published
        if not req.exists():
            fail(f"Contenu déclencheur introuvable: {require_published}")
        req_data, _ = parse_entry(req)
        if req_data.get("status") != "published":
            fail("Le contenu est encore en Brouillon ou Archivé. Passez d'abord le statut à « Publié », sauvegardez, puis relancez « Publier sur B2R-TALENTS.FR ».")

    tmp = PUBLICATIONS_ROOT.with_name("publications.__tmp__")
    if tmp.exists():
        shutil.rmtree(tmp)
    tmp.mkdir(parents=True)

    entries: list[dict] = []

    # Articles B2R
    for path in sorted((CONTENT_ROOT / "articles").glob("*.md")):
        data, body = parse_entry(path)
        status = data.get("status", "draft")
        if status == "draft":
            continue
        check_required(data, REQUIRED_ARTICLE, path)
        if not body.strip():
            fail(f"{path}: article vide.")
        title = str(data["title"])
        stem = path.stem
        stem = re.sub(r"^\d{4}-\d{2}-\d{2}-", "", stem)
        slug = slugify(stem or title)
        image = optimize_image(data.get("image"), slug, tmp)
        out_dir = tmp / slug
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "index.html").write_text(article_html(data, body, slug, image), encoding="utf-8")
        entries.append({
            "id": slug,
            "type": "Réflexion B2R",
            "categorie": str(data["category"]),
            "titre": title,
            "date": normalize_date(data["date"]),
            "source": "B2R TALENTS",
            "url": f"publications/{slug}/",
            "resume": str(data["summary"]),
            "mon_regard": "",
            "image": image,
            "statut": "archive" if status == "archived" else "publie",
        })

    # Regards extérieurs
    for path in sorted((CONTENT_ROOT / "regards").glob("*.md")):
        data, body = parse_entry(path)
        status = data.get("status", "draft")
        if status == "draft":
            continue
        check_required(data, REQUIRED_REGARD, path)
        entries.append({
            "id": slugify(path.stem),
            "type": "À lire",
            "categorie": str(data["category"]),
            "titre": str(data["title"]),
            "date": normalize_date(data["date"]),
            "source": str(data["source"]),
            "url": str(data["url"]),
            "resume": str(data["summary"]),
            "mon_regard": clean_text(body),
            "image": str(data.get("image") or ""),
            "statut": "archive" if status == "archived" else "publie",
        })

    # Vidéos
    for path in sorted((CONTENT_ROOT / "videos").glob("*.md")):
        data, body = parse_entry(path)
        status = data.get("status", "draft")
        if status == "draft":
            continue
        check_required(data, REQUIRED_VIDEO, path)
        entries.append({
            "id": slugify(path.stem),
            "type": "Vidéo",
            "categorie": str(data["category"]),
            "titre": str(data["title"]),
            "date": normalize_date(data["date"]),
            "source": "B2R TALENTS",
            "url": str(data["url"]),
            "resume": str(data["summary"]),
            "mon_regard": clean_text(body),
            "image": str(data.get("image") or ""),
            "statut": "archive" if status == "archived" else "publie",
        })

    entries.sort(key=lambda x: x["date"], reverse=True)

    # Validation avant bascule.
    for item in entries:
        if item["statut"] == "publie" and not item["url"]:
            fail(f"Lien manquant pour {item['titre']}.")

    if PUBLICATIONS_ROOT.exists():
        shutil.rmtree(PUBLICATIONS_ROOT)
    tmp.rename(PUBLICATIONS_ROOT)
    JSON_OUT.write_text(json.dumps(entries, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"OK: {len(entries)} contenu(s) généré(s).")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--require-published", default=None)
    args = parser.parse_args()
    build(args.require_published)
