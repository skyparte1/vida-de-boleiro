const country = document.querySelector('#country');
if (country) {
  const clubBox = document.querySelector('#club-box');
  const options = document.querySelector('#club-options');
  const note = document.querySelector('#league-note');
  const startButton = document.querySelector('#start-button');
  country.addEventListener('change', async () => {
    options.innerHTML = '';
    startButton.disabled = true;
    if (!country.value) return clubBox.hidden = true;
    const response = await fetch('/api/starting-clubs', {method:'POST', headers:{'Content-Type':'application/x-www-form-urlencoded'}, body:new URLSearchParams({country:country.value})});
    const data = await response.json();
    note.textContent = data.clubs[0].league_country === country.value ? `Liga disponível: ${country.value}` : `Sem liga disponível: usando a liga mais próxima, ${data.clubs[0].league_country}`;
    data.clubs.forEach((club, index) => {
      options.insertAdjacentHTML('beforeend', `<label class="club-choice"><input type="radio" name="club" value="${club.name}" ${index === 0 ? 'checked' : ''}> ${club.name} <small>· clube ${club.size === 'small' ? 'de menor expressão' : club.size === 'medium' ? 'médio' : 'grande'}</small></label>`);
    });
    clubBox.hidden = false;
    startButton.disabled = false;
  });
}
