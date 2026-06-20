"""Layer 1 - Intent Parser (natural language -> structured Intent)."""
from __future__ import annotations

import json
import os
import re
from abc import ABC, abstractmethod

from .schema import Intent, INTENT_JSON_SCHEMA, validate_intent

SYSTEM_PROMPT = """You are the intent parser for BioPilot, a genomics pipeline system.
Convert the user's request into a single JSON object matching this schema:

{schema}

Rules:
- Output ONLY the JSON object, no prose, no code fences.
- "analysis" MUST be one of the enum values. Do not invent analyses.
- "inputs" are the FASTQ read files the user provided.
- "reference" is the reference genome path or id.
- Put any extra knobs under "options".
"""


class LLMBackend(ABC):
    name = "abstract"

    @abstractmethod
    def complete(self, system: str, user: str) -> str:
        ...


class RuleBasedBackend(LLMBackend):
    name = "rule_based"
    FASTQ_RE = re.compile(r"\S+\.(?:fastq|fq)(?:\.gz)?(?![\w])", re.IGNORECASE)
    FASTA_RE = re.compile(r"\S+\.(?:fasta|fa|fna)(?:\.gz)?(?![\w])", re.IGNORECASE)
    KNOWN_REFERENCES = {
        "human": "GRCh38", "grch38": "GRCh38", "hg38": "GRCh38",
        "e. coli": "ecoli_K12", "e.coli": "ecoli_K12", "ecoli": "ecoli_K12",
    }

    def complete(self, system: str, user: str) -> str:
        text = user.strip()
        low = text.lower()
        analysis = "variant_calling"
        inputs = self.FASTQ_RE.findall(text)
        fasta = self.FASTA_RE.findall(text)
        reference = ""
        if fasta:
            reference = fasta[0]
        else:
            for key, ref in self.KNOWN_REFERENCES.items():
                if key in low:
                    reference = ref
                    break
        options = {}
        if "qc" in low or "quality" in low or "trim" in low:
            options["run_qc"] = True
        return json.dumps({"analysis": analysis, "inputs": inputs,
                           "reference": reference, "options": options, "raw_prompt": text})


class ClaudeBackend(LLMBackend):
    name = "claude"

    def __init__(self, model: str = "claude-sonnet-4-6"):
        self.model = model

    def complete(self, system: str, user: str) -> str:
        try:
            import anthropic
        except ImportError as e:
            raise RuntimeError("pip install 'biopilot[llm]' to use ClaudeBackend") from e
        client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
        msg = client.messages.create(model=self.model, max_tokens=1024,
                                      system=system,
                                      messages=[{"role": "user", "content": user}])
        return msg.content[0].text


class LocalModelBackend(LLMBackend):
    name = "local"

    def __init__(self, model: str = "qwen2.5", base_url: str = "http://localhost:11434/v1"):
        self.model = model
        self.base_url = base_url

    def complete(self, system: str, user: str) -> str:
        try:
            from openai import OpenAI
        except ImportError as e:
            raise RuntimeError("pip install 'biopilot[llm]' to use LocalModelBackend") from e
        client = OpenAI(base_url=self.base_url, api_key="not-needed")
        resp = client.chat.completions.create(model=self.model, messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user}])
        return resp.choices[0].message.content


_BACKENDS = {"rule_based": RuleBasedBackend, "claude": ClaudeBackend, "local": LocalModelBackend}


def get_backend(name: str = "rule_based") -> LLMBackend:
    if name not in _BACKENDS:
        raise ValueError(f"unknown backend {name!r}; choose from {list(_BACKENDS)}")
    return _BACKENDS[name]()


def _extract_json(text: str) -> dict:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?", "", text).rsplit("```", 1)[0].strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        m = re.search(r"\{.*\}", text, re.DOTALL)
        if not m:
            raise
        return json.loads(m.group(0))


class IntentParser:
    def __init__(self, backend="rule_based"):
        self.backend = get_backend(backend) if isinstance(backend, str) else backend

    def parse(self, prompt, inputs=None, reference=None) -> Intent:
        system = SYSTEM_PROMPT.format(schema=json.dumps(INTENT_JSON_SCHEMA, indent=2))
        raw = self.backend.complete(system, prompt)
        data = _extract_json(raw)
        if inputs:
            data["inputs"] = inputs
        if reference:
            data["reference"] = reference
        data.setdefault("raw_prompt", prompt)
        return validate_intent(data)
