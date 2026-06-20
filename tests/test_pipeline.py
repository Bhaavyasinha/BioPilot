from biopilot.intent import IntentParser
from biopilot.planner import Planner
from biopilot.validator import Validator
from biopilot.executor import generate_nextflow
from biopilot.benchmark import run_benchmark


def test_plan_is_valid_and_complete():
    intent = IntentParser("rule_based").parse(
        "call variants", inputs=["reads.fastq"], reference="ref.fasta")
    plan = Planner("out").plan(intent)
    step_ids = [c.step_id for c in plan.commands]
    assert step_ids == ["bwa_index", "faidx", "bwa_mem", "samtools_sort",
                        "samtools_index", "bcftools_mpileup", "bcftools_call"]
    assert Validator("out").validate_plan(plan.commands).ok


def test_nextflow_generation():
    intent = IntentParser("rule_based").parse(
        "call variants", inputs=["reads.fastq"], reference="ref.fasta")
    plan = Planner("out").plan(intent)
    nf = generate_nextflow(plan.commands, prompt="call variants")
    assert "nextflow.enable.dsl=2" in nf
    assert "quay.io/biocontainers/bwa" in nf
    assert nf.count("process P_") == len(plan.commands)


def test_benchmark_catches_all_bad():
    r = run_benchmark()
    assert r.n_caught == r.n_bad
    assert r.n_false_positive == 0
    assert r.baseline_caught == 0
