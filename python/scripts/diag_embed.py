"""Step-by-step embedding diagnostic (stdout flushed after each step)."""

from __future__ import annotations

import os
import sys

os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("MKL_NUM_THREADS", "1")
os.environ.setdefault("HF_HUB_DISABLE_PROGRESS_BARS", "1")


def step(msg: str) -> None:
    print(msg, flush=True)


def main() -> int:
    step("1 import torch")
    import torch

    torch.set_num_threads(1)
    step(f"2 torch {torch.__version__} threads={torch.get_num_threads()}")
    x = torch.randn(4, 32)
    step(f"3 matmul ok shape={(x @ x.T).shape}")

    step("4 import SentenceTransformer")
    from sentence_transformers import SentenceTransformer

    step("5 load model (cpu)")
    model = SentenceTransformer("intfloat/multilingual-e5-small", device="cpu")
    step("6 model loaded")

    step("7 tokenize only")
    features = model.tokenize(["passage: hello world"])
    step(f"8 tokenized keys={list(features.keys())}")

    step("9 forward (model.forward)")
    features = {
        k: v.to(model.device) if hasattr(v, "to") else v for k, v in features.items()
    }
    with torch.inference_mode():
        out = model.forward(features)
    step(f"10 forward ok type={type(out)}")

    step("11 encode via encode() numpy")
    with torch.inference_mode():
        vec = model.encode(
            ["passage: hello world"],
            show_progress_bar=False,
            convert_to_numpy=True,
            convert_to_tensor=False,
            batch_size=8,
        )
    step(f"12 encode ok dim={len(vec[0])}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr, flush=True)
        raise
