'use strict';

/**
 * Extract flashcards from Markdown text.
 *
 * A card is any line containing `::` followed by whitespace or end-of-line:
 *
 *     Ease factor:: how fast the interval grows after a "Good" answer
 *
 * The lookahead is what keeps C++ scope resolution (`std::vector`), URLs and
 * Obsidian block refs from being mistaken for cards.
 *
 * The back of the card absorbs any following lines that are indented deeper than
 * the card line, so nested sub-bullets and fenced examples stay with their answer.
 *
 * Run standalone to preview what a file yields:
 *     node src/parser.js path/to/note.md
 */

const crypto = require('crypto');

const FENCE = /^\s{0,3}(?:`{3,}|~{3,})/;
const HEADING = /^(#{1,6})\s+(.+?)\s*#*\s*$/;
const LIST_MARKER = /^\s*(?:[-*+]|\d+[.)])\s+/;
const CARD_DELIM = /::(?=\s|$)/;

function indentOf(line) {
  return line.length - line.trimStart().length;
}

/** Key used for the card id: cosmetic edits to the front must not orphan history. */
function normalizeFront(front) {
  return front
    .replace(LIST_MARKER, '')
    .replace(/[*_`~]/g, '')
    .replace(/\s+/g, ' ')
    .trim()
    .toLowerCase();
}

function cardId(relPath, front, occurrence) {
  const key = `${relPath}\u0000${normalizeFront(front)}${occurrence > 1 ? `\u0000#${occurrence}` : ''}`;
  return crypto.createHash('sha1').update(key).digest('hex').slice(0, 12);
}

/** Split a line into front/back, or return null when it is not a card line. */
function splitCardLine(line) {
  if (HEADING.test(line)) return null;
  const at = line.search(CARD_DELIM);
  if (at < 0) return null;
  const front = line.slice(0, at).replace(LIST_MARKER, '').trim();
  if (!front) return null;
  return { front, back: line.slice(at + 2).trim() };
}

/**
 * Collect the continuation lines belonging to a card, starting at `from`.
 * Stops at the first non-blank line that is not indented deeper than the card,
 * and at any nested card line (that one becomes a card of its own).
 */
function readContinuation(lines, from, baseIndent) {
  const out = [];
  let i = from;
  let inFence = false;

  for (; i < lines.length; i++) {
    const line = lines[i];
    if (inFence) {
      out.push(line);
      if (FENCE.test(line)) inFence = false;
      continue;
    }
    if (!line.trim()) {
      out.push('');
      continue;
    }
    if (indentOf(line) <= baseIndent) break;
    if (splitCardLine(line)) break;
    if (FENCE.test(line)) inFence = true;
    out.push(line);
  }

  while (out.length && !out[out.length - 1].trim()) out.pop();

  const common = out.reduce((min, l) => (l.trim() ? Math.min(min, indentOf(l)) : min), Infinity);
  const dedented = Number.isFinite(common) ? out.map((l) => l.slice(common)) : out;
  return { text: dedented.join('\n'), next: i };
}

/**
 * @param {string} text     raw Markdown
 * @param {string} relPath  workspace-relative path, used for stable card ids
 * @returns {{cards: Array, headings: Array}}
 */
function parse(text, relPath) {
  const lines = text.split(/\r?\n/);
  const cards = [];
  const headings = [];
  const stack = [];
  const occurrences = new Map();
  let inFence = false;

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];

    if (FENCE.test(line)) {
      inFence = !inFence;
      continue;
    }
    if (inFence) continue;

    const heading = HEADING.exec(line);
    if (heading) {
      const node = { line: i, level: heading[1].length, title: heading[2].trim(), cards: 0 };
      while (stack.length && stack[stack.length - 1].level >= node.level) stack.pop();
      stack.push(node);
      headings.push(node);
      continue;
    }

    const split = splitCardLine(line);
    if (!split) continue;

    const baseIndent = indentOf(line);
    const cont = readContinuation(lines, i + 1, baseIndent);
    const back = [split.back, cont.text].filter(Boolean).join('\n');

    const key = normalizeFront(split.front);
    const occurrence = (occurrences.get(key) || 0) + 1;
    occurrences.set(key, occurrence);

    cards.push({
      id: cardId(relPath, split.front, occurrence),
      file: relPath,
      line: i,
      front: split.front,
      back,
      section: stack.length ? stack[stack.length - 1].title : '',
      ancestors: stack.map((h) => h.line),
    });
    for (const h of stack) h.cards++;

    i = cont.next - 1;
  }

  return { cards, headings };
}

/** Cards under a heading, including everything in its sub-headings. */
function cardsInSection(cards, headingLine) {
  return cards.filter((c) => c.ancestors.includes(headingLine));
}

module.exports = { parse, cardsInSection, normalizeFront, cardId };

if (require.main === module) {
  const fs = require('fs');
  const file = process.argv[2];
  if (!file) {
    console.error('usage: node parser.js <file.md>');
    process.exit(2);
  }
  const { cards } = parse(fs.readFileSync(file, 'utf8'), file.replace(/\\/g, '/'));
  for (const c of cards) {
    console.log(`${c.id}  L${c.line + 1}  [${c.section}]`);
    console.log(`   Q: ${c.front}`);
    console.log(`   A: ${c.back.split('\n').join('\n      ')}`);
  }
  console.log(`\n${cards.length} cards`);
}
