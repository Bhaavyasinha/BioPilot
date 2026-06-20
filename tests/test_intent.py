from biopilot.intent import IntentParser
from biopilot.intent.schema import IntentValidationError


def test_rule_based_parses_files_and_reference():
    p = IntentParser("rule_based")
    intent = p.parse("call variants in sample.fastq against ref.fasta")
    assert intent.analysis == "variant_calling"
    assert "sample.fastq" in intent.inputs
    assert intent.reference == "ref.fasta"


def test_known_reference_name():
    p = IntentParser("rule_based")
    intent = p.parse("find SNPs in reads.fq vs the human genome",
                     inputs=["reads.fq"])
    assert intent.reference == "GRCh38"


def test_cli_overrides_win():
    p = IntentParser("rule_based")
    intent = p.parse("do variant calling", inputs=["a.fastq"], reference="r.fa")
    assert intent.inputs == ["a.fastq"]
    assert intent.reference == "r.fa"


def test_qc_option_detected():
    p = IntentParser("rule_based")
    intent = p.parse("variant calling with quality trimming", inputs=["a.fastq"],
                     reference="r.fa")
    assert intent.options.get("run_qc") is True
