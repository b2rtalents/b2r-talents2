(() => {
  const esc = (s = '') =>
    String(s).replace(/[&<>"']/g, c => ({
      '&': '&amp;',
      '<': '&lt;',
      '>': '&gt;',
      '"': '&quot;',
      "'": '&#039;'
    }[c]));

  const normalize = s => String(s || '').replace(/\s+/g, ' ').trim();

  const fmt = s => {
    if (!s) return '';
    const d = new Date(s + 'T12:00:00');
    return Number.isNaN(d.getTime())
      ? s
      : d.toLocaleDateString('fr-FR', {
          day: '2-digit',
          month: 'long',
          year: 'numeric'
        });
  };

  const desc = (a, b) =>
    String(b.date || '').localeCompare(String(a.date || ''));

  const excerpt = (s, max = 300) => {
    const text = normalize(s);
    if (text.length <= max) return text;
    const cut = text.slice(0, max);
    const lastSpace = cut.lastIndexOf(' ');
    return (lastSpace > 180 ? cut.slice(0, lastSpace) : cut).trim() + '…';
  };

  /*
   * Correspondance CMS -> affichage public.
   * Référence demandée :
   * - Recrutement -> Recrutement
   * - Parcours professionnels -> RH & Parcours pro
   * - Neurodiversité -> Neurodiversité
   * - Gestion -> Management
   * - Défense et Industrie -> Défense & Industrie
   */
  const publicCategory = value => {
    const v = normalize(value);
    const map = {
      'Recrutement': 'Recrutement',
      'Parcours professionnels': 'RH & Parcours pro',
      'Trajectoires professionnelles': 'RH & Parcours pro', /* compatibilité ancien contenu */
      'Neurodiversité': 'Neurodiversité',
      'Gestion': 'Management',
      'Management': 'Management',
      'Défense et Industrie': 'Défense & Industrie',
      'Défense & Industrie': 'Défense & Industrie'
    };
    return map[v] || v;
  };

  const FILTERS = [
    ['Tous', 'Tous'],
    ['Réflexion B2R', 'Réflexions B2R'],
    ['À lire', 'À lire'],
    ['Vidéo', 'Vidéos'],
    ['Recrutement', 'Recrutement'],
    ['RH & Parcours pro', 'RH & Parcours pro'],
    ['Neurodiversité', 'Neurodiversité'],
    ['Management', 'Management'],
    ['Défense & Industrie', 'Défense & Industrie']
  ];

  const rebuildFilters = () => {
    const nav = document.querySelector('.r-filters');
    if (!nav) return;
    nav.innerHTML = FILTERS.map(([value, label], index) =>
      `<button class="r-filter${index === 0 ? ' active' : ''}" data-filter="${esc(value)}" type="button">${esc(label)}</button>`
    ).join('');
  };

  const action = i => {
    if (!i.url) return '';
    const t =
      i.type === 'Vidéo'
        ? 'Voir la vidéo'
        : i.type === 'À lire'
          ? 'Lire la source'
          : 'Lire';

    const ext = /^https?:\/\//i.test(i.url);

    return `<a class="r-card-link" href="${esc(i.url)}"${
      ext ? ' target="_blank" rel="noopener noreferrer"' : ''
    }>${t} →</a>`;
  };

  const absoluteUrl = i => {
    if (!i.url) return '';
    try {
      return new URL(i.url, window.location.href).href;
    } catch {
      return i.url;
    }
  };

  const shareButton = i => {
    const url = absoluteUrl(i);
    if (!url) return '';
    return `<button type="button" class="r-card-share" data-share-url="${esc(url)}" data-share-title="${esc(i.titre || 'B2R TALENTS')}">Partager</button>`;
  };

  const regardBlock = (text, mobile = false) => {
    const full = normalize(text);
    if (!full) return '';

    const short = excerpt(full, mobile ? 210 : 245);
    const expandable = short !== full;
    const cls = mobile ? 'r-mobile-regard' : 'r-card-regard';

    return `<div class="r-regard-wrap">
      <p class="${cls}"><strong>Mon regard.</strong>
        <span class="r-regard-short">${esc(short)}</span>
        <span class="r-regard-full" hidden>${esc(full)}</span>
      </p>
      ${expandable ? `<button type="button" class="r-regard-toggle" aria-expanded="false">Lire mon regard</button>` : ''}
    </div>`;
  };

  const card = i => {
    const cat = publicCategory(i.categorie || '');
    return `<article class="r-card" data-type="${esc(i.type || 'Réflexion')}" data-cat="${esc(cat)}">
      ${i.image ? `<div class="r-card-image"><img src="${esc(i.image)}" alt=""></div>` : ''}
      <div class="r-card-body">
        <div class="r-card-meta">
          <span>${esc(i.type || 'Réflexion')}</span>
          ${cat ? `<span>${esc(cat)}</span>` : ''}
          ${i.date ? `<time datetime="${esc(i.date)}">${esc(fmt(i.date))}</time>` : ''}
        </div>
        <h3>${esc(i.titre || 'Sans titre')}</h3>
        <p class="r-card-summary">${esc(i.resume || '')}</p>
        ${regardBlock(i.mon_regard, false)}
        <div class="r-card-foot">
          ${i.source ? `<span class="r-card-source">${esc(i.source)}</span>` : ''}
          <div class="r-card-actions">
            ${shareButton(i)}
            ${action(i)}
          </div>
        </div>
      </div>
    </article>`;
  };

  const mobile = i => {
    const cat = publicCategory(i.categorie || '');
    return `<article class="m-card">
      <div class="r-mobile-meta">
        ${esc(i.type || 'Réflexion')}${cat ? ' · ' + esc(cat) : ''}
      </div>
      <h3>${esc(i.titre || 'Sans titre')}</h3>
      <p class="r-mobile-summary">${esc(i.resume || '')}</p>
      ${regardBlock(i.mon_regard, true)}
      <div class="r-mobile-actions">
        ${shareButton(i)}
        ${action(i)}
      </div>
    </article>`;
  };

  const archives = (items, isMobile = false) =>
    [...new Set(items.map(i => (i.date || '').slice(0, 4) || 'Sans date'))]
      .sort((a, b) => b.localeCompare(a))
      .map(y => {
        const a = items
          .filter(i => ((i.date || '').slice(0, 4) || 'Sans date') === y)
          .sort(desc);

        return `<section class="r-archive-year">
          <h3>${esc(y)}</h3>
          <div class="${isMobile ? 'm-cards' : 'r-grid'}">
            ${a.map(isMobile ? mobile : card).join('')}
          </div>
        </section>`;
      })
      .join('');

  function render(items) {
    const pub = items
      .filter(i => (i.statut || 'publie') === 'publie')
      .sort(desc);

    const arc = items
      .filter(i => i.statut === 'archive')
      .sort(desc);

    const d = document.getElementById('reflexions-live-grid');
    const m = document.getElementById('reflexions-mobile-cards');

    if (d) {
      d.innerHTML =
        pub.map(card).join('') ||
        '<p class="r-empty-state">Les premiers contenus arrivent bientôt.</p>';
    }

    if (m) {
      m.innerHTML =
        pub.map(mobile).join('') ||
        '<p class="r-empty-state">Les premiers contenus arrivent bientôt.</p>';
    }

    const c = document.getElementById('reflexions-count');
    if (c) c.textContent = `${pub.length} contenu${pub.length > 1 ? 's' : ''}`;

    const bd = document.getElementById('archive-toggle');
    const bm = document.getElementById('archive-toggle-mobile');
    const ad = document.getElementById('reflexions-archives');
    const am = document.getElementById('reflexions-mobile-archives');

    [bd, bm].forEach(b => {
      if (!b) return;
      b.hidden = !arc.length;
      b.textContent = `Voir les archives (${arc.length})`;
      b.setAttribute('aria-expanded', 'false');
    });

    if (ad) ad.innerHTML = arc.length ? archives(arc, false) : '';
    if (am) am.innerHTML = arc.length ? archives(arc, true) : '';
  }

  function filter(v) {
    document
      .querySelectorAll('#reflexions-live-grid .r-card')
      .forEach(el => {
        el.hidden = !(
          v === 'Tous' ||
          el.dataset.type === v ||
          el.dataset.cat === v
        );
      });

    document
      .querySelectorAll('.r-filter')
      .forEach(b =>
        b.classList.toggle('active', b.dataset.filter === v)
      );
  }

  function toggle(btn, id) {
    const t = document.getElementById(id);
    if (!t) return;

    const open = t.hidden;
    t.hidden = !open;
    btn.setAttribute('aria-expanded', String(open));

    btn.textContent =
      (open ? 'Masquer les archives' : 'Voir les archives') +
      btn.textContent.replace(/^.*?(\(\d+\))$/, ' $1');

    if (open) {
      t.scrollIntoView({
        behavior: 'smooth',
        block: 'start'
      });
    }
  }

  rebuildFilters();

  fetch('contenus.json', { cache: 'no-store' })
    .then(r => {
      if (!r.ok) throw new Error('HTTP ' + r.status);
      return r.json();
    })
    .then(items => {
      render(items);
      filter('Tous');
    })
    .catch(err => {
      console.error(err);

      const msg =
        '<p class="r-error">Impossible de charger les contenus pour le moment.</p>';

      const d = document.getElementById('reflexions-live-grid');
      if (d) d.innerHTML = msg;

      const m = document.getElementById('reflexions-mobile-cards');
      if (m) m.innerHTML = msg;
    });

  document.addEventListener('click', async e => {
    const regardToggle = e.target.closest('.r-regard-toggle');
    if (regardToggle) {
      e.preventDefault();
      const wrap = regardToggle.closest('.r-regard-wrap');
      if (!wrap) return;

      const short = wrap.querySelector('.r-regard-short');
      const full = wrap.querySelector('.r-regard-full');
      const open = regardToggle.getAttribute('aria-expanded') === 'true';

      if (short) short.hidden = !open;
      if (full) full.hidden = open;
      regardToggle.setAttribute('aria-expanded', String(!open));
      regardToggle.textContent = open ? 'Lire mon regard' : 'Réduire';
      return;
    }

    const share = e.target.closest('.r-card-share');
    if (share) {
      e.preventDefault();

      const data = {
        title: share.dataset.shareTitle || 'B2R TALENTS',
        url: share.dataset.shareUrl || window.location.href
      };

      try {
        if (navigator.share) {
          await navigator.share(data);
        } else if (navigator.clipboard && window.isSecureContext) {
          await navigator.clipboard.writeText(data.url);
          const previous = share.textContent;
          share.textContent = 'Lien copié ✓';
          window.setTimeout(() => {
            share.textContent = previous;
          }, 1800);
        } else {
          window.prompt('Copiez ce lien :', data.url);
        }
      } catch (err) {
        if (err && err.name !== 'AbortError') {
          try {
            await navigator.clipboard.writeText(data.url);
          } catch {
            window.prompt('Copiez ce lien :', data.url);
          }
        }
      }
      return;
    }

    const f = e.target.closest('.r-filter');
    if (f) {
      e.preventDefault();
      filter(f.dataset.filter);
      return;
    }

    const a = e.target.closest('#archive-toggle');
    if (a) {
      e.preventDefault();
      toggle(a, 'reflexions-archives');
      return;
    }

    const am = e.target.closest('#archive-toggle-mobile');
    if (am) {
      e.preventDefault();
      toggle(am, 'reflexions-mobile-archives');
    }
  });
})();
