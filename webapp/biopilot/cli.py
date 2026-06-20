"""BioPilot command-line interface.

    biopilot run "find variants in these reads vs the reference" \\
        --inputs reads.fastq --reference ref.fasta --outdir run/

    biopilot benchmark        # hallucination-catch benchmark (headline number)
"""
from __future__ import annotations

import argparse
import json
import sys


def _cmd_run(args) -> int:
    from .pipeline import run
    art = run(
        args.prompt, inputs=args.inputs, reference=args.reference,
        outdir=args.outdir, backend=args.backend, env_path=args.env_path,
        execute=not args.no_execute,
    )
    print("Parsed intent:")
    print(json.dumps(art.intent, indent=2))
    v = art.validation
    status = "PASSED" if v["ok"] else "FAILED"
    print(f"\nValidation: {status} ({v['n_errors']} errors, {v['n_warnings']} warnings)")
    for issue in v["issues"]:
        print(f"  - {issue['severity'].upper()}: {issue['message']} ({issue['code']})")
    print(f"\nGenerated Nextflow: {art.nextflow_path}")
    print(f"Manifest: {art.manifest_json}")
    if art.executed:
        print(f"\nRun complete. VCF: {art.vcf}")
    elif not v["ok"]:
        print("\nExecution blocked by validation errors (this is the safety net working).")
    else:
        print("\nExecution skipped (--no-execute).")
    return 0 if (v["ok"] or args.no_execute) else 2


def _cmd_benchmark(args) -> int:
    from .benchmark import run_benchmark, print_report
    report = run_benchmark()
    print_report(report)
    return 0


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="biopilot", description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)

    r = sub.add_parser("run", help="run a natural-language analysis")
    r.add_argument("prompt", help="natural-language request")
    r.add_argument("--inputs", nargs="*", default=None, help="FASTQ read files")
    r.add_argument("--reference", default=None, help="reference FASTA path")
    r.add_argument("--outdir", default="run", help="output directory")
    r.add_argument("--backend", default="rule_based",
                   choices=["rule_based", "claude", "local"])
    r.add_argument("--env-path", default=None,
                   help="prepend this dir to PATH so the tools are found")
    r.add_argument("--no-execute", action="store_true",
                   help="plan + validate + emit Nextflow, but do not run")
    r.set_defaults(func=_cmd_run)

    b = sub.add_parser("benchmark", help="hallucination-catch benchmark")
    b.set_defaults(func=_cmd_benchmark)

    args = p.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
