const labels = {
  power: 'Power',
  input: 'Input',
  mute: 'Mute',
  1: '1', 2: '2', 3: '3',
  4: '4', 5: '5', 6: '6',
  7: '7', 8: '8', 9: '9',
  0: '0',
  'prev-ch': 'Prev Channel',
  guide: 'Guide',
  'vol-up': 'Volume Up',
  'vol-down': 'Volume Down',
  'ch-up': 'Channel Up',
  'ch-down': 'Channel Down',
  up: 'Up',
  down: 'Down',
  left: 'Left',
  right: 'Right',
  ok: 'OK',
  menu: 'Menu',
  home: 'Home',
  back: 'Back',
  rewind: 'Rewind',
  'play-pause': 'Play / Pause',
  'fast-forward': 'Fast Forward',
  red: 'Red',
  green: 'Green',
  yellow: 'Yellow',
  'blue-btn': 'Blue',
};

const feedback = document.getElementById('feedback');
let clearTimer;

function press(action) {
  const label = labels[action] || action;
  feedback.textContent = label;
  feedback.style.opacity = '1';
  clearTimeout(clearTimer);
  clearTimer = setTimeout(() => { feedback.style.opacity = '0'; }, 1200);

  if (navigator.vibrate) navigator.vibrate(30);
}

document.querySelectorAll('[data-action]').forEach(btn => {
  btn.addEventListener('click', () => press(btn.dataset.action));
});
