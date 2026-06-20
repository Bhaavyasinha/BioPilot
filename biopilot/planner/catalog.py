"""The curated tool catalog.

This is the *closed world* the planner is allowed to build from. The LLM may
select tools and order them, but it can never introduce a tool that is not
here. Combined with the validator's per-flag schemas, this is the structural
reason BioPilot cannot run a hallucinated tool.

Each tool is pinned to a version and a BioContainer digest-able image. Pinned
containers are the backbone of the reproducibility guarantee.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class ToolSpec:
    name: str
    version: str                 # pinned version (verified June 2026)
    purpose: str
    consumes: tuple[str, ...]    # input file kinds
    produces: tuple[str, ...]    # output file kinds
    container: str               # BioContainers image:tag (reproducible run)
    optional: bool = False       # QC-style steps that can be skipped


# BioContainers images follow quay.io/biocontainers/<tool>:<version>--<build>.
# The build suffix is resolved at container-pull time; pinning name+version is
# the contract recorded in the manifest.
TOOL_CATALOG: dict[str, ToolSpec] = {
    "fastqc": ToolSpec(
        name="fastqc", version="0.12.1", purpose="read quality control report",
        consumes=("fastq",), produces=("html", "zip"),
        container="quay.io/biocontainers/fastqc:0.12.1", optional=True,
    ),
    "fastp": ToolSpec(
        name="fastp", version="0.24.1", purpose="adapter/quality trimming",
        consumes=("fastq",), produces=("fastq", "json", "html"),
        container="quay.io/biocontainers/fastp:0.24.1", optional=True,
    ),
    "bwa": ToolSpec(
        name="bwa", version="0.7.19", purpose="short-read alignment to reference",
        consumes=("fasta", "fastq"), produces=("sam", "index"),
        container="quay.io/biocontainers/bwa:0.7.19",
    ),
    "samtools": ToolSpec(
        name="samtools", version="1.23.1", purpose="SAM/BAM sort, index, faidx",
        consumes=("sam", "bam", "fasta"), produces=("bam", "bai", "fai"),
        container="quay.io/biocontainers/samtools:1.23.1",
    ),
    "bcftools": ToolSpec(
        name="bcftools", version="1.23.1", purpose="pileup and variant calling",
        consumes=("bam", "fasta"), produces=("bcf", "vcf"),
        container="quay.io/biocontainers/bcftools:1.23.1",
    ),
}


def container_for(tool: str) -> str:
    return TOOL_CATALOG[tool].container


def is_known_tool(tool: str) -> bool:
    return tool in TOOL_CATALOG
