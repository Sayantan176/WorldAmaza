// WorldAmaze Minimal Client Helpers

function fillPrompt(text) {
  const composer = document.getElementById("promptComposer");
  if (composer) {
    composer.value = text;
    composer.focus();
    composer.scrollIntoView({ behavior: 'smooth', block: 'center' });
  }
}

function openModal(modalId) {
  const el = document.getElementById(modalId);
  if (el) el.classList.remove('hidden');
}

function closeModal(modalId) {
  const el = document.getElementById(modalId);
  if (el) el.classList.add('hidden');
}

// Global key shortcut: Esc closes any open modal
document.addEventListener('keydown', (e) => {
  if (e.key === 'Escape') {
    document.querySelectorAll('.modal-backdrop').forEach(el => el.classList.add('hidden'));
  }
});
