# Background

**IrokoBench.** The benchmark supplies human-translated African-language tasks
covering natural-language inference, knowledge questions and grade-school math.
Its experiments compare in-language prompting with translating test inputs to
English and show why translation is a useful condition to test. Those results
concern the evaluated models and translators, so they do not establish that a
small quantized phone model benefits equally. This project repeats the relevant
comparison while measuring device performance and user data cost.
[Paper](https://arxiv.org/html/2406.03368v2),
[datasets](https://huggingface.co/masakhane/datasets).

**The African Language Tax (2026).** This paper examines how different tokenizers
encode parallel African-language content and translates token inflation into
deployment considerations. It supports measuring observed tokens, latency and
bytes for the actual workload. Its tokenization-derived cost and latency
projections should not be mistaken for measured network use, phone performance
or complete end-user cost. Here, actual responses and application-body bytes are
logged separately from any price conversion.
[Paper](https://arxiv.org/pdf/2606.24460).

**Swahili on-device pilot (Farouk, 2026).** The NeurIPS listing describes a
40-item Swahili pilot with Llama 3.2 3B, Qwen 2.5 3B and Gemma 2 2B at three
precisions. It reports task-dependent accuracy changes and a notable systems
result: int8 was slower than fp16 on its Kaggle T4, despite smaller memory use.
The reported timing hardware was a GPU, rather than a physical phone. Its small
per-cell sample sizes are explicitly descriptive. This motivates measuring
quantization on the actual target device rather than assuming that fewer bits
must mean faster inference, and using a larger, independently translated test set.
[NeurIPS listing](https://neurips.cc/virtual/2026/162776),
[OpenReview](https://openreview.net/forum?id=1cdEKvFHfk).
