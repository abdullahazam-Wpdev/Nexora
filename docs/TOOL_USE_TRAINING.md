# Tool-use training — Phase 6 (baseline exists, training not run this pass)

Phase 6 §12 asks for a tool-selection benchmark/training dataset (search
the web, read a document, run a test, inspect an error log, decline
unauthorized actions, etc.) with strict JSON schemas and held-out
evaluation before any training.

## What already exists: a real, measured baseline

`scripts/agent_eval.py`'s `tool_selection` category (from Phase 5) already
measures exactly this for three tools (`/write`, `/read`, `/run`): NEXORA
Core scores 0/3, Ollama/SmolLM2 scores 1/3. This is the "establish a
baseline" step Phase 6 §12 itself requires before training -- already
done, in a prior pass, and still valid (re-confirm by re-running
`scripts/agent_eval.py` before any future training attempt, since this
pass changed the local model generation length limits and that could
shift results).

Phase 5's `docs/INSTRUCTION_TUNING.md` already demonstrates, with a real
experiment, that training on a tiny (61-document) original dataset
produces memorization rather than generalization at this parameter count.
The same conclusion almost certainly applies to a tool-use dataset of
similar size, so expanding the tool catalog (web search, document read,
error-log inspection, decline-unauthorized-action, as Phase 6 asks) without
also fixing the two root causes identified there (no completion-only loss
masking, too little varied data per pattern) would very likely reproduce
the same negative result rather than teach anything new.

## Status: no new tool-use dataset or training run this pass

Not done, by the same prioritization as `docs/PROBLEM_SOLVING.md` and
`docs/RAG_ARCHITECTURE.md` -- this pass's time went to the search/browser/
research vertical slice. Running another training experiment before
addressing loss masking (the #1 priority in
`docs/NEXORA_TRAINING_STRATEGY.md`'s roadmap) would not be a meaningfully
different experiment from the one already run and documented.

## Concrete next step, scoped for a future pass

1. Implement completion-only loss masking in `nexora/research.py`'s
   training loop (the standing #1 priority from Phase 5).
2. Build a tool-use dataset covering the categories Phase 6 §12 lists
   (search, read file, run test, inspect log, search codebase, structured
   response, ask for missing info, decline unauthorized action), each
   target a strict JSON schema (`{"tool": "...", "args": {...}}`), with
   dozens of varied phrasings per category -- not 6-8, per the lesson
   already learned.
3. Measure correct tool selection, argument validity, and unsafe/
   unnecessary tool-call rate on a held-out split written independently
   of the training-data generator, to avoid repeating the contamination
   caught and documented in `docs/INSTRUCTION_TUNING.md`.
4. Only promote a checkpoint if it beats the existing baseline on that
   held-out set -- never on the training-adjacent numbers alone.
