const country = document.querySelector('#country');
const careerForm = document.querySelector('#career-form');

const setPreview = (selector, value, fallback) => {
  const element = document.querySelector(selector);
  if (element) element.textContent = value || fallback;
};

// =========================================================
// Seletor de países — bandeiras locais + nomes em português
// =========================================================
const COUNTRY_ISO = {
  "Algeria": "dz",
  "Angola": "ao",
  "Benin": "bj",
  "Botswana": "bw",
  "Burkina Faso": "bf",
  "Burundi": "bi",
  "Cabo Verde": "cv",
  "Cameroon": "cm",
  "Central African Republic": "cf",
  "Chad": "td",
  "Comoros": "km",
  "Congo": "cg",
  "Congo DR": "cd",
  "Cote d'Ivoire": "ci",
  "Djibouti": "dj",
  "Egypt": "eg",
  "Equatorial Guinea": "gq",
  "Eritrea": "er",
  "Eswatini": "sz",
  "Ethiopia": "et",
  "Gabon": "ga",
  "The Gambia": "gm",
  "Ghana": "gh",
  "Guinea": "gn",
  "Guinea-Bissau": "gw",
  "Kenya": "ke",
  "Lesotho": "ls",
  "Liberia": "lr",
  "Libya": "ly",
  "Madagascar": "mg",
  "Malawi": "mw",
  "Mali": "ml",
  "Mauritania": "mr",
  "Mauritius": "mu",
  "Morocco": "ma",
  "Mozambique": "mz",
  "Namibia": "na",
  "Niger": "ne",
  "Nigeria": "ng",
  "Rwanda": "rw",
  "Sao Tome and Principe": "st",
  "Senegal": "sn",
  "Seychelles": "sc",
  "Sierra Leone": "sl",
  "Somalia": "so",
  "South Africa": "za",
  "South Sudan": "ss",
  "Sudan": "sd",
  "Tanzania": "tz",
  "Togo": "tg",
  "Tunisia": "tn",
  "Uganda": "ug",
  "Zambia": "zm",
  "Zimbabwe": "zw",
  "Afghanistan": "af",
  "Australia": "au",
  "Bahrain": "bh",
  "Bangladesh": "bd",
  "Bhutan": "bt",
  "Brunei Darussalam": "bn",
  "Cambodia": "kh",
  "China PR": "cn",
  "Chinese Taipei": "tw",
  "Guam": "gu",
  "Hong Kong, China": "hk",
  "India": "in",
  "Indonesia": "id",
  "IR Iran": "ir",
  "Iraq": "iq",
  "Japan": "jp",
  "Jordan": "jo",
  "DPR Korea": "kp",
  "Korea Republic": "kr",
  "Kuwait": "kw",
  "Kyrgyz Republic": "kg",
  "Laos": "la",
  "Lebanon": "lb",
  "Macau": "mo",
  "Malaysia": "my",
  "Maldives": "mv",
  "Mongolia": "mn",
  "Myanmar": "mm",
  "Nepal": "np",
  "Oman": "om",
  "Pakistan": "pk",
  "Palestine": "ps",
  "Philippines": "ph",
  "Qatar": "qa",
  "Saudi Arabia": "sa",
  "Singapore": "sg",
  "Sri Lanka": "lk",
  "Syria": "sy",
  "Tajikistan": "tj",
  "Thailand": "th",
  "Timor-Leste": "tl",
  "Turkmenistan": "tm",
  "United Arab Emirates": "ae",
  "Uzbekistan": "uz",
  "Vietnam": "vn",
  "Yemen": "ye",
  "Albania": "al",
  "Andorra": "ad",
  "Armenia": "am",
  "Austria": "at",
  "Azerbaijan": "az",
  "Belarus": "by",
  "Belgium": "be",
  "Bosnia and Herzegovina": "ba",
  "Bulgaria": "bg",
  "Croatia": "hr",
  "Cyprus": "cy",
  "Czechia": "cz",
  "Denmark": "dk",
  "England": "gb-eng",
  "Estonia": "ee",
  "Faroe Islands": "fo",
  "Finland": "fi",
  "France": "fr",
  "Georgia": "ge",
  "Germany": "de",
  "Gibraltar": "gi",
  "Greece": "gr",
  "Hungary": "hu",
  "Iceland": "is",
  "Israel": "il",
  "Italy": "it",
  "Kazakhstan": "kz",
  "Kosovo": "xk",
  "Latvia": "lv",
  "Liechtenstein": "li",
  "Lithuania": "lt",
  "Luxembourg": "lu",
  "Malta": "mt",
  "Moldova": "md",
  "Montenegro": "me",
  "Netherlands": "nl",
  "North Macedonia": "mk",
  "Northern Ireland": "gb-nir",
  "Norway": "no",
  "Poland": "pl",
  "Portugal": "pt",
  "Republic of Ireland": "ie",
  "Romania": "ro",
  "Russia": "ru",
  "San Marino": "sm",
  "Scotland": "gb-sct",
  "Serbia": "rs",
  "Slovakia": "sk",
  "Slovenia": "si",
  "Spain": "es",
  "Sweden": "se",
  "Switzerland": "ch",
  "Türkiye": "tr",
  "Ukraine": "ua",
  "Wales": "gb-wls",
  "Anguilla": "ai",
  "Antigua and Barbuda": "ag",
  "Aruba": "aw",
  "Bahamas": "bs",
  "Barbados": "bb",
  "Belize": "bz",
  "Bermuda": "bm",
  "British Virgin Islands": "vg",
  "Canada": "ca",
  "Cayman Islands": "ky",
  "Costa Rica": "cr",
  "Cuba": "cu",
  "Curacao": "cw",
  "Dominica": "dm",
  "Dominican Republic": "do",
  "El Salvador": "sv",
  "Grenada": "gd",
  "Guatemala": "gt",
  "Guyana": "gy",
  "Haiti": "ht",
  "Honduras": "hn",
  "Jamaica": "jm",
  "Mexico": "mx",
  "Montserrat": "ms",
  "Nicaragua": "ni",
  "Panama": "pa",
  "Puerto Rico": "pr",
  "St Kitts and Nevis": "kn",
  "St Lucia": "lc",
  "St Vincent and the Grenadines": "vc",
  "Suriname": "sr",
  "Trinidad and Tobago": "tt",
  "Turks and Caicos Islands": "tc",
  "US Virgin Islands": "vi",
  "USA": "us",
  "Argentina": "ar",
  "Bolivia": "bo",
  "Brazil": "br",
  "Chile": "cl",
  "Colombia": "co",
  "Ecuador": "ec",
  "Paraguay": "py",
  "Peru": "pe",
  "Uruguay": "uy",
  "Venezuela": "ve",
  "American Samoa": "as",
  "Cook Islands": "ck",
  "Fiji": "fj",
  "New Caledonia": "nc",
  "New Zealand": "nz",
  "Papua New Guinea": "pg",
  "Samoa": "ws",
  "Solomon Islands": "sb",
  "Tahiti": "pf",
  "Tonga": "to",
  "Vanuatu": "vu"
};
const COUNTRY_SPECIAL_NAMES = {
  "England": "Inglaterra",
  "Scotland": "Escócia",
  "Wales": "País de Gales",
  "Northern Ireland": "Irlanda do Norte",
  "USA": "Estados Unidos",
  "IR Iran": "Irã",
  "DPR Korea": "Coreia do Norte",
  "Korea Republic": "Coreia do Sul",
  "China PR": "China",
  "Cote d'Ivoire": "Costa do Marfim",
  "The Gambia": "Gâmbia",
  "Sao Tome and Principe": "São Tomé e Príncipe",
  "Cabo Verde": "Cabo Verde",
  "Türkiye": "Turquia",
  "Curacao": "Curaçao",
  "St Kitts and Nevis": "São Cristóvão e Névis",
  "St Lucia": "Santa Lúcia",
  "St Vincent and the Grenadines": "São Vicente e Granadinas",
  "Laos": "Laos",
  "Vietnam": "Vietnã",
  "Brunei Darussalam": "Brunei",
  "Chinese Taipei": "Taipé Chinesa",
  "Hong Kong, China": "Hong Kong",
  "Macau": "Macau",
  "Republic of Ireland": "Irlanda",
  "North Macedonia": "Macedônia do Norte",
  "Czechia": "Tchéquia",
  "Eswatini": "Essuatíni"
};

const countryDisplayName = (name) => {
  if (COUNTRY_SPECIAL_NAMES[name]) return COUNTRY_SPECIAL_NAMES[name];
  const iso = COUNTRY_ISO[name];
  if (iso && typeof Intl !== 'undefined' && Intl.DisplayNames) {
    try {
      const displayNames = new Intl.DisplayNames(['pt-BR'], { type: 'region' });
      return displayNames.of(iso.toUpperCase()) || name;
    } catch (_) {}
  }
  return name;
};

const normalizeText = (value) => String(value || '')
  .normalize('NFD')
  .replace(/[\u0300-\u036f]/g, '')
  .toLowerCase();

const countryGrid = document.querySelector('#country-grid');
const countrySearch = document.querySelector('#country-search');
const countryFeedback = document.querySelector('#country-feedback');

let countryButtons = [];

if (countryGrid && country) {
  countryButtons = Array.from(countryGrid.querySelectorAll('.country-option'));

  countryButtons.forEach((button) => {
    const internalName = button.dataset.country;
    const displayName = countryDisplayName(internalName);
    const iso = COUNTRY_ISO[internalName];
    const flag = button.querySelector('.country-flag');
    const name = button.querySelector('.country-name');

    if (name) name.textContent = displayName;
    if (flag && iso) flag.className = `country-flag fi fi-${iso}`;
    button.dataset.search = normalizeText(`${displayName} ${internalName}`);
  });

  // Ordena os cards pelo nome exibido em português.
  countryButtons.sort((a, b) => {
    const aName = a.querySelector('.country-name')?.textContent || '';
    const bName = b.querySelector('.country-name')?.textContent || '';
    return aName.localeCompare(bName, 'pt-BR');
  });
  countryButtons.forEach((button) => countryGrid.appendChild(button));

  const loadStartingClubs = async (selectedCountry) => {
    const clubBox = document.querySelector('#club-box');
    const options = document.querySelector('#club-options');
    const note = document.querySelector('#league-note');
    const startButton = document.querySelector('#start-button');

    options.innerHTML = '';
    startButton.disabled = true;
    setPreview('#preview-country', countryDisplayName(selectedCountry), '—');

    if (!selectedCountry) {
      clubBox.hidden = true;
      return;
    }

    try {
      const response = await fetch('/api/starting-clubs', {
        method: 'POST',
        headers: {'Content-Type': 'application/x-www-form-urlencoded'},
        body: new URLSearchParams({country: selectedCountry})
      });
      if (!response.ok) throw new Error('Não foi possível carregar os clubes.');
      const data = await response.json();
      if (!data.clubs.length) {
        note.textContent = data.message || 'Ainda não há clubes cadastrados para este país.';
        clubBox.hidden = false;
        return;
      }
      note.textContent = `Liga inicial usada pelo jogo: ${data.clubs[0].league_country}`;
      data.clubs.forEach((club, index) => {
        const tier = club.size === 'small' ? 'clube de menor expressão' : club.size === 'medium' ? 'clube médio' : 'clube grande';
        const initials = club.name.split(/\s+/).map((word) => word[0]).join('').slice(0, 3).toUpperCase();
        const crest = club.logo_url
          ? `<img class="club-choice__logo" src="${club.logo_url}" alt="Escudo do ${club.name}" onerror="this.outerHTML='<span class=&quot;club-choice__crest&quot; aria-hidden=&quot;true&quot;>${initials}</span>'">`
          : `<span class="club-choice__crest" aria-hidden="true">${initials}</span>`;
        options.insertAdjacentHTML('beforeend', `
          <label class="club-choice${index === 0 ? ' is-selected' : ''}">
            <input class="club-choice__radio" type="radio" name="club_id" value="${club.id}" ${index === 0 ? 'checked' : ''}>
            <span class="club-choice__selected" aria-hidden="true">✓</span>
            <span class="club-choice__visual">${crest}</span>
            <span class="club-choice__content">
              <small class="club-choice__eyebrow">PRIMEIRO CONTRATO</small>
              <strong>${club.name}</strong>
              <small class="club-choice__tier">${tier}</small>
            </span>
            <span class="club-choice__cta">Selecionar <i aria-hidden="true">→</i></span>
          </label>`);
      });
      options.querySelectorAll('.club-choice__radio').forEach((radio) => {
        radio.addEventListener('change', () => {
          options.querySelectorAll('.club-choice').forEach((card) => card.classList.remove('is-selected'));
          radio.closest('.club-choice')?.classList.add('is-selected');
        });
      });
      clubBox.hidden = false;
      startButton.disabled = false;
    } catch (error) {
      note.textContent = 'Não foi possível carregar os clubes. Tente novamente.';
      clubBox.hidden = false;
    }
  };

  countryButtons.forEach((button) => button.addEventListener('click', () => {
    countryButtons.forEach((item) => item.classList.remove('selected'));
    button.classList.add('selected');

    country.value = button.dataset.country;
    const displayName = countryDisplayName(country.value);

    if (countryFeedback) {
      countryFeedback.textContent = `País selecionado: ${displayName}`;
      countryFeedback.classList.add('has-selection');
    }

    loadStartingClubs(country.value);
  }));

  if (countrySearch) {
    countrySearch.addEventListener('input', () => {
      const query = normalizeText(countrySearch.value);
      countryButtons.forEach((button) => {
        button.hidden = Boolean(query) && !button.dataset.search.includes(query);
      });
    });
  }
}

const positionInput = document.querySelector('#position');
if (positionInput) {
  const feedback = document.querySelector('#position-feedback');
  const profile = document.querySelector('#position-profile');
  document.querySelectorAll('.position-button').forEach((button) => button.addEventListener('click', () => {
    document.querySelectorAll('.position-button').forEach((item) => {
      item.classList.remove('selected', 'is-pulsing');
      item.setAttribute('aria-pressed', 'false');
    });
    button.classList.add('selected');
    window.requestAnimationFrame(() => button.classList.add('is-pulsing'));
    positionInput.value = button.dataset.position;
    button.setAttribute('aria-pressed', 'true');
    feedback.textContent = button.dataset.position;
    if (profile) profile.textContent = button.dataset.profile || 'Perfil de jogo selecionado.';
    setPreview('#preview-position', button.dataset.position, 'Posição a definir');
  }));
}

const nameInput = document.querySelector('#player-name');
if (nameInput) nameInput.addEventListener('input', () => setPreview('#preview-name', nameInput.value, 'Novo talento'));

document.querySelectorAll('input[name="dominant_foot"]').forEach((input) => input.addEventListener('change', () => setPreview('#preview-foot', input.value, 'Direita')));

if (careerForm) careerForm.addEventListener('submit', (event) => {
  if (country && !country.value) {
    event.preventDefault();
    if (countryFeedback) countryFeedback.textContent = 'Escolha um país para continuar.';
    return;
  }
  if (positionInput && !positionInput.value) {
    event.preventDefault();
    document.querySelector('#position-feedback').textContent = 'Escolha uma posição no campo para continuar.';
    return;
  }
  sessionStorage.removeItem('vdb:career-metrics');
  const submit = careerForm.querySelector('button[type="submit"], #start-button');
  if (submit) { submit.classList.add('is-loading'); submit.disabled = true; submit.querySelector('span')?.replaceChildren('Preparando carreira...'); }
});

document.querySelectorAll('form:not(#career-form)').forEach((form) => form.addEventListener('submit', (event) => {
  // Não desabilite o submitter aqui: navegadores podem excluí-lo do POST.
  // O backend protege o evento contra reenvio pelo seu identificador único.
  event.submitter?.classList.add('is-loading');
  if (form.classList.contains('event-choices')) {
    form.classList.add('is-resolving');
    event.submitter?.classList.add('is-selected');
  }
}));

const dashboard = document.querySelector('.page-career');
if (dashboard) {
  const metricKey = 'vdb:career-metrics';
  let previous = {};
  try { previous = JSON.parse(sessionStorage.getItem(metricKey) || '{}'); } catch (_) {}
  const current = {};
  document.querySelectorAll('[data-metric][data-value]').forEach((element) => {
    current[element.dataset.metric] = Number(element.dataset.value);
  });

  const formatValue = (value, format) => format === 'currency'
    ? new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'EUR', maximumFractionDigits: 0 }).format(value)
    : String(Math.round(value));
  const animateNumber = (element, target) => {
    const old = Number(previous[element.closest('[data-metric]')?.dataset.metric] ?? target);
    if (old === target) return;
    const started = performance.now();
    const duration = 360;
    const frame = (time) => {
      const progress = Math.min(1, (time - started) / duration);
      const value = old + (target - old) * (1 - (1 - progress) ** 3);
      element.textContent = formatValue(value, element.dataset.format);
      if (progress < 1) requestAnimationFrame(frame);
    };
    requestAnimationFrame(frame);
  };
  document.querySelectorAll('[data-count]').forEach((element) => {
    const target = Number(element.dataset.count);
    const metric = element.closest('[data-metric]')?.dataset.metric;
    if (metric && Object.hasOwn(previous, metric)) animateNumber(element, target);
  });
  requestAnimationFrame(() => document.querySelectorAll('.status-progress span').forEach((bar) => bar.classList.add('is-ready')));

  const labels = { form: 'Forma', fitness: 'Condicionamento', morale: 'Moral', overall: 'Overall', market_value: 'Valor de mercado' };
  if (Object.hasOwn(previous, 'overall') && previous.overall !== current.overall) {
    document.querySelector('.overall-display')?.classList.add('metric-changed');
  }
  const tags = document.querySelector('.change-tags');
  if (tags) Object.entries(current).forEach(([key, value]) => {
    if (!labels[key] || !Object.hasOwn(previous, key) || previous[key] === value) return;
    const delta = value - previous[key];
    const tag = document.createElement('span');
    tag.className = `change-tag ${delta > 0 ? 'is-positive' : 'is-negative'}`;
    const display = key === 'market_value' ? formatValue(Math.abs(delta), 'currency') : Math.abs(delta);
    tag.textContent = `${labels[key]} ${delta > 0 ? '+' : '−'}${display}`;
    tags.appendChild(tag);
  });
  sessionStorage.setItem(metricKey, JSON.stringify(current));

  // Confete sutil para eventos marcados como celebração (ex.: título). Não interfere na leitura.
  const celebration = document.querySelector('.event-card.is-celebration');
  const reduceMotion = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  if (celebration && !reduceMotion) {
    const layer = document.createElement('div');
    layer.className = 'confetti-layer';
    const colors = ['#b9ef54', '#ffc857', '#6fb9ff', '#f3f8f2'];
    for (let i = 0; i < 40; i += 1) {
      const piece = document.createElement('span');
      piece.className = 'confetti-piece';
      piece.style.left = `${Math.random() * 100}%`;
      piece.style.background = colors[i % colors.length];
      piece.style.animationDuration = `${2.2 + Math.random() * 1.4}s`;
      piece.style.animationDelay = `${Math.random() * 0.5}s`;
      layer.appendChild(piece);
    }
    document.body.appendChild(layer);
    setTimeout(() => layer.remove(), 4200);
  }

  const links = Array.from(document.querySelectorAll('.section-nav a'));
  const sections = links.map((link) => document.querySelector(link.getAttribute('href'))).filter(Boolean);
  if ('IntersectionObserver' in window && sections.length) {
    const observer = new IntersectionObserver((entries) => entries.forEach((entry) => {
      if (!entry.isIntersecting) return;
      links.forEach((link) => link.classList.toggle('is-active', link.getAttribute('href') === `#${entry.target.id}`));
    }), { rootMargin: '-25% 0px -60% 0px', threshold: 0.01 });
    sections.forEach((section) => observer.observe(section));
  }
}
