# Independent Core 2.0 research

There is no promoted Core 2.0 assistant. Selected Core stays at 984,192 parameters
and its original SHA-256/tokenizer/context/409,600-token training record. Loading
and integrity were verified; Phase 8 wider tool checkpoint reproduced 6/16 tools
and 14/16 valid JSON. Qwen weights are external inference only, not Core or a
fine-tuned external checkpoint.

Phase 9 tested training/data/format changes instead of enlarging for a headline:
336,864-parameter 80-step tool-only continuation of the controlled random-init
pilot design; two 387,552-parameter random-init mixed-instruction/argument pilots;
and an exact repeat of the explicit-parameter pilot. Different tokenizer/data
vocabulary explains the small parameter difference. None initializes from Qwen
or alters the selected Core checkpoint.

Completion-only supervision masks prompt/padding labels, trains response/EOS,
clips gradients and uses AdamW, two CPU threads, a 45-second monitored budget,
650 MiB RSS ceiling and 500 MiB minimum available RAM. Checkpoints are separate
safetensors with round-trip verification. The explicit pilot repeat reproduced
**every tensor and the dataset SHA**. No original checkpoint migration is needed.

The principal failure is generalization, not a missing bigger parameter target:
validation paraphrases reuse training meanings, and withheld values/actions remain
hard. Low validation perplexity coincides with poor held-out generation. The model
replied amber to a violet request, showing response memorization. Do not promote
on loss or syntax alone. See INSTRUCTION_TUNING_RESULTS.md for exact measurements.
