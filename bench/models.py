import argparse
import hashlib
import json
from pathlib import Path

from huggingface_hub import hf_hub_download


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--model", choices=["qwen", "llama", "smollm"], required=True)
    p.add_argument("--quant", choices=["Q4_K_M", "Q8_0"], required=True)
    p.add_argument("--out", type=Path, default=Path("models"))
    p.add_argument("--config", type=Path, default=Path("configs/models.json"))
    a = p.parse_args()
    model = json.loads(a.config.read_text())["models"][a.model]
    path = Path(
        hf_hub_download(
            model["repo"], model["files"][a.quant], revision=model["revision"], local_dir=a.out
        )
    )
    sha = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(4 * 1024 * 1024), b""):
            sha.update(chunk)
    path.with_suffix(".provenance.json").write_text(
        json.dumps(
            {
                **model,
                "quantization": a.quant,
                "filename": path.name,
                "sha256": sha.hexdigest(),
            },
            indent=2,
        )
    )
    print(path)
