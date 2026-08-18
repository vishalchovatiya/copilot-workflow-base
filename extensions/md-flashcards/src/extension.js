'use strict';

const vscode = require('vscode');
const fs = require('fs');
const path = require('path');

const { parse, cardsInSection } = require('./parser');
const scheduler = require('./scheduler');
const store = require('./store');
const webview = require('./webview');

const RELEARN_GAP = 4; // how many cards later an unlearned card comes back in the same session
const GRADE_ORDER = ['again', 'hard', 'good', 'easy'];

function config() {
  return vscode.workspace.getConfiguration('mdFlashcards');
}

/** Lowest grade that retires a card for the session; anything below it is re-queued. */
function repeatThreshold() {
  const index = GRADE_ORDER.indexOf(config().get('repeatUntilGrade') || 'good');
  return index < 0 ? scheduler.GRADES.good : index + 1;
}

function resolveUri(uri) {
  if (uri && uri.scheme === 'file') return uri;
  const editor = vscode.window.activeTextEditor;
  if (editor && editor.document.languageId === 'markdown') return editor.document.uri;
  return undefined;
}

function stateFileFor(uri) {
  const folder = vscode.workspace.getWorkspaceFolder(uri);
  const root = folder ? folder.uri.fsPath : path.dirname(uri.fsPath);
  return { root, file: path.join(root, config().get('stateFile') || '.flashcards/state.json') };
}

function relative(root, fsPath) {
  return path.relative(root, fsPath).split(path.sep).join('/');
}

/**
 * Re-read the note on every call - the unsaved editor buffer when one is dirty,
 * otherwise the bytes on disk. Nothing is cached anywhere, so an edit is visible in
 * the very next session (and a file changed by git/sync outside VS Code is too).
 */
function readCards(uri, root) {
  const open = vscode.workspace.textDocuments.find((d) => d.uri.fsPath === uri.fsPath);
  const text = open && open.isDirty ? open.getText() : fs.readFileSync(uri.fsPath, 'utf8');
  return parse(text, relative(root, uri.fsPath));
}

// Fisher-Yates: every permutation equally likely, unlike the `sort(() => Math.random() - .5)`
// idiom, which is biased and leaves cards near their original neighbours.
function shuffle(items) {
  const out = items.slice();
  for (let i = out.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [out[i], out[j]] = [out[j], out[i]];
  }
  return out;
}

/** Whole deck, never truncated: due and never-seen cards first, then the ones scheduled ahead. */
function orderDeck(cards, state) {
  const due = [];
  const later = [];
  for (const card of cards) (scheduler.isDue(state.cards[card.id]) ? due : later).push(card);
  return [...shuffle(due), ...shuffle(later)];
}

/** Workspace-wide sweep: due and never-seen cards only, capped by `sessionLimit`. */
function orderDue(cards, state) {
  const limit = config().get('sessionLimit') || 0;
  const due = shuffle(cards.filter((c) => scheduler.isDue(state.cards[c.id])));
  return limit > 0 ? due.slice(0, limit) : due;
}

class Session {
  constructor(context, queue, stateFile, state, title, root) {
    this.queue = queue;
    this.stateFile = stateFile;
    this.state = state;
    this.root = root;
    this.total = queue.length;
    this.reviews = 0;
    this.repeats = 0;
    this.index = 0;

    this.panel = vscode.window.createWebviewPanel(
      'mdFlashcards.review',
      `Flashcards - ${title}`,
      { viewColumn: vscode.ViewColumn.Beside, preserveFocus: false },
      { enableScripts: true, localResourceRoots: [], retainContextWhenHidden: true },
    );
    this.panel.webview.html = webview.html(this.panel.webview);
    this.panel.webview.onDidReceiveMessage((m) => this.onMessage(m), null, context.subscriptions);
    this.panel.onDidDispose(() => { this.queue = []; }, null, context.subscriptions);
  }

  get current() {
    return this.queue[this.index];
  }

  onMessage(msg) {
    if (msg.type === 'ready') this.show();
    else if (msg.type === 'grade') this.grade(msg.grade);
    else if (msg.type === 'open') this.openNote().catch((err) => vscode.window.showWarningMessage(`Cannot open note: ${err.message}`));
  }

  show() {
    const card = this.current;
    if (!card) {
      this.panel.webview.postMessage({
        type: 'done',
        title: this.total ? 'Session complete' : 'Nothing to review',
        summary: this.total
          ? `${this.total} card(s), ${this.reviews} review(s), ${this.repeats} repeat(s). State saved to ${relative(this.root, this.stateFile)}.`
          : 'No cards matched this selection.',
      });
      return;
    }
    this.panel.webview.postMessage({
      type: 'card',
      front: card.front,
      back: card.back,
      source: `${card.file}:${card.line + 1}`,
      progress: `${this.index + 1} / ${this.queue.length}`,
      previews: scheduler.previews(this.state.cards[card.id]),
    });
  }

  grade(grade) {
    const card = this.current;
    if (!card) return;

    const next = scheduler.review(this.state.cards[card.id], grade);
    this.state.cards[card.id] = store.entry(card, next);
    store.save(this.stateFile, this.state);

    this.reviews++;
    if (grade < repeatThreshold()) {
      this.repeats++;
      // Keep the card in rotation until it is answered well enough to retire for today.
      const at = Math.min(this.index + RELEARN_GAP, this.queue.length);
      this.queue.splice(at, 0, card);
    }
    this.index++;
    this.show();
  }

  async openNote() {
    const card = this.current;
    if (!card) return;
    const uri = vscode.Uri.file(path.join(this.root, card.file));
    // Open beside the panel, never on top of it, so the session stays visible.
    const column = this.panel.viewColumn === vscode.ViewColumn.One
      ? vscode.ViewColumn.Two
      : vscode.ViewColumn.One;
    const editor = await vscode.window.showTextDocument(uri, { viewColumn: column, preview: false });
    const pos = new vscode.Position(card.line, 0);
    editor.selection = new vscode.Selection(pos, pos);
    editor.revealRange(new vscode.Range(pos, pos), vscode.TextEditorRevealType.InCenter);
  }
}

async function startSession(context, cards, uri, title, queueFor) {
  const { root, file } = stateFileFor(uri);
  if (cards.length === 0) {
    vscode.window.showInformationMessage('No `::` cards found in this selection.');
    return;
  }
  const state = store.load(file);
  const queue = queueFor(cards, state);
  if (queue.length === 0) {
    vscode.window.showInformationMessage(`All caught up - none of the ${cards.length} card(s) are due yet.`);
    return;
  }
  new Session(context, queue, file, state, title, root);
}

async function practiceFile(context, uri) {
  const target = resolveUri(uri);
  if (!target) return;
  const { root } = stateFileFor(target);
  const { cards } = readCards(target, root);
  await startSession(context, cards, target, path.basename(target.fsPath), orderDeck);
}

async function practiceSection(context, uri) {
  const target = resolveUri(uri);
  if (!target) return;
  const { root } = stateFileFor(target);
  const { cards, headings } = readCards(target, root);

  const withCards = headings.filter((h) => h.cards > 0);
  if (withCards.length === 0) {
    await startSession(context, cards, target, path.basename(target.fsPath), orderDeck);
    return;
  }

  const editor = vscode.window.activeTextEditor;
  const cursor = editor && editor.document.uri.fsPath === target.fsPath ? editor.selection.active.line : -1;
  const enclosing = withCards.filter((h) => h.line <= cursor).pop();

  const items = withCards.map((h) => ({
    label: `${'  '.repeat(Math.max(0, h.level - 2))}${h.title}`,
    description: `${h.cards} card${h.cards === 1 ? '' : 's'}`,
    detail: h === enclosing ? 'section at cursor' : undefined,
    heading: h,
  }));
  if (enclosing) items.unshift(items.splice(items.findIndex((i) => i.heading === enclosing), 1)[0]);

  const picked = await vscode.window.showQuickPick(items, {
    title: `Practice a section of ${path.basename(target.fsPath)}`,
    placeHolder: 'Pick the section to review',
    matchOnDescription: true,
  });
  if (!picked) return;

  await startSession(context, cardsInSection(cards, picked.heading.line), target, picked.heading.title, orderDeck);
}

async function practiceWorkspace(context) {
  const folder = vscode.workspace.workspaceFolders && vscode.workspace.workspaceFolders[0];
  if (!folder) {
    vscode.window.showWarningMessage('Open a folder to review cards across the whole workspace.');
    return;
  }
  const patterns = config().get('exclude') || [];
  const exclude = patterns.length ? `{${patterns.join(',')}}` : undefined;
  const files = await vscode.workspace.findFiles('**/*.md', exclude);
  const root = folder.uri.fsPath;

  const all = [];
  await vscode.window.withProgress(
    { location: vscode.ProgressLocation.Window, title: 'Flashcards: scanning notes...' },
    async () => {
      for (const uri of files) {
        try {
          all.push(...readCards(uri, root).cards);
        } catch (err) {
          console.warn(`[md-flashcards] skipped ${uri.fsPath}: ${err.message}`);
        }
      }
    },
  );
  await startSession(context, all, folder.uri, path.basename(root), orderDue);
}

async function showStats(uri) {
  const target = resolveUri(uri);
  if (!target) return;
  const { root, file } = stateFileFor(target);
  const { cards, headings } = readCards(target, root);
  const state = store.load(file);
  const due = cards.filter((c) => scheduler.isDue(state.cards[c.id])).length;
  const seen = cards.filter((c) => state.cards[c.id]).length;
  vscode.window.showInformationMessage(
    `${path.basename(target.fsPath)}: ${cards.length} cards in ${headings.filter((h) => h.cards).length} sections - ${due} due, ${cards.length - seen} new.`,
  );
}

function activate(context) {
  context.subscriptions.push(
    vscode.commands.registerCommand('mdFlashcards.practiceFile', (uri) => practiceFile(context, uri)),
    vscode.commands.registerCommand('mdFlashcards.practiceSection', (uri) => practiceSection(context, uri)),
    vscode.commands.registerCommand('mdFlashcards.practiceWorkspace', () => practiceWorkspace(context)),
    vscode.commands.registerCommand('mdFlashcards.showStats', (uri) => showStats(uri)),
  );
}

function deactivate() {}

module.exports = { activate, deactivate };
