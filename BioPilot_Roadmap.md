# BioPilot — Project Roadmap & Research Plan

*A natural-language interface to genomics pipelines that is verifiably reproducible and guards against LLM hallucination.*

**Author:** Baby
**Status:** Planning (no code written yet)
**Last updated:** June 19, 2026

---

## 0. The one-sentence thesis (memorize this)

> BioPilot turns plain-English requests into real, runnable genomics pipelines, and — unlike a naive "chatbot that runs commands" — it **guarantees the result is reproducible** and **catches LLM hallucinations** before they corrupt a scientific analysis.

Everything in this document serves that sentence. If a feature doesn't support the thesis, it's a distraction.

---

## 1. Why this is a real project (and not a toy)

**The product:** You type *"find variants in these FASTQ files against the human genome."* BioPilot plans the workflow, builds a real pipeline, runs it in isolated containers, and returns results plus a reproducibility manifest.

**The research contribution (what makes it publishable):** Anyone can make an LLM emit a shell command. The hard, novel problem is *trusting* it. An LLM that hallucinates one wrong `samtools` flag can silently corrupt a genomics result and nobody notices. BioPilot's contribution is the **validation + provenance layer** that makes generated pipelines verifiably correct and reproducible.

**Why it's novel:** Existing tools are either (a) manual pipeline frameworks (Nextflow, Snakemake — powerful but require expertise), or (b) LLM wrappers that emit commands with no safety net. Nobody has cleanly combined natural-language ease-of-use WITH formal reproducibility guarantees and hallucination defense. That gap is your paper.

---

## 2. Architecture — five layers

```
   User: "find variants in these FASTQ files vs human genome"
                          |
   [1] INTENT PARSER  -> structured JSON plan (NOT raw shell)
                          |
   [2] PIPELINE PLANNER -> maps intent onto a known DAG of tool steps
                          |
   [3] VALIDATOR  *** research heart *** -> checks every command vs real
                          |                   tool schemas; catches hallucinations
   [4] EXECUTOR -> generates Nextflow, runs in Docker/Conda containers
                          |
   [5] PROVENANCE RECORDER -> manifest: versions, params, checksums, digests
                          |
                   Results (VCF) + reproducibility manifest
```

### Layer 1 — Intent Parser (NL -> structured plan)
The LLM never generates raw shell. It outputs a structured intermediate representation (JSON): input type, reference genome, analysis goal, options. This indirection is what lets us verify the LLM instead of blindly trusting it.

### Layer 2 — Pipeline Planner (plan -> DAG)
Maps the structured intent onto a curated catalog of tools and a directed graph of steps (QC -> trim -> align -> sort -> call -> annotate). The LLM **selects within** this catalog; it cannot invent tools that don't exist. This is the first half of the anti-hallucination defense.

### Layer 3 — Validator (THE research heart)
Before anything runs, every generated command is checked against each tool's real parameter schema. Invalid flag? Caught. Reference/read mismatch? Caught. Dangerous operation? Blocked. **This layer produces your headline benchmark number.** (Optional: write the hot path in C++ for a performance angle.)

### Layer 4 — Executor (Nextflow + containers)
Don't reinvent a workflow engine. Generate **Nextflow** code; run every step in **Docker/Conda** containers with pinned versions. Reproducibility comes largely for free from pinned containers.

### Layer 5 — Provenance Recorder
Every run auto-emits a manifest: tool versions, exact parameters, input file checksums (hashes), container digests, timestamps, and the original NL prompt. This manifest is the artifact that lets anyone reproduce the analysis exactly.

---

## 3. Tech stack (decided)

| Concern | Choice | Notes |
|---|---|---|
| Core language | Python | Glue, parsing, orchestration |
| Performance hot path (optional) | C++ | Validator, if you want a speed claim |
| LLM | **Model-agnostic abstraction** | Develop on cloud API (Claude/GPT); validate on a local open model (Llama/Qwen) for the offline story |
| Workflow engine | Nextflow | Industry standard, reproducible |
| Containers | Docker + Conda | Version pinning = reproducibility |
| Test data | E. coli / downsampled human chr | Runs in minutes, not hours |
| Tool catalog (start) | FastQC, fastp, BWA, samtools, bcftools | A complete variant-calling pipeline |

**LLM decision rationale:** Build one interface, swappable backends. Develop with a cloud API (smartest, fastest to debug). Before the paper, prove it also runs on a local open model -> strongest reproducibility claim ("fully offline, no external dependency"), near-zero extra cost because you designed for it from day one.

---

## 4. Build plan — staged (do NOT build all layers at once)

### MVP — "it works" (target: ~2-3 weeks)
- One hardcoded workflow: **variant calling**.
- NL prompt -> structured intent -> fixed Nextflow pipeline -> runs on tiny test data -> produces a VCF + provenance manifest.
- Demo-able and screenshot-able. This is your first win.

### v2 — "it's novel" (target: ~4-6 weeks)
- Add the **Validator** + anti-hallucination layer.
- Add a **second workflow** (RNA-seq) so it's not a one-trick script.
- Now you can run the experiment that produces your paper numbers.

### v3 — "it's a paper" (target: ~8-10 weeks)
- Build the **benchmark suite** (see Section 5).
- Run cross-machine reproducibility tests.
- Write up + post bioRxiv preprint.
- Validate on a local model.

---

## 5. The measurements that make it publishable

A paper lives or dies on numbers. Yours:

1. **Reproducibility rate** — same prompt across N machines -> % identical results. Target 100%; explain *why* (containers + pinned versions + checksums).
2. **Hallucination-catch rate (HEADLINE)** — inject M invalid/dangerous tool calls -> % the Validator catches vs. % a naive LLM-to-shell baseline runs blindly. Example target headline: *"caught 94% of hallucinated errors the baseline executed."*
3. **Usability ratio** — lines of natural language vs. lines of correct pipeline code generated (e.g., "1 sentence -> 200 lines of valid Nextflow").

If you only nail ONE, make it #2 — it's the most novel and the most quotable.

---

## 6. Paper plan

**Working title:** *BioPilot: Reproducible, Hallucination-Resistant Natural-Language Genomics Pipelines*

**Structure (standard CS/bioinformatics paper):**
1. **Abstract** — problem (reproducibility crisis + LLM risk), what BioPilot does, headline numbers.
2. **Introduction** — the bioinformatics reproducibility crisis; why naive LLM-to-shell is dangerous.
3. **Related work** — Nextflow/Snakemake; Galaxy; existing LLM-for-bio attempts; gap.
4. **Methods** — the five-layer architecture (Section 2 maps directly here).
5. **Experiments** — the three measurements (Section 5).
6. **Results** — your numbers + a worked example (prompt -> pipeline -> manifest).
7. **Discussion / limitations** — honest scope.
8. **Availability** — GitHub link, license, bioRxiv DOI.

**Publishing path (in order):**
1. Build prototype + get one real benchmark number.
2. Clean GitHub repo: README, license (MIT), example, install instructions.
3. **bioRxiv preprint** (free, instant, citable — makes it "out there" with zero gatekeeping).
4. THEN approach a faculty mentor with a working repo + numbers (far stronger than pitching an idea).
5. Target venue: **JOSS** (built for student software) and/or a **bioinformatics workshop**; aim higher (Bioinformatics / GigaScience / BMC Bioinformatics) with the mentor's guidance.

**Avoid:** predatory journals (anything that emails you offering to publish for a fee). A faculty co-author is your best protection.

---

## 7. Faculty & process — the right order

- **Build first, then approach the professor.** Walking in with "I built X, here's the number" gets you a mentor + co-author. "I have an idea" gets a polite nod.
- You don't need faculty for the *building*. You want them for the *publishing*: credibility, venue access, predatory-journal protection, framing.
- A student solo paper is hard to place; a paper with your professor as senior author is normal and expected.

---

## 8. Money angles (honest)

- **Open-core + hosted version** — tool is free/open; sell a managed cloud version where users don't install anything. Standard bioinformatics-startup model.
- **Cloud credits & grants** — AWS/Google/Azure research credits; student research grants; biotech hackathons ($1k-$10k prizes reward exactly this).
- **GitHub Sponsors / consulting** — if labs adopt it, they pay for customization/support.
- **Career value (biggest real return)** — a novel, published tool with a clean GitHub beats the cash for internships, grad school, biotech jobs.

Realistic framing: "hundreds to low thousands + a great resume," not "quit school" money — unless it grows into a product, which is a separate, longer game.

---

## 9. Immediate next steps

- [ ] Confirm scope & timeline with Claude.
- [ ] Set up repo skeleton (folders for each of the 5 layers).
- [ ] Acquire tiny test dataset (E. coli reads + reference).
- [ ] Build MVP variant-calling pipeline (hardcoded).
- [ ] Get first run producing a VCF + manifest.
- [ ] THEN layer in the Validator.

---

*This is a living document. We refine as we go. Nothing gets built until you say go.*
