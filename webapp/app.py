"""BioPilot web app — a live demo of the real safety-checker.

This is a small Flask server that exposes BioPilot's actual code over HTTP:
  /api/parse      plain-English  -> structured plan (real rule-based parser)
  /api/check      a command      -> validated by the REAL validator
  /api/benchmark  runs the real hallucination-catch benchmark

The genomics *execution* (bwa/samtools) is simulated for the public demo, but
the safety-checker — the novel research contribution — runs for real here.
"""
import os
import shlex
import sys

from flask import Flask, jsonify, render_template, request

sys.path.insert(0, os.path.dirname(__file__))

from biopilot.command import Command           # noqa: E402
from biopilot.validator import Validator        # noqa: E402
from biopilot.benchmark import run_benchmark     # noqa: E402
from biopilot.intent import IntentParser         # noqa: E402
from biopilot.planner import Planner             # noqa: E402

app = Flask(__name__)
_validator = Validator(workdir=".")
_parser = IntentParser("rule_based")

_FILE_EXTS = (".fasta", ".fa", ".fna", ".fastq", ".fq", ".sam", ".bam",
              ".bcf", ".vcf", ".gz")


def _looks_like_file(tok: str) -> bool:
    return tok.lower().endswith(_FILE_EXTS)


def _string_to_command(text: str) -> Command:
    """Turn a typed command line into a structured Command for validation."""
    parts = shlex.split(text.strip())
    if not parts:
        return Command("demo", "", "", [])
    tool = parts[0]
    rest = parts[1:]
    # treat a non-flag second token as the subcommand (bwa mem, samtools sort)
    subcommand = ""
    if rest and not rest[0].startswith("-"):
        subcommand = rest[0]
        rest = rest[1:]
    inputs = [t for t in rest if _looks_like_file(t)]
    return Command("demo", tool, subcommand, rest, inputs=inputs)


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/check", methods=["POST"])
def api_check():
    text = (request.json or {}).get("command", "")
    cmd = _string_to_command(text)
    report = _validator.validate(cmd)
    return jsonify({
        "command": text,
        "ok": report.ok,
        "issues": [
            {"severity": i.severity.value, "message": i.message, "code": i.code}
            for i in report.issues
        ],
    })


@app.route("/api/parse", methods=["POST"])
def api_parse():
    prompt = (request.json or {}).get("prompt", "")
    inputs = ["reads.fastq"]
    reference = "ref.fasta"
    intent = _parser.parse(prompt, inputs=inputs, reference=reference)
    plan = Planner(workdir="run").plan(intent)
    steps = [{"id": c.step_id, "command": c.render(), "tool": c.tool}
             for c in plan.commands]
    # simulated execution result (genomics tools not run on the public demo)
    variants = [
        {"chrom": "chr_test", "pos": 3001, "ref": "T", "alt": "G", "qual": 191.4},
        {"chrom": "chr_test", "pos": 7501, "ref": "T", "alt": "G", "qual": 189.4},
        {"chrom": "chr_test", "pos": 12001, "ref": "A", "alt": "T", "qual": 193.4},
        {"chrom": "chr_test", "pos": 15501, "ref": "T", "alt": "C", "qual": 190.4},
    ]
    return jsonify({"intent": intent.to_dict(), "steps": steps, "variants": variants})


@app.route("/api/benchmark", methods=["GET"])
def api_benchmark():
    r = run_benchmark()
    return jsonify({
        "n_bad": r.n_bad, "n_caught": r.n_caught,
        "false_positives": r.n_false_positive,
        "baseline_caught": r.baseline_caught,
        "rate": round(100.0 * r.n_caught / r.n_bad) if r.n_bad else 0,
        "per_category": r.per_category,
    })


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
