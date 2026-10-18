# Instruction-following pilot — Phase 5

A real, bounded, measured experiment: can the existing NEXORA Core
architecture learn to follow simple instructions at all, at this parameter
and data scale? Short answer, backed by the evidence below: **it learns the
surface format, but does not generalize** -- a negative-but-informative
result, reported in full rather than reframed as a win.

## Dataset

`artifacts/datasets/instruction-pilot-v1/`, built by
`scripts/prepare-instruction-pilot.py`. 61 original documents (48 train / 6
validation / 7 test), each a complete `"Instruction: ...\nResponse: ..."`
pair. All text is NEXORA-engineering-authored for this pilot specifically --
no third-party content, no model-generated text, no private conversation
data. License: CC0-1.0 (public domain; the author dedicates it). Categories
covered: exact word/phrase repetition, single-digit arithmetic (`a` in 0-5,
`b` in 0-3), yes/no factual questions, small structured JSON objects/arrays,
cowork tool-selection (`/write`/`/read`/`/run`), and three original
"decline rather than fabricate" examples. Manifest and both split files are
sha256-pinned, following the same integrity convention as every other
dataset in this project (`nexora.data_engine.load_dataset` verifies them on
every load).

**This is not a proper supervised fine-tuning (SFT) pipeline.** A real SFT
setup masks the loss to the response tokens only, so the model is never
penalized for not predicting the prompt. `nexora.research`'s training loop
computes plain next-token cross-entropy over the *entire* concatenated
document (prompt and response both) -- there is no loss-masking
implementation yet. This pilot is best described as **continued pretraining
on instruction-formatted text**, not SFT. Adding real completion-only loss
masking is the concrete next engineering step before claiming an SFT
pipeline exists; it needs a per-token mask threaded through tokenization,
packing and the loss computation in `nexora/research.py`'s training step,
which was not implemented this pass.

## Training run

```
nexora.research.create_run('instruction-pilot-v1', profile='small',
  training={'steps': 300, 'vocab_size': 512, 'max_seconds': 170, ...},
  run_id='phase5-instruction-pilot-v1')
nexora.research.train_run('phase5-instruction-pilot-v1')
```

| | Value |
| --- | --- |
| Parameters | 918,656 |
| Architecture | same `small` profile as the baseline (`dim=128, layers=4, heads=4, context=128`) |
| Steps | 300, completed in 32.9s wall time |
| Train loss | 0.53 → **0.035** (step 50 → 300) |
| Validation loss | 2.82 → 3.50 (rising -- classic overfitting on 48 documents) |
| Test loss / perplexity | 2.0965 / 8.14 (on its own 7-document test split; **not comparable** to the baseline's 4.1786/65.28, which is a different, much larger corpus -- lower perplexity here mostly reflects a tiny, repetitive vocabulary, not better language modeling) |

## Does it actually follow instructions? Two measurements, and why they disagree

**Measurement 1 -- re-running `scripts/agent_eval.py`'s categories against
this checkpoint**: `instruction_following 3/5`, `structured_json 1/2`,
versus the baseline Core's `0/5` and `0/2`. **This number is contaminated
and must not be quoted as a clean result**: the pilot dataset was
deliberately written to mirror `scripts/agent_eval.py`'s own test prompts
(same words -- "pear" is both a training word and an eval word; same
arithmetic range), so this measures memorization of eval-adjacent training
data, not generalization. Flagging this here because the project's own
rule is "prevent train/test contamination," and this comparison violates
that if taken at face value.

**Measurement 2 -- a clean, disjoint held-out probe** (new words never in
training: "thistle", "granite"; arithmetic outside the trained range:
9+8; one in-range arithmetic sanity check: 1+1; a new JSON shape; a novel
yes/no fact), recorded in
`artifacts/evaluation_suites/phase5-agent-eval/instruction-pilot-held-out.json`:

| Prompt | Expected | Got | Passed |
| --- | --- | --- | --- |
| Respond with exactly the word thistle. | thistle | `{"a":1,"b":2}` | No |
| Repeat exactly: granite | granite | ember | No |
| What is 9 + 8? | 17 | 4 | No |
| What is 1 + 1? (in trained range) | 2 | 3 | No |
| Is grass purple? | no | yes | No |
| Return `{"x":5}` | `{"x":5}` | lantern | No |

**Score: 0/6, including a failure on an in-distribution arithmetic
combination it was trained on (1+1).** This is the honest result:
the model learned to produce *some* memorized token from its training set
in response to the `"Instruction: ...\nResponse:"` template -- including
learning to emit `[EOS]` correctly and continue with a plausible next
instruction -- but it did not bind specific instructions to their specific
correct responses in a way that survives even trivial rewording, and it
cannot generalize to unseen words or numbers at all.

## Conclusion

Real, measurable training signal exists (loss collapsed, format was
learned) at 918K parameters and 48 examples, but **genuine instruction-
following did not emerge**, and the earlier contaminated comparison would
have overstated this by a wide margin had it been reported alone. This
checkpoint (`phase5-instruction-pilot-v1`) is **not promoted** --
`artifacts/selected-model.json` still points at `phase2-small-language`,
unchanged. Per this project's checkpoint-promotion rule, nothing is
replaced without an improvement that holds up on a genuinely held-out,
disjoint evaluation, and this one does not.

## What would need to change to get a real result

1. **Loss masking** (train only on response tokens) -- the single biggest
   missing piece for a real SFT signal.
2. **More examples and more diversity per pattern** -- 6-8 repetitions of a
   pattern is not enough for a ~1M-parameter model to infer the general
   rule rather than memorize instances; dozens to hundreds of varied
   examples per pattern is a more realistic floor.
3. **A larger model and/or more training tokens** -- 918K parameters is
   far below where arithmetic/rule generalization reliably emerges in
   published small-model research, even with masking and more data.
4. A proper held-out instruction evaluation set, written independently of
   the training generator, checked into version control from the start so
   contamination like the one caught here cannot happen silently next time.
