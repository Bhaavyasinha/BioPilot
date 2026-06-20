"""Layer 4 - Executor.

Two backends, one DAG:

* ``DirectExecutor`` runs each *already-validated* command with subprocess and
  no shell (argv list -> no injection surface). It captures stdout to the
  command's declared output file when the tool writes its result to stdout.
  This is the development / demo path used to produce a real VCF locally.

* ``generate_nextflow`` (see nextflow_gen.py) emits a real Nextflow DSL2
  pipeline with one process per step and pinned BioContainers images. That is
  the production / portable-reproducibility path (needs Nextflow + a container
  engine).

The executor refuses to run a command unless a ``ValidationReport`` with no
errors is supplied -- execution is gated on validation.
"""
from __future__ import annotations

import os
import subprocess
import time
from dataclasses import dataclass, field

from ..command import Command
from ..validator import Validator


class ExecutionError(RuntimeError):
    pass


@dataclass
class StepResult:
    step_id: str
    command: str
    returncode: int
    seconds: float
    stderr_tail: str = ""
    outputs: list[str] = field(default_factory=list)


class DirectExecutor:
    def __init__(self, workdir: str = ".", env_path: str | None = None,
                 validator: Validator | None = None):
        self.workdir = workdir
        os.makedirs(workdir, exist_ok=True)
        self.env_path = env_path
        self.validator = validator or Validator(workdir)

    def _env(self) -> dict:
        env = dict(os.environ)
        if self.env_path:
            env["PATH"] = self.env_path + os.pathsep + env.get("PATH", "")
        return env

    def run_command(self, c: Command) -> StepResult:
        # Hard gate: validate immediately before execution.
        report = self.validator.validate(c)
        if not report.ok:
            raise ExecutionError(
                f"refusing to run {c.step_id}: "
                + "; ".join(str(i) for i in report.errors)
            )

        stdout_target = None
        if c.stdout_to:
            stdout_target = open(c.stdout_to, "wb")
        t0 = time.time()
        try:
            # Plan paths are already prefixed with workdir, so run in-place.
            proc = subprocess.run(
                c.argv(),
                stdout=stdout_target or subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=self._env(),
            )
        finally:
            if stdout_target:
                stdout_target.close()
        dt = time.time() - t0
        stderr = proc.stderr.decode("utf-8", "replace") if proc.stderr else ""
        if proc.returncode != 0:
            raise ExecutionError(
                f"step {c.step_id} failed (rc={proc.returncode}):\n{stderr[-2000:]}"
            )
        return StepResult(
            step_id=c.step_id, command=c.render(), returncode=proc.returncode,
            seconds=round(dt, 3), stderr_tail=stderr[-500:],
            outputs=list(c.outputs) + ([c.stdout_to] if c.stdout_to else []),
        )

    def run_plan(self, commands: list[Command]) -> list[StepResult]:
        results = []
        for c in commands:
            results.append(self.run_command(c))
        return results
