"""Generate a tiny, fully self-contained variant-calling test dataset with a
KNOWN ground truth -- no downloads required.

We build a random reference, copy it into a "sample" genome with a handful of
SNPs at known positions, then simulate short reads off the sample. Because we
planted the variants ourselves, the expected VCF is known exactly, which makes
correctness measurable (recall against ground truth), not just "it ran".

Usage:
    python data/make_test_data.py --outdir data/test --seed 42
"""
from __future__ import annotations

import argparse
import json
import os
import random


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--outdir", default="data/test")
    ap.add_argument("--length", type=int, default=20000)
    ap.add_argument("--coverage", type=int, default=30)
    ap.add_argument("--readlen", type=int, default=100)
    ap.add_argument("--error-rate", type=float, default=0.001)
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()

    random.seed(args.seed)
    os.makedirs(args.outdir, exist_ok=True)
    N = args.length

    ref = "".join(random.choice("ACGT") for _ in range(N))
    ref_path = os.path.join(args.outdir, "ref.fasta")
    with open(ref_path, "w") as f:
        f.write(">chr_test\n")
        for i in range(0, N, 70):
            f.write(ref[i:i + 70] + "\n")

    # plant SNPs at spread-out positions
    sample = list(ref)
    truth = {}
    for pos in [3000, 7500, 12000, 15500]:
        orig = sample[pos]
        alt = random.choice([b for b in "ACGT" if b != orig])
        sample[pos] = alt
        truth[pos + 1] = {"ref": orig, "alt": alt}   # 1-based, VCF convention
    sample = "".join(sample)

    rl, cov = args.readlen, args.coverage
    n_reads = N * cov // rl
    reads_path = os.path.join(args.outdir, "reads.fastq")
    with open(reads_path, "w") as f:
        for i in range(n_reads):
            s = random.randint(0, N - rl)
            seq = sample[s:s + rl]
            if args.error_rate:
                seq = "".join(
                    c if random.random() > args.error_rate else random.choice("ACGT")
                    for c in seq
                )
            f.write(f"@r{i}\n{seq}\n+\n{'I' * rl}\n")

    truth_path = os.path.join(args.outdir, "truth.json")
    with open(truth_path, "w") as f:
        json.dump({"reference": "ref.fasta", "snps": truth}, f, indent=2)

    print(f"reference : {ref_path} ({N} bp)")
    print(f"reads     : {reads_path} ({n_reads} reads, ~{cov}x)")
    print(f"truth     : {truth_path} ({len(truth)} planted SNPs)")
    for pos, v in truth.items():
        print(f"  chr_test:{pos} {v['ref']}>{v['alt']}")


if __name__ == "__main__":
    main()
