# BioPilot

**Natural-language genomics pipelines that are verifiably reproducible and hallucination-resistant.**

> You type *"find variants in these reads against the reference genome."*
> BioPilot parses the request into a structured plan, **validates every
> generated command against the real tool schemas**, runs a real
> variant-calling pipeline, and returns the results plus a
> **reproducibility manifest** — versions, parameters, and SHA-256 checksums
> of every file.

Anyone can make an LLM emit a shell command. The hard, novel problem is
*trusting* it: a single hallucinated `samtools` flag can silently corrupt a
scientific result and nobody notices. BioPilot's contribution is the
**validation + provenance layer** that makes generated pipelines verifiably
correct and reproducible.

---

## Why this is different

Existing tools sit at two extremes:

- **Manual workflow frameworks** (Nextflow, Snakemake) — powerful and
  reproducible, but require real bioinformatics expertise to write.
- **LLM-to-shell wrappers** — easy to talk to, but they run whatever the model
  emits, with no safety net.

BioPilot combines natural-language ease-of-use **with** formal reproducibility
guarantees **and** an explicit hallucination defense. That combination is the
gap this project fills.

---

## The five-layer architecture

```
   User: "find variants in these reads vs the reference"
                          |
   [1] INTENT PARSER   -> structured JSON Intent (never raw shell)
                          |
   [2] PIPELINE PLANNER -> ordered DAG drawn ONLY from a curated tool catalog
                          |
   [3] VALIDATOR  *** research heart *** -> every command checked vs the real
                          |                  tool flag schemas; hallucinations blocked
   [4] EXECUTOR -> runs the validated commands AND emits a pinned-container Nextflow file
                          |
   [5] PROVENANCE RECORDER -> manifest: versions, params, checksums, prompt
                          |
                   Results (VCF) + reproducibility manifest
```

| Layer | Package | What it guarantees |
|-------|---------|--------------------|
| 1. Intent parser | `biopilot/intent` | The LLM emits a schema-checked JSON Intent, never shell. A malformed intent stops here. |
| 2. Planner | `biopilot/planner` | The plan is built only from a **closed** tool catalog; no invented tools. |
| 3. **Validator** | `biopilot/validator` | Every flag is checked against the real per-subcommand schema; bad flags, wrong file stages, shell injection, and destructive ops are blocked **before** anything runs. |
| 4. Executor | `biopilot/executor` | Runs commands with no shell (no injection surface); also generates portable Nextflow with pinned BioContainers. |
| 5. Provenance | `biopilot/provenance` | Emits a manifest that lets anyone reproduce the run exactly. |

The anti-hallucination defense is structural, in two parts: the planner can
only select tools that exist (closed world), and the validator rejects any
flag or file-stage that does not match the real tool schema.

---

## Install

BioPilot runs **fully offline** with its rule-based intent parser — no API key
required. The reproducible toolchain is pinned in `environment.yml`:

```bash
# create the pinned environment (conda / mamba / micromamba)
mamba env create -f environment.yml
conda activate biopilot
pip install -e .
```

Tool versions are pinned to current bioconda releases (verified June 2026):
Nextflow 26.4.3, BWA 0.7.19, samtools 1.23.1, bcftools 1.23.1, fastp 0.24.1,
FastQC 0.12.1.

---

## Quickstart

```bash
# 1. make a tiny self-contained dataset with KNOWN planted variants
python data/make_test_data.py --outdir data/test --seed 42

# 2. run the whole pipeline from a plain-English request
biopilot run "find variants in these reads against the reference genome" \
    --inputs data/test/reads.fastq \
    --reference data/test/ref.fasta \
    --outdir runs/demo

# 3. see the hallucination-catch benchmark
biopilot benchmark
```

Outputs land in `runs/demo/`:

- `variants.vcf` — the called variants
- `pipeline.nf` — the generated, portable Nextflow pipeline (pinned containers)
- `manifest.json` / `manifest.md` — the reproducibility manifest

A complete worked example is checked in under [`examples/`](examples/).

---

## The headline measurement

`biopilot benchmark` runs a labelled suite of commands — valid ones plus the
kinds of mistakes LLMs actually make — through the validator, and compares
against a naive "LLM → shell" baseline that would run everything:

```
Injected bad commands : 12
Caught by BioPilot    : 12  (100%)
Caught by naive LLM->shell baseline : 0  (0%)
False positives (valid blocked)     : 0

By error category:
  destructive_command    1/1
  input_clobber          1/1
  missing_value          1/1
  shell_metacharacter    1/1
  stage_mismatch         2/2
  unknown_flag           3/3
  unknown_subcommand     1/1
  unknown_tool           1/1
  wrong_file_kind        1/1
```

**BioPilot blocked 100% of hallucinated/dangerous commands the baseline would
have executed, with zero false positives.**

## Correctness, against ground truth

Because the test data plants variants at known positions, correctness is
*measurable*, not just "it ran." On the bundled dataset:

| Metric | Result |
|--------|--------|
| Recall (planted SNPs recovered) | **4 / 4** |
| Precision (called variants that are true) | **4 / 4** |
| Allele correctness (REF>ALT) | 4 / 4 exact |

---

## Reproducibility manifest

Every run emits a manifest recording the prompt, the parsed intent, every
command with its pinned container, the resolved tool versions, and a SHA-256
checksum of every input and output. Hand the manifest to a colleague and they
can reproduce the analysis byte-for-byte. See
[`examples/manifest.md`](examples/manifest.md).

---

## Project layout

```
biopilot/
  intent/      Layer 1 - NL -> structured Intent (rule-based + LLM backends)
  planner/     Layer 2 - Intent -> DAG, plus the curated tool catalog
  validator/   Layer 3 - the anti-hallucination heart (per-flag schemas)
  executor/    Layer 4 - direct runner + Nextflow generator
  provenance/  Layer 5 - the reproducibility manifest
  pipeline.py  end-to-end orchestration
  cli.py       `biopilot run` / `biopilot benchmark`
  benchmark.py the hallucination-catch suite
data/          synthetic ground-truth test-data generator
tests/         pytest suite (intent, validator, planner, benchmark)
examples/      a complete worked run (VCF + manifest + generated Nextflow)
```

---

## Model-agnostic by design

The intent parser is one interface (`LLMBackend`) with swappable backends:

- `rule_based` — deterministic, offline, no API key (the default; also the
  baseline the LLM backends are measured against).
- `claude` — cloud backend for highest parse quality.
- `local` — a local open model (Llama/Qwen via an OpenAI-compatible server)
  for the fully-offline reproducibility story.

Whatever the backend, the output passes through the same schema gate and the
same validator — the trust guarantees do not depend on which model is used.

---

## Status & roadmap

This is the MVP: a complete, working variant-calling slice across all five
layers, with the validator and benchmark in place. Next milestones:

- A second workflow (RNA-seq) so it is not a one-trick pipeline.
- Cross-machine reproducibility tests (same prompt, N machines, identical results).
- Validation on a local open model.
- Write-up + bioRxiv preprint.

See `BioPilot_Roadmap.md` for the full plan.

## License

MIT — see [LICENSE](LICENSE).
