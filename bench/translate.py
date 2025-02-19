"""Optional local translation; benchmark its compute and memory on the target device."""

import copy

CODES = {"yor": "yor_Latn", "hau": "hau_Latn", "ibo": "ibo_Latn", "eng": "eng_Latn"}


class Translator:
    def __init__(self, model_id="facebook/nllb-200-distilled-600M"):
        from transformers import AutoModelForSeq2SeqLM, AutoTokenizer

        self.tokenizer = AutoTokenizer.from_pretrained(model_id)
        self.model = AutoModelForSeq2SeqLM.from_pretrained(model_id).eval()

    def text(self, text, source, target):
        import torch

        self.tokenizer.src_lang = CODES[source]
        tokens = self.tokenizer(text, return_tensors="pt")
        if tokens.input_ids.shape[-1] > 512:
            raise ValueError("Translation input exceeds the reviewed context limit")
        with torch.inference_mode():
            result = self.model.generate(
                **tokens,
                forced_bos_token_id=self.tokenizer.convert_tokens_to_ids(CODES[target]),
                max_new_tokens=512,
            )
        return self.tokenizer.batch_decode(result, skip_special_tokens=True)[0]

    def item_to_english(self, item):
        output = copy.deepcopy(item)
        if item["language"] == "eng":
            return output
        for key in ["question", "premise", "hypothesis"]:
            if key in item:
                output[key] = self.text(item[key], item["language"], "eng")
        if "choices" in item:
            output["choices"] = [self.text(x, item["language"], "eng") for x in item["choices"]]
        return output
