'use strict';

/**
 * Review panel markup. The extension only ever posts plain text to the webview;
 * all rendering happens client side after HTML-escaping, so note content can
 * never inject markup or script into the panel.
 */

function nonce() {
  let out = '';
  const chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789';
  for (let i = 0; i < 32; i++) out += chars[Math.floor(Math.random() * chars.length)];
  return out;
}

function html(webview) {
  const n = nonce();
  return `<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta http-equiv="Content-Security-Policy"
      content="default-src 'none'; style-src ${webview.cspSource} 'unsafe-inline'; script-src 'nonce-${n}';">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Flashcards</title>
<style>
  :root { color-scheme: light dark; }
  body {
    font-family: var(--vscode-font-family);
    font-size: var(--vscode-font-size);
    color: var(--vscode-foreground);
    background: var(--vscode-editor-background);
    margin: 0; padding: 0 1.5rem 1.5rem;
    display: flex; flex-direction: column; height: 100vh; box-sizing: border-box;
  }
  header {
    position: sticky; top: 0; padding: .75rem 0; display: flex; gap: 1rem;
    align-items: center; background: var(--vscode-editor-background);
    border-bottom: 1px solid var(--vscode-panel-border); font-size: .85em;
    color: var(--vscode-descriptionForeground);
  }
  #source {
    margin-left: auto; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
    font-family: inherit; font-size: inherit; padding: .1rem .25rem; border: none; flex: 0 1 auto;
    background: none; color: var(--vscode-textLink-foreground); cursor: pointer; border-radius: 3px;
  }
  #source:hover { text-decoration: underline; color: var(--vscode-textLink-activeForeground); }
  #source:focus-visible { outline: 1px solid var(--vscode-focusBorder); }
  #source:empty { display: none; }
  main { flex: 1; overflow-y: auto; padding-top: 1.25rem; }
  #front { font-size: 1.35em; font-weight: 600; line-height: 1.45; white-space: pre-wrap; }
  #back {
    margin-top: 1.25rem; padding-top: 1.25rem; line-height: 1.6; white-space: pre-wrap;
    border-top: 1px dashed var(--vscode-panel-border);
  }
  #back.hidden { display: none; }
  code {
    font-family: var(--vscode-editor-font-family);
    background: var(--vscode-textCodeBlock-background); padding: 0 .25em; border-radius: 3px;
  }
  .wiki { color: var(--vscode-textLink-foreground); }
  footer { padding-top: 1rem; border-top: 1px solid var(--vscode-panel-border); }
  .row { display: flex; gap: .5rem; flex-wrap: wrap; }
  button {
    flex: 1; min-width: 7rem; padding: .55rem .4rem; cursor: pointer;
    font-family: inherit; font-size: .95em; border: 1px solid var(--vscode-panel-border);
    border-radius: 4px; color: var(--vscode-button-foreground);
    background: var(--vscode-button-background);
  }
  button:hover { background: var(--vscode-button-hoverBackground); }
  button .k { opacity: .65; font-size: .85em; }
  button .iv { display: block; opacity: .7; font-size: .78em; }
  .hint { margin-top: .5rem; font-size: .8em; color: var(--vscode-descriptionForeground); }
  #done { text-align: center; padding-top: 4rem; }
  #done h2 { font-weight: 600; }
  .hidden { display: none; }
</style>
</head>
<body>
  <header>
    <span id="progress"></span>
    <button id="source" data-action="open" title="Open this note at the card's line (O)"></button>
  </header>

  <main>
    <div id="card">
      <div id="front"></div>
      <div id="back" class="hidden"></div>
    </div>
    <div id="done" class="hidden"></div>
  </main>

  <footer>
    <div class="row" id="revealRow">
      <button data-action="reveal">Show answer <span class="k">(Space)</span></button>
    </div>
    <div class="row hidden" id="gradeRow">
      <button data-grade="1">Again <span class="k">(1)</span><span class="iv" id="iv1"></span></button>
      <button data-grade="2">Hard <span class="k">(2)</span><span class="iv" id="iv2"></span></button>
      <button data-grade="3">Good <span class="k">(3)</span><span class="iv" id="iv3"></span></button>
      <button data-grade="4">Easy <span class="k">(4)</span><span class="iv" id="iv4"></span></button>
    </div>
    <div class="hint">Space / Enter reveal &middot; 1-4 grade &middot; click the file path (or O) to edit the note &middot; Esc end session</div>
  </footer>

<script nonce="${n}">
(function () {
  const vscode = acquireVsCodeApi();
  const $ = (id) => document.getElementById(id);
  let revealed = false;
  let finished = false;

  const esc = (s) => s.replace(/[&<>"']/g, (c) =>
    ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));

  // Escape first, then re-introduce a minimal, known-safe subset of inline Markdown.
  const fmt = (s) => esc(s || '')
    .replace(/\`([^\`]+)\`/g, '<code>$1</code>')
    .replace(/\\*\\*([^*]+)\\*\\*/g, '<strong>$1</strong>')
    .replace(/(^|[^*])\\*([^*\\n]+)\\*/g, '$1<em>$2</em>')
    .replace(/\\[\\[([^\\]|]+)(?:\\|([^\\]]+))?\\]\\]/g, (m, a, b) => '<span class="wiki">' + (b || a) + '</span>');

  function reveal() {
    if (revealed || finished) return;
    revealed = true;
    $('back').classList.remove('hidden');
    $('revealRow').classList.add('hidden');
    $('gradeRow').classList.remove('hidden');
  }

  function grade(n) {
    if (!revealed || finished) return;
    vscode.postMessage({ type: 'grade', grade: n });
  }

  document.addEventListener('click', (e) => {
    const btn = e.target.closest('button');
    if (!btn) return;
    if (btn.dataset.action === 'reveal') reveal();
    else if (btn.dataset.action === 'open') vscode.postMessage({ type: 'open' });
    else if (btn.dataset.grade) grade(Number(btn.dataset.grade));
  });

  document.addEventListener('keydown', (e) => {
    if (e.key === ' ' || e.key === 'Enter') { e.preventDefault(); revealed ? grade(3) : reveal(); }
    else if (e.key >= '1' && e.key <= '4') grade(Number(e.key));
    else if (e.key === 'Escape') vscode.postMessage({ type: 'quit' });
    else if (e.key === 'o' || e.key === 'O') vscode.postMessage({ type: 'open' });
  });

  window.addEventListener('message', (event) => {
    const msg = event.data;
    if (msg.type === 'card') {
      finished = false;
      revealed = false;
      $('card').classList.remove('hidden');
      $('done').classList.add('hidden');
      $('front').innerHTML = fmt(msg.front);
      $('back').innerHTML = fmt(msg.back) || '<em>(no answer text)</em>';
      $('back').classList.add('hidden');
      $('revealRow').classList.remove('hidden');
      $('gradeRow').classList.add('hidden');
      $('progress').textContent = msg.progress;
      $('source').textContent = msg.source;
      for (const [i, key] of ['again', 'hard', 'good', 'easy'].entries()) {
        $('iv' + (i + 1)).textContent = msg.previews[key];
      }
      window.scrollTo(0, 0);
    } else if (msg.type === 'done') {
      finished = true;
      $('card').classList.add('hidden');
      $('done').classList.remove('hidden');
      $('done').innerHTML = '<h2>' + esc(msg.title) + '</h2><p>' + esc(msg.summary) + '</p>';
      $('revealRow').classList.add('hidden');
      $('gradeRow').classList.add('hidden');
      $('progress').textContent = '';
      $('source').textContent = '';
    }
  });

  vscode.postMessage({ type: 'ready' });
}());
</script>
</body>
</html>`;
}

module.exports = { html };
