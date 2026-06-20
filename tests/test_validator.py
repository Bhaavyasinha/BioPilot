from biopilot.command import Command
from biopilot.validator import Validator


V = Validator(".")


def test_valid_command_passes():
    c = Command("s", "bwa", "mem", ["-t", "2", "ref.fasta", "reads.fastq"],
                inputs=["ref.fasta", "reads.fastq"], outputs=["a.sam"], stdout_to="a.sam")
    assert V.validate(c).ok


def test_invented_flag_blocked():
    c = Command("s", "bwa", "mem", ["--turbo", "ref.fasta", "reads.fastq"],
                inputs=["ref.fasta", "reads.fastq"])
    rep = V.validate(c)
    assert not rep.ok
    assert any(i.code == "unknown_flag" for i in rep.errors)


def test_unknown_tool_blocked():
    c = Command("s", "genomagic", "run", ["x"], inputs=["x"])
    assert any(i.code == "unknown_tool" for i in V.validate(c).errors)


def test_unknown_subcommand_blocked():
    c = Command("s", "samtools", "supercall", ["a.bam"], inputs=["a.bam"])
    assert any(i.code == "unknown_subcommand" for i in V.validate(c).errors)


def test_wrong_reference_kind_blocked():
    c = Command("s", "bcftools", "mpileup", ["-f", "reads.fastq", "a.bam"],
                inputs=["reads.fastq", "a.bam"])
    assert any(i.code == "wrong_file_kind" for i in V.validate(c).errors)


def test_stage_mismatch_blocked():
    c = Command("s", "bcftools", "call", ["-mv", "reads.fastq"],
                inputs=["reads.fastq"])
    assert any(i.code == "stage_mismatch" for i in V.validate(c).errors)


def test_shell_metacharacter_blocked():
    c = Command("s", "samtools", "sort", ["-o", "x.bam; rm -rf /", "a.sam"],
                inputs=["a.sam"], outputs=["x.bam; rm -rf /"])
    assert any(i.code == "shell_metacharacter" for i in V.validate(c).errors)


def test_destructive_blocked():
    c = Command("s", "rm", "", ["-rf", "/data"])
    assert any(i.code == "destructive_command" for i in V.validate(c).errors)


def test_input_clobber_blocked():
    c = Command("s", "samtools", "sort", ["-o", "ref.fasta", "a.sam"],
                inputs=["a.sam", "ref.fasta"], outputs=["ref.fasta"])
    assert any(i.code == "input_clobber" for i in V.validate(c).errors)


def test_combined_short_flags_ok():
    # -mv is two boolean flags; -O u is a value flag -- must all parse cleanly
    c = Command("s", "bcftools", "call", ["-mv", "-O", "v", "pileup.bcf"],
                inputs=["pileup.bcf"], outputs=["out.vcf"], stdout_to="out.vcf")
    assert V.validate(c).ok
