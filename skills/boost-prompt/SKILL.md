---
name: boost-prompt
description: "Turn any rough prompt, half-formed idea, or task description into a finished, ready-to-send prompt optimized for chat-based LLMs. Use when user wants to write, rewrite, optimize, improve, sharpen, or polish a prompt. Trigger phrases: 'rewrite this prompt', 'make this a better prompt', 'optimize this prompt', 'help me prompt this', 'draft a prompt that...'. Also trigger when user pastes a draft prompt and asks for improvements, or describes a task for an LLM and wants a reusable prompt rather than a direct answer. Output is always a single copy-pasteable prompt -- never a template with placeholders."
---

# Prompt Optimizer

Turn whatever the user gives you -- a rough draft, vague idea, task description, or paragraph of context -- into a single high-quality prompt for **chat interfaces** (Claude, Copilot, ChatGPT, etc.). No system prompt, no API config -- the prompt itself does all the work.

## Two Hard Rules

These override everything else.

### Rule 1 -- No placeholders. Ever.

Never produce `[paste X here]`, `{topic}`, `<your_input>`, `___`, or any template variable. The user must copy-paste-send with zero edits. If you catch yourself typing brackets around a noun, rewrite.

### Rule 2 -- Ship a finished prompt no matter what.

- **Case A** -- user gave real content (draft, code, document, data): bake it directly into the prompt.
- **Case B** -- user described a class of task ("help me prompt code review"): write a self-contained instruction that either asks the LLM to gather inputs ("Before drafting, ask me for...") or phrases the task so user provides input next turn ("I'm going to paste code next. For each file...").

## Workflow

1. **Clarify if needed.** If the user's intent is ambiguous, ask targeted questions about scope, audience, format, constraints. Keep questions minimal -- don't interrogate when you can infer. Use the `joyride_request_human_input` tool when clarification is needed.
2. **Explore context.** Use available tools to understand the user's project/workspace if relevant to writing a better prompt.
3. **Rewrite.** Apply the principles below. Work through these mentally:
   - What concrete output does the user want? (document, decision, code, analysis)
   - Who reads it and what do they do with it?
   - Case A or Case B?
   - What's missing? (audience, format, length, constraints, examples, edge cases)
   - Handle gaps: assume non-essential details; for essential user-specific inputs, follow Rule 2.
   - Pick structure: single paragraph for simple tasks; XML tags for multi-section prompts.
4. **Output.** Produce the optimized prompt in a fenced code block.
5. **Clipboard.** Copy to clipboard via Joyride:
   ```clojure
   (require '["vscode" :as vscode])
   (vscode/env.clipboard.writeText "your-markdown-text-here")
   ```
6. **Iterate.** Tell the user the prompt is on their clipboard. Ask if they want changes. Repeat copy + display + ask after any revision.

## Core Principles

### Clarity and directness
State the task explicitly. Specify output format and constraints up front. "Create an analytics dashboard with as many relevant features as possible" beats "create a dashboard."

### Explain the why
"Avoid ellipses because TTS mispronounces them" lands better than "never use ellipses." LLMs generalize from reasons.

### Positive framing
Tell the LLM what to do, not what to avoid. "Write in flowing prose" beats "don't use bullets."

### Style matching
If you want prose output, write the prompt in prose. Style leaks through.

### XML tags for complexity
When the prompt mixes instructions, context, examples, and input, wrap each in `<instructions>`, `<context>`, `<examples>`, `<input>`. Skip for simple tasks.

### Role assignment (when useful)
"You are a senior product strategist at a B2B SaaS company" tightens tone. Only when it meaningfully steers output.

### Examples for format/tone
2-4 examples in `<example>` tags beat description for steering format. Skip when examples would over-constrain.

### Long inputs on top, question on bottom
~30% quality lift on long-context tasks from this ordering.

### Grounding for long documents
Instruct the LLM to pull relevant quotes into `<quotes>` tags first, then answer. Reduces drift and hallucination.

### Be literal about scope
"Apply this to every section, not just the first." Use imperative verbs -- "Edit the function to..." not "Could you suggest..."

### Self-check for high stakes
For code, math, or factual claims: "Before finishing, re-read your answer and verify against the criteria above."

### Closing line
End every prompt with a reasoning nudge:
- Models with extended thinking: `Think before answering (maximum reasoning)`
- General models: `Take time to think through this carefully before responding.`

## Domain-Specific Moves

Apply only when relevant:

- **Code review**: "Report every issue including low-confidence ones. Include confidence and severity per finding." Avoid "only flag important issues" -- LLMs over-filter.
- **Research/analysis**: "Develop competing hypotheses. Track confidence. Self-critique periodically."
- **Creative writing**: Specify voice, audience, length. Provide 1-2 example sentences in target voice.
- **Frontend/design**: Specify palette, type system, structure concretely, or instruct model to propose 3-4 directions first.
- **Document creation**: "Include visual hierarchy, considered typography, engaging structure."

## Output Format

Always exactly: a single fenced code block containing the optimized prompt. No preamble ("Here's your prompt:"). No trailing explanation. If the user asks "what did you change?" after receiving the prompt, explain in a follow-up.

## Edge Cases

- **User asks "is this good?"** -- Treat as rewrite request. Return optimized version.
- **User gives an API/system prompt** -- Strip API mechanics, translate to single chat message, add closing line.
- **User wants many small tasks** -- Combine into one coherent prompt with clear sections.
- **User input is already excellent** -- Tighten, add closing line. Don't add ceremony.
- **Non-English input** -- Write optimized prompt in the same language.
- **Tempted to write a fill-in block** -- Don't. Rule 1. Bake content in or tell LLM to ask.

  
