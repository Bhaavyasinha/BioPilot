"""End-to-end orchestration: prompt -> parse -> plan -> validate -> execute
-> record. This is the thin conductor that wires the five layers together.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field

from .intent import IntentParser
from .planner import Planner
from .validator import Validator
from .executor import DirectExecutor, generate_nextflow
from .provenance import ProvenanceRecorder
from .provenance.recorder import collect_tool_versions


@dataclass
class RunArtifacts:
    intent: dict
    plan: list
    validation: dict
    manifest: dict
    vcf: str | None
    nextflow_path: str
    manifest_json: str
    manifest_md: str
    executed: bool


def run(prompt: str, *, inputs=None, reference=None, outdir="run",
        backend="rule_based", env_path=None, execute=True) -> RunArtifacts:
    os.makedirs(outdir, exist_ok=True)

    # 1. parse
    intent = IntentParser(backend).parse(prompt, inputs=inputs, reference=reference)

    # 2. plan
    plan = Planner(workdir=outdir).plan(intent)

    # 3. validate (gate)
    validator = Validator(workdir=outdir)
    report = validator.validate_plan(plan.commands)

    # 4a. always emit the portable Nextflow pipeline artifact
    nf = generate_nextflow(plan.commands, prompt=prompt)
    nf_path = os.path.join(outdir, "pipeline.nf")
    with open(nf_path, "w") as f:
        f.write(nf)

    # 4b. execute locally if validation passed and execution requested
    results = None
    executed = False
    if execute and report.ok:
        execu = DirectExecutor(workdir=outdir, env_path=env_path, validator=validator)
        results = execu.run_plan(plan.commands)
        executed = True

    # 5. record provenance
    rec = ProvenanceRecorder(workdir=outdir)
    manifest = rec.build(
        intent=intent, commands=plan.commands, validation=report.to_dict(),
        step_results=results,
        tool_versions=collect_tool_versions(env_path) if executed else {},
    )
    mj = os.path.join(outdir, "manifest.json")
    mm = os.path.join(outdir, "manifest.md")
    rec.write(manifest, mj, mm)

    return RunArtifacts(
        intent=intent.to_dict(), plan=[c.to_dict() for c in plan.commands],
        validation=report.to_dict(), manifest=manifest,
        vcf=plan.final_vcf() if executed else None,
        nextflow_path=nf_path, manifest_json=mj, manifest_md=mm, executed=executed,
    )
