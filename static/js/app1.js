const country = document.querySelector('#country');
const careerForm = document.querySelector('#career-form');

const setPreview = (selector, value, fallback) => {
  const element = document.querySelector(selector);
  if (element) element.textContent = value || fallback;
};

if (country) {
  const clubBox = document.querySelector('#club-box');
  const options = document.querySelector('#club-options');
  const note = document.querySelector('#league-note');
  const startButton = document.querySelector('#start-button');
  country.addEventListener('change', async () => {
    options.innerHTML = '';
    startButton.disabled = true;
    setPreview('#preview-country', country.value, '—');
    if (!country.value) { clubBox.hidden = true; return; }
    try {
      const response = await fetch('/api/starting-clubs', {method:'POST', headers:{'Content-Type':'application/x-www-form-urlencoded'}, body:new URLSearchParams({country:country.value})});
      if (!response.ok) throw new Error('Não foi possível carregar os clubes.');
      const data = await response.json();
      note.textContent = `Liga inicial usada pelo jogo: ${data.clubs[0].league_country}`;
      data.clubs.forEach((club, index) => {
        const tier = club.size === 'small' ? 'clube de menor expressão' : club.size === 'medium' ? 'clube médio' : 'clube grande';
        options.insertAdjacentHTML('beforeend', `<label class="club-choice"><input type="radio" name="club" value="${club.name}" ${index === 0 ? 'checked' : ''}> <strong>${club.name}</strong><small>${tier}</small></label>`);
      });
      clubBox.hidden = false;
      startButton.disabled = false;
    } catch (error) {
      note.textContent = 'Não foi possível carregar os clubes. Tente novamente.';
      clubBox.hidden = false;
    }
  });
}

const positionInput = document.querySelector('#position');
if (positionInput) {
  const feedback = document.querySelector('#position-feedback');
  document.querySelectorAll('.position-button').forEach((button) => button.addEventListener('click', () => {
    document.querySelectorAll('.position-button').forEach((item) => item.classList.remove('selected'));
    button.classList.add('selected');
    positionInput.value = button.dataset.position;
    feedback.textContent = `Posição selecionada: ${button.dataset.position}.`;
    setPreview('#preview-position', button.dataset.position, 'Posição a definir');
  }));
}

const nameInput = document.querySelector('#player-name');
if (nameInput) nameInput.addEventListener('input', () => setPreview('#preview-name', nameInput.value, 'Novo talento'));

document.querySelectorAll('input[name="dominant_foot"]').forEach((input) => input.addEventListener('change', () => setPreview('#preview-foot', input.value, 'Direita')));

if (careerForm) careerForm.addEventListener('submit', (event) => {
  if (positionInput && !positionInput.value) {
    event.preventDefault();
    document.querySelector('#position-feedback').textContent = 'Escolha uma posição no campo para continuar.';
    return;
  }
  const submit = careerForm.querySelector('button[type="submit"], #start-button');
  if (submit) { submit.classList.add('is-loading'); submit.disabled = true; submit.querySelector('span')?.replaceChildren('Preparando carreira...'); }
});

document.querySelectorAll('form:not(#career-form)').forEach((form) => form.addEventListener('submit', () => {
  const button = form.querySelector('button');
  if (button) { button.classList.add('is-loading'); button.disabled = true; }
}));
