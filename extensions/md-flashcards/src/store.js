'use strict';

/**
 * Scheduling state persistence.
 *
 * One JSON file per workspace, keys sorted, two-space indent - so git diffs show
 * only the handful of lines belonging to the cards you actually reviewed.
 * `note` and `front` are stored purely so the file stays readable on its own.
 */

const fs = require('fs');
const path = require('path');

const VERSION = 1;

function load(file) {
  try {
    const parsed = JSON.parse(fs.readFileSync(file, 'utf8'));
    return { version: VERSION, cards: parsed.cards || {} };
  } catch (err) {
    if (err.code !== 'ENOENT') {
      console.warn(`[md-flashcards] unreadable state file ${file}: ${err.message}`);
    }
    return { version: VERSION, cards: {} };
  }
}

function sortKeys(cards) {
  const out = {};
  for (const id of Object.keys(cards).sort()) out[id] = cards[id];
  return out;
}

function save(file, state) {
  fs.mkdirSync(path.dirname(file), { recursive: true });
  const payload = { version: VERSION, cards: sortKeys(state.cards) };
  const tmp = `${file}.tmp`;
  fs.writeFileSync(tmp, `${JSON.stringify(payload, null, 2)}\n`, 'utf8');
  fs.renameSync(tmp, file);
}

/** Merge the scheduling fields with the human-readable breadcrumbs for one card. */
function entry(card, scheduling) {
  return {
    note: card.file,
    front: card.front.length > 90 ? `${card.front.slice(0, 87)}...` : card.front,
    due: scheduling.due,
    interval: scheduling.interval,
    ease: scheduling.ease,
    reps: scheduling.reps,
    lapses: scheduling.lapses,
    reviewed: scheduling.reviewed,
  };
}

module.exports = { load, save, entry, VERSION };
