# Sample Flashcard Note

Everything below is ordinary Markdown. Nothing here is special syntax for the extension
except the `::` delimiter, and nothing needs to be added to your own notes.

## 1. Spaced Repetition Basics

1. Ease factor:: the per-card multiplier applied to the interval after a "Good" answer; starts at 2.5 and floors at 1.3
2. Lapse:: a review graded **Again**, which resets the interval to zero and lowers the ease
3. Interval:: the number of days until the card is due again
4. Learning card:: a card with zero reps or a zero interval, so it is still being drilled today

## 2. Cards With Nested Answers

1. Three grades that keep a card in rotation:: **Again** repeats it today, while Hard and Good only slow it down
   1. Again -> interval 0, ease -0.20
   2. Hard -> interval x 1.2, ease -0.15
   3. Good -> interval x ease, ease unchanged
2. What the state file stores:: one sorted JSON object per card
   ```json
   { "due": "2026-08-14", "interval": 4, "ease": 2.3, "reps": 6, "lapses": 1 }
   ```

## 3. Lines That Are Deliberately Not Cards

1. `std::vector<int>` — no whitespace after `::`, so this is code, not a card
2. Docs live at https://code.visualstudio.com/api — a URL, not a card
3. Headings are skipped even when they contain the delimiter

```text
inside_a_fence:: this is never extracted
```

## 4. Cue-Only Cards

1. Name three connectors used for addition::
2. Name three connectors used for contrast::

These have an empty back on purpose — the panel shows *(no answer text)* and you self-check.

---

## 5. What a Review Session Looks Like

Right-click this file -> **Flashcards** -> **Practice Section...** -> pick
`2. Cards With Nested Answers`. The panel opens beside the note:

```text
 1 / 2                                        samples/sample-cards.md:15
 ─────────────────────────────────────────────────────────────────────
 Three grades that keep a card in rotation

 [ Show answer (Space) ]
```

Press `Space`:

```text
 1 / 2                                        samples/sample-cards.md:15
 ─────────────────────────────────────────────────────────────────────
 Three grades that keep a card in rotation
 ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─
 Again repeats it today, while Hard and Good only slow it down
 1. Again -> interval 0, ease -0.20
 2. Hard  -> interval x 1.2, ease -0.15
 3. Good  -> interval x ease, ease unchanged

 [ Again (1) ] [ Hard (2) ] [ Good (3) ] [ Easy (4) ]
    today          1 day       1 day        4 days
```

Press `3`. The card's entry is written to `.flashcards/state.json` immediately and the next
card appears. The path in the top-right corner is a link — click it (or press `O`) to open
this note at line 15 in the neighbouring column, edit it, then click back on the panel and
carry on grading. Choosing **Practice Whole File** instead reviews all cards in sections 1-4
in shuffled order.
