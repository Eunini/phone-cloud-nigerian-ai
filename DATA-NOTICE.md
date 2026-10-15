# Benchmark data attribution

The evaluator code uses the MIT license in `LICENSE`. That does not relicense
third-party datasets or model weights.

This research bundle contains a deterministic 3,400-item selection from
Masakhane's IrokoBench datasets: AfriMMLU, AfriXNLI and AfriMGSM, in English,
Yoruba, Hausa and Igbo. Selection uses seed 2026, no replacement and the same
row indices across languages. Field names are normalized for evaluation.

Each pinned dataset card declares Apache-2.0. The bundle includes a copy of that
license and the unmodified upstream cards, including their citations, examples
and underlying benchmark references. Those cards and any underlying rights
remain applicable. The audit records the exact revisions and selection hash.

- [AfriMMLU](https://huggingface.co/datasets/masakhane/afrimmlu/tree/96f247619673906ae4c321a3232afc67b98ea57e)
- [AfriXNLI](https://huggingface.co/datasets/masakhane/afrixnli/tree/e3ca06b30f3e7af2a86f6c8609ea76fee326bc56)
- [AfriMGSM](https://huggingface.co/datasets/masakhane/afrimgsm/tree/8e4268d2b94941f18f63f694cf48e4ae26fbec65)
- [IrokoBench paper](https://arxiv.org/abs/2406.03368)

Model weights are not included in this bundle. Their separate source revisions
and licenses are recorded in `configs/models.json`.
