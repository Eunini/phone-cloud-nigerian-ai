"""Optional local translation; benchmark its compute and memory on the target device."""

import copy
import json
from urllib.parse import urlsplit

from bench.client import Endpoint

CODES = {"yor": "yor_Latn", "hau": "hau_Latn", "ibo": "ibo_Latn", "eng": "eng_Latn"}


class Translator:
    def __init__(
        self,
        model_id="facebook/nllb-200-distilled-600M",
        revision="f8d333a098d19b4fd9a8b18f94170487ad3f821d",
    ):
        from transformers import AutoModelForSeq2SeqLM, AutoTokenizer

        self.identity = {"model": model_id, "revision": revision, "backend": "local NLLB CPU"}
        self.tokenizer = AutoTokenizer.from_pretrained(model_id, revision=revision)
        self.model = AutoModelForSeq2SeqLM.from_pretrained(model_id, revision=revision).eval()

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


class EndpointTranslator:
    """Translation by an actual locally running GGUF model, including on Termux."""

    def __init__(self, endpoint, model, revision):
        if urlsplit(endpoint).hostname not in {"127.0.0.1", "localhost", "::1"}:
            raise ValueError("The phone translation experiment requires a loopback translator")
        self.endpoint = Endpoint(endpoint, model)
        self.identity = {
            "model": model,
            "revision": revision,
            "backend": "local HTTP GGUF translation",
        }

    def text(self, text, source, target):
        if source == target:
            return text
        names = {"yor": "Yoruba", "hau": "Hausa", "ibo": "Igbo", "eng": "English"}
        response = self.endpoint.complete(
            [
                {
                    "role": "system",
                    "content": "Translate the quoted text without answering it or changing numbers. Return only JSON with exactly one string key: translation.",
                },
                {
                    "role": "user",
                    "content": json.dumps(
                        {
                            "source_language": names[source],
                            "target_language": names[target],
                            "text": text,
                        },
                        ensure_ascii=False,
                    ),
                },
            ],
            max_tokens=512,
        )
        value = json.loads(response["text"])
        if (
            not isinstance(value, dict)
            or set(value) != {"translation"}
            or not isinstance(value["translation"], str)
            or not value["translation"].strip()
        ):
            raise ValueError("Invalid local translation; never substitute a parallel gold question")
        return value["translation"]

    item_to_english = Translator.item_to_english

    def close(self):
        self.endpoint.close()
