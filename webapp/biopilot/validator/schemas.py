"""Per-subcommand parameter schemas.

These are the ground truth the validator checks generated commands against.
A flag that is not in the schema for its subcommand is, by definition, a
hallucination -- the model invented it. ``takes_value`` lets us parse short
flag clusters (e.g. ``-mv`` = two boolean flags, ``-Ou`` = ``-O u``).

The flag sets below are drawn from the real tool man pages (bwa 0.7.x,
samtools 1.2x, bcftools 1.2x). They need not be 100% exhaustive to be useful,
but the closer they are to reality the lower the false-positive rate.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class CommandSchema:
    tool: str
    subcommand: str
    # flag -> takes_value
    flags: dict[str, bool] = field(default_factory=dict)
    min_positional: int = 0
    # expected file "kind" of each leading positional, by index (best-effort)
    positional_kinds: tuple[str, ...] = ()


def _s(tool, sub, flags, min_pos=0, kinds=()):
    return CommandSchema(tool, sub, flags, min_pos, kinds)


# ---------------------------------------------------------------------------
# bwa
# ---------------------------------------------------------------------------
BWA_INDEX = _s("bwa", "index", {
    "-a": True, "-p": True, "-b": True, "-6": False,
}, min_pos=1, kinds=("fasta",))

BWA_MEM = _s("bwa", "mem", {
    "-t": True, "-k": True, "-w": True, "-d": True, "-r": True, "-c": True,
    "-A": True, "-B": True, "-O": True, "-E": True, "-L": True, "-U": True,
    "-R": True, "-T": True, "-v": True, "-o": True, "-I": True, "-m": True,
    "-p": False, "-a": False, "-C": False, "-H": True, "-M": False,
    "-P": False, "-S": False, "-Y": False, "-j": False, "-5": False,
}, min_pos=2, kinds=("fasta", "fastq"))

# ---------------------------------------------------------------------------
# samtools
# ---------------------------------------------------------------------------
SAMTOOLS_SORT = _s("samtools", "sort", {
    "-l": True, "-m": True, "-o": True, "-O": True, "-T": True, "-@": True,
    "-t": True, "-n": False, "-K": True, "--threads": True,
}, min_pos=1, kinds=("sam_or_bam",))

SAMTOOLS_INDEX = _s("samtools", "index", {
    "-b": False, "-c": False, "-m": True, "-@": True, "--threads": True,
}, min_pos=1, kinds=("bam",))

SAMTOOLS_FAIDX = _s("samtools", "faidx", {
    "-o": True, "--fai-idx": True, "--gzi-idx": True, "-r": True,
}, min_pos=1, kinds=("fasta",))

SAMTOOLS_VIEW = _s("samtools", "view", {
    "-b": False, "-h": False, "-S": False, "-o": True, "-O": True, "-@": True,
    "-q": True, "-f": True, "-F": True, "-c": False, "-T": True, "--threads": True,
}, min_pos=1, kinds=("sam_or_bam",))

# ---------------------------------------------------------------------------
# bcftools
# ---------------------------------------------------------------------------
BCFTOOLS_MPILEUP = _s("bcftools", "mpileup", {
    "-f": True, "-O": True, "-o": True, "-r": True, "-R": True, "-b": True,
    "-q": True, "-Q": True, "-d": True, "-a": True, "-g": True, "-G": True,
    "--threads": True, "-B": False, "-E": False, "-I": False, "-x": False,
    "--max-depth": True, "--min-MQ": True, "--min-BQ": True,
}, min_pos=1, kinds=("bam",))

BCFTOOLS_CALL = _s("bcftools", "call", {
    "-O": True, "-o": True, "-r": True, "-R": True, "-s": True, "-G": True,
    "-p": True, "-P": True, "--ploidy": True, "-V": True, "-f": True,
    "-t": True, "-T": True, "--threads": True,
    "-m": False, "-v": False, "-c": False, "-A": False, "-X": False, "-N": False,
}, min_pos=1, kinds=("bcf_or_vcf",))

COMMAND_SCHEMAS: dict[tuple[str, str], CommandSchema] = {
    ("bwa", "index"): BWA_INDEX,
    ("bwa", "mem"): BWA_MEM,
    ("samtools", "sort"): SAMTOOLS_SORT,
    ("samtools", "index"): SAMTOOLS_INDEX,
    ("samtools", "faidx"): SAMTOOLS_FAIDX,
    ("samtools", "view"): SAMTOOLS_VIEW,
    ("bcftools", "mpileup"): BCFTOOLS_MPILEUP,
    ("bcftools", "call"): BCFTOOLS_CALL,
    # fastqc has no subcommand
    ("fastqc", ""): _s("fastqc", "", {"-o": True, "--outdir": True, "-t": True,
                                       "--threads": True, "-q": False, "--quiet": False},
                       min_pos=1, kinds=("fastq",)),
    ("fastp", ""): _s("fastp", "", {"-i": True, "-I": True, "-o": True, "-O": True,
                                    "-j": True, "-h": True, "-w": True, "-q": True},
                      min_pos=0),
}


# File-kind helpers used by semantic checks.
FILE_KIND_SUFFIXES = {
    "fasta": (".fa", ".fasta", ".fna"),
    "fastq": (".fastq", ".fq", ".fastq.gz", ".fq.gz"),
    "sam": (".sam",),
    "bam": (".bam",),
    "bcf": (".bcf",),
    "vcf": (".vcf", ".vcf.gz"),
}


def kind_of(path: str) -> str | None:
    low = path.lower()
    for kind, sufs in FILE_KIND_SUFFIXES.items():
        if low.endswith(sufs):
            return kind
    return None
