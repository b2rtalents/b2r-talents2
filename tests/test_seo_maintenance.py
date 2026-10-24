"""Tests sans réseau du pipeline de maintenance B2R."""
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / 'scripts/seo_maintenance.py'
OLD_SLUG = 'lessh1greaterneurodiversite-en-entreprise-avant-dinclure-encore-faut-il-comprendrelessh1greater'
NEW_SLUG = 'neurodiversite-en-entreprise-avant-dinclure-encore-faut-il-comprendre'


class SEOMaintenanceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / 'scripts').mkdir()
        shutil.copy2(SCRIPT, self.root / 'scripts/seo_maintenance.py')
        self.make('CNAME', 'b2r-talents.fr\n')
        self.make('index.html', '<html><head><link rel="canonical" href="https://www.b2r-talents.fr/"></head><body><a href="/atelier-cadres/">Atelier</a></body></html>')
        self.make('atelier-cadres/index.html', '<html><head><link rel="canonical" href="https://www.b2r-talents.fr/atelier-cadres/"></head><body></body></html>')
        self.make('cgv/index.html', '<html><head><meta name="robots" content="noindex,follow"><link rel="canonical" href="https://www.b2r-talents.fr/cgv/"></head><body></body></html>')
        self.make('reflexions/contenus/articles/2026-10-06-' + OLD_SLUG + '.md', 'Article source\n')
        self.make('scripts/generate_reflexions.py', '''from pathlib import Path
import shutil
SITE = "https://www.b2r-talents.fr"
r=Path(__file__).resolve().parents[1]
p=r/'reflexions/publications'
if p.exists(): shutil.rmtree(p)
p.mkdir(parents=True)
for f in (r/'reflexions/contenus/articles').glob('*.md'):
    slug=f.stem.split('2026-10-06-',1)[-1]
    item=p/slug/'index.html'; item.parent.mkdir(parents=True)
    item.write_text('<html><head><link rel="canonical" href="'+SITE+'/reflexions/publications/'+slug+'/"></head></html>')
''')

    def make(self, path, value):
        dest = self.root / path
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(value, encoding='utf-8')

    def cmd(self, *args):
        return subprocess.run([sys.executable, 'scripts/seo_maintenance.py', *args], cwd=self.root,
                              capture_output=True, text=True)

    def test_migrate_check_and_preserve_noindex(self):
        result = self.cmd('--apply', '--regenerate')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse((self.root / ('reflexions/contenus/articles/2026-10-06-' + OLD_SLUG + '.md')).exists())
        self.assertTrue((self.root / 'reflexions/publications' / NEW_SLUG / 'index.html').exists())
        self.assertEqual(self.cmd('--check').returncode, 0)
        sitemap = (self.root / 'sitemap.xml').read_text()
        self.assertIn('/atelier-cadres/', sitemap)
        self.assertNotIn('/cgv/', sitemap)
        self.assertNotIn(OLD_SLUG, sitemap)
        self.assertIn(NEW_SLUG, sitemap)
        self.assertEqual(self.cmd('--apply', '--regenerate').returncode, 0)
        self.assertEqual(self.cmd('--check').returncode, 0)

    def test_broken_link_is_rejected(self):
        self.assertEqual(self.cmd('--apply', '--regenerate').returncode, 0)
        page = self.root / 'index.html'
        page.write_text(page.read_text() + '<a href="/inexistant/">Cassé</a>')
        result = self.cmd('--check')
        self.assertEqual(result.returncode, 1)
        self.assertIn('Lien interne absent', result.stderr)

    def test_migration_without_regeneration_is_blocked(self):
        result = self.cmd('--apply')
        self.assertEqual(result.returncode, 2)
        self.assertTrue((self.root / ('reflexions/contenus/articles/2026-10-06-' + OLD_SLUG + '.md')).exists())


if __name__ == '__main__':
    unittest.main()
