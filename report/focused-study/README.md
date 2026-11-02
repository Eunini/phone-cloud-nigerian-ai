# Q4 and Q8 accuracy in Yoruba and English

Inioluwa Atanda

I compare two published GGUF versions of Qwen2.5-1.5B-Instruct on 300 matched English and Yoruba AfriXNLI questions. The question is whether the accuracy change from Q8_0 to Q4_K_M differs between the two languages.

I narrowed the study after examining the wider benchmark results. This is an exploratory reanalysis of existing answers. I have not run the proposed confirmation experiment.

English accuracy is 65.00% for both configurations. Yoruba accuracy is 34.67% for Q8_0 and 36.33% for Q4_K_M. The paired comparison does not establish a greater compression penalty for Yoruba. Neither Yoruba configuration predicts the neutral class, which limits the conclusions I can draw from this task.

The [three-page review note](Inioluwa-Quantization-Review-Note-2026-11-02.pdf) gives the question, results and remaining problems. The [protocol](protocol.md) describes the method, and [results.md](results.md) includes the tables and error analysis.

For reproduction, see the [analysis settings](analysis-plan.json), [runtime records](provenance.json), [paired results](paired-results.csv) and [file hashes](review-manifest.json). The [confirmation plan](confirmation-plan.json) lists the unused question IDs and the controls still to be agreed before a fresh run.
