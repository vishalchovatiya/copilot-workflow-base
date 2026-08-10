'use strict';

/**
 * SM-2 (Anki-flavoured) spaced repetition.
 *
 * Each card carries an ease factor and an interval in days. A correct answer
 * multiplies the interval by the ease; a lapse sends the card back to "today"
 * and shaves the ease. Only whole days are tracked - intra-day learning steps
 * are handled by the session queue, not by the stored state, which keeps the
 * on-disk format small and diffable.
 */

const EASE_DEFAULT = 2.5;
const EASE_MIN = 1.3;
const MAX_INTERVAL = 3650;

const GRADES = { again: 1, hard: 2, good: 3, easy: 4 };

function today(now = new Date()) {
  const local = new Date(now.getTime() - now.getTimezoneOffset() * 60000);
  return local.toISOString().slice(0, 10);
}

function addDays(iso, days) {
  const d = new Date(`${iso}T00:00:00Z`);
  d.setUTCDate(d.getUTCDate() + Math.round(days));
  return d.toISOString().slice(0, 10);
}

function newState() {
  return { ease: EASE_DEFAULT, interval: 0, due: today(), reps: 0, lapses: 0, reviewed: null };
}

function clampEase(ease) {
  return Math.max(EASE_MIN, Math.round(ease * 100) / 100);
}

/**
 * Apply a grade and return the next state. Pure: the input is never mutated.
 * An interval of 0 means "still due today" - the session re-queues those cards.
 */
function review(state, grade, now = new Date()) {
  const prev = state || newState();
  const day = today(now);
  const next = { ...prev, reps: prev.reps + 1, reviewed: day };
  const learning = prev.reps === 0 || prev.interval === 0;

  switch (grade) {
    case GRADES.again:
      next.ease = clampEase(prev.ease - 0.2);
      next.interval = 0;
      next.lapses = prev.lapses + (learning ? 0 : 1);
      break;
    case GRADES.hard:
      next.ease = clampEase(prev.ease - 0.15);
      next.interval = learning ? 1 : Math.max(prev.interval + 1, Math.round(prev.interval * 1.2));
      break;
    case GRADES.good:
      next.ease = prev.ease;
      next.interval = learning ? 1 : Math.max(prev.interval + 1, Math.round(prev.interval * prev.ease));
      break;
    case GRADES.easy:
      next.ease = clampEase(prev.ease + 0.15);
      next.interval = learning ? 4 : Math.max(prev.interval + 2, Math.round(prev.interval * prev.ease * 1.3));
      break;
    default:
      throw new Error(`unknown grade: ${grade}`);
  }

  next.interval = Math.min(next.interval, MAX_INTERVAL);
  next.due = addDays(day, next.interval);
  return next;
}

function isDue(state, now = new Date()) {
  return !state || state.due <= today(now);
}

function formatInterval(days) {
  if (days <= 0) return 'today';
  if (days === 1) return '1 day';
  if (days < 30) return `${days} days`;
  if (days < 365) return `${Math.round(days / 30)} mo`;
  return `${(days / 365).toFixed(1)} yr`;
}

/** Interval preview shown on each grading button. */
function previews(state, now = new Date()) {
  return {
    again: formatInterval(review(state, GRADES.again, now).interval),
    hard: formatInterval(review(state, GRADES.hard, now).interval),
    good: formatInterval(review(state, GRADES.good, now).interval),
    easy: formatInterval(review(state, GRADES.easy, now).interval),
  };
}

module.exports = { GRADES, newState, review, isDue, today, addDays, formatInterval, previews };
