"""Layer 2 - Pipeline Planner (Intent -> ordered DAG of catalog steps).

The planner maps a validated ``Intent`` onto a directed acyclic graph of
``Command`` objects drawn entirely from the tool catalog. Each workflow is a
known recipe; the planner fills in the concrete file paths.

This is deliberately rule-driven rather than free LLM generation: the LLM
already did its job (NL -> Intent). Turning a known analysis into a known DAG
is exactly the part you do NOT want a model to improvise.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field

from ..command import Command
from ..intent.schema import Intent
from .catalog import TOOL_CATALOG


@dataclass
class Plan:
    analysis: str
    commands: list[Command] = field(default_factory=list)
    outputs: dict[str, str] = field(default_factory=dict)  # logical name -> path

    def final_vcf(self) -> str | None:
        return self.outputs.get("vcf")


class Planner:
    def __init__(self, workdir: str = "."):
        self.workdir = workdir

    def _p(self, *parts: str) -> str:
        return os.path.join(self.workdir, *parts)

    def plan(self, intent: Intent) -> Plan:
        if intent.analysis == "variant_calling":
            return self._plan_variant_calling(intent)
        raise ValueError(f"no planner registered for analysis {intent.analysis!r}")

    def _plan_variant_calling(self, intent: Intent) -> Plan:
        """The canonical germline variant-calling DAG:

            (qc) -> index ref -> faidx ref -> align -> sort -> index bam
                 -> mpileup -> call -> VCF
        """
        ref = intent.reference
        reads = intent.inputs
        cmds: list[Command] = []

        sam = self._p("aln.sam")
        sorted_bam = self._p("aln.sorted.bam")
        pileup = self._p("pileup.bcf")
        vcf = self._p("variants.vcf")

        # Optional QC (catalog tools marked optional). Off unless requested.
        if intent.options.get("run_qc"):
            for i, r in enumerate(reads):
                cmds.append(Command(
                    step_id=f"fastqc_{i}", tool="fastqc", subcommand="",
                    args=[r, "-o", self.workdir],
                    inputs=[r], outputs=[],
                    description="quality-control report for raw reads",
                ))

        # 1. Build the BWA index of the reference.
        cmds.append(Command(
            step_id="bwa_index", tool="bwa", subcommand="index",
            args=[ref], inputs=[ref],
            outputs=[ref + ext for ext in (".amb", ".ann", ".bwt", ".pac", ".sa")],
            description="build BWA FM-index of the reference genome",
        ))

        # 2. FASTA index for the variant caller.
        cmds.append(Command(
            step_id="faidx", tool="samtools", subcommand="faidx",
            args=[ref], inputs=[ref], outputs=[ref + ".fai"],
            description="build .fai index of the reference",
        ))

        # 3. Align reads to the reference (writes SAM to stdout).
        cmds.append(Command(
            step_id="bwa_mem", tool="bwa", subcommand="mem",
            args=["-t", str(intent.options.get("threads", 2)), ref, *reads],
            inputs=[ref, *reads], outputs=[sam], stdout_to=sam,
            description="align reads to reference with BWA-MEM",
        ))

        # 4. Sort alignments into a coordinate-sorted BAM.
        cmds.append(Command(
            step_id="samtools_sort", tool="samtools", subcommand="sort",
            args=["-o", sorted_bam, sam],
            inputs=[sam], outputs=[sorted_bam],
            description="coordinate-sort the alignments",
        ))

        # 5. Index the sorted BAM.
        cmds.append(Command(
            step_id="samtools_index", tool="samtools", subcommand="index",
            args=[sorted_bam], inputs=[sorted_bam], outputs=[sorted_bam + ".bai"],
            description="index the sorted BAM",
        ))

        # 6. Pile up read bases against the reference (writes BCF to stdout).
        cmds.append(Command(
            step_id="bcftools_mpileup", tool="bcftools", subcommand="mpileup",
            args=["-f", ref, sorted_bam, "-O", "u"],
            inputs=[ref, sorted_bam], outputs=[pileup], stdout_to=pileup,
            description="compute genotype likelihoods (pileup)",
        ))

        # 7. Call variants (writes VCF to stdout).
        cmds.append(Command(
            step_id="bcftools_call", tool="bcftools", subcommand="call",
            args=["-mv", "-O", "v", pileup],
            inputs=[pileup], outputs=[vcf], stdout_to=vcf,
            description="call SNPs/indels from the pileup",
        ))

        return Plan(analysis="variant_calling", commands=cmds, outputs={"vcf": vcf})
