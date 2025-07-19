"""Create a private, self-contained Kaggle vLLM evaluation notebook."""

import argparse
import base64
import hashlib
import io
import json
import subprocess
import tarfile
from pathlib import Path

MODEL = "Qwen/Qwen2.5-7B-Instruct-AWQ"
REVISION = "b25037543e9394b818fdfca67ab2a00ecc7dd641"


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--owner", required=True)
    p.add_argument("--out", type=Path, required=True)
    a = p.parse_args()
    a.out.mkdir(parents=True, exist_ok=True)
    archive = subprocess.check_output(["git", "archive", "--format=tar.gz", "HEAD"])
    items = Path("data/prepared/items.jsonl").read_bytes()
    if len(items.splitlines()) != 3400:
        raise ValueError("Prepare the full audited item set")
    bundle = io.BytesIO()
    with tarfile.open(fileobj=bundle, mode="w:gz") as target:
        with tarfile.open(fileobj=io.BytesIO(archive), mode="r:gz") as source:
            for member in source:
                target.addfile(member, source.extractfile(member) if member.isfile() else None)
        member = tarfile.TarInfo("data/prepared/items.jsonl")
        member.size, member.mode = len(items), 0o644
        target.addfile(member, io.BytesIO(items))
    blob = bundle.getvalue()
    source = """import base64, hashlib, io, json, os, pathlib, subprocess, sys, tarfile, time, urllib.request
root = pathlib.Path('/kaggle/temp/phone-cloud-nigerian-ai')
root.mkdir(parents=True, exist_ok=True)
blob = base64.b64decode('__BLOB__')
assert hashlib.sha256(blob).hexdigest() == '__SHA__'
with tarfile.open(fileobj=io.BytesIO(blob)) as source:
    source.extractall(root, filter='data')
import torch
assert torch.cuda.is_available(), 'No GPU; no benchmark started'
print('GPU:', torch.cuda.get_device_name(0), 'Python:', sys.version)
env = os.environ.copy()
env.update(HF_HOME='/kaggle/temp/huggingface', HF_HUB_DISABLE_IMPLICIT_TOKEN='1', CUDA_VISIBLE_DEVICES='0', VLLM_NO_USAGE_STATS='1')
venv = pathlib.Path('/kaggle/temp/vllm-env')
subprocess.run([sys.executable, '-m', 'venv', '--without-pip', str(venv)], check=True)
python = str(venv / 'bin/python')
subprocess.run([sys.executable, '-m', 'pip', '--python', str(venv), 'install', '--no-cache-dir', 'vllm==0.11.2', 'psutil==7.2.2'], env=env, check=True)
output = pathlib.Path('/kaggle/working/cloud-results'); output.mkdir(exist_ok=True)
model, revision = '__MODEL__', '__REVISION__'
(output / 'run-provenance.json').write_text(json.dumps({'model':model,'revision':revision,'vllm':'0.11.2','gpu':torch.cuda.get_device_name(0),'items_sha256':hashlib.sha256((root/'data/prepared/items.jsonl').read_bytes()).hexdigest(),'latency_scope':'client and vLLM server on the same Kaggle host; excludes phone WAN RTT','cost_scope':'free research GPU quota; no continuously available public endpoint'},indent=2))
with (output / 'vllm-server.log').open('w') as log:
    server = subprocess.Popen([str(venv/'bin/vllm'), 'serve', model, '--revision', revision,
        '--host','127.0.0.1','--port','8000','--served-model-name','cloud-qwen7b-awq',
        '--max-model-len','2048','--max-num-seqs','1','--dtype','half','--quantization','awq',
        '--enforce-eager','--seed','2026','--gpu-memory-utilization','0.80','--disable-log-requests'],env=env,stdout=log,stderr=subprocess.STDOUT)
    try:
        for attempt in range(180):
            if server.poll() is not None: raise RuntimeError('vLLM stopped; inspect the private server log')
            try:
                with urllib.request.urlopen('http://127.0.0.1:8000/health',timeout=5) as response:
                    if response.status == 200: break
            except OSError: pass
            time.sleep(5)
        else: raise RuntimeError('vLLM readiness timeout')
        subprocess.run([python,'-m','bench.run','--items','data/prepared/items.jsonl',
            '--endpoint','http://127.0.0.1:8000/v1','--model','cloud-qwen7b-awq',
            '--label','Qwen2.5-7B-AWQ-Kaggle','--model-revision',revision,'--placement','cloud',
            '--device','Kaggle Tesla T4; client/server loopback; free research quota',
            '--server-pid',str(server.pid),'--out',str(output/'qwen7b-full.jsonl')],cwd=root,env=env,check=True)
    finally:
        server.terminate()
        try: server.wait(timeout=30)
        except subprocess.TimeoutExpired: server.kill(); server.wait()
print('Completed real vLLM batch benchmark; phone WAN latency and production hosting costs remain separate.')
"""
    for key, value in {
        "__BLOB__": base64.b64encode(blob).decode(),
        "__SHA__": hashlib.sha256(blob).hexdigest(),
        "__MODEL__": MODEL,
        "__REVISION__": REVISION,
    }.items():
        source = source.replace(key, value)
    (a.out / "study.py").write_text(source)
    (a.out / "kernel-metadata.json").write_text(
        json.dumps(
            {
                "id": a.owner + "/nigerian-languages-vllm-cloud-benchmark",
                "title": "Nigerian languages vLLM cloud benchmark",
                "code_file": "study.py",
                "language": "python",
                "kernel_type": "script",
                "is_private": True,
                "enable_gpu": True,
                "enable_internet": True,
                "machine_shape": "NvidiaTeslaT4",
                "docker_image": "gcr.io/kaggle-private-byod/python@sha256:22be155a37fc52bc8254ebfd0bb894643d00a1283e2446e212597ae12aec45f9",
                "docker_image_pinning_type": "original",
                "dataset_sources": [],
                "competition_sources": [],
                "kernel_sources": [],
            },
            indent=2,
        )
    )
    print("Prepared self-contained private GPU benchmark, pinned vLLM and AWQ weights.")


if __name__ == "__main__":
    main()
