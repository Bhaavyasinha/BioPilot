"""BioPilot: natural-language genomics pipelines that are verifiably
reproducible and hallucination-resistant.

Five layers, each a sub-package:

    1. intent      NL prompt  -> structured Intent (JSON)
    2. planner     Intent     -> DAG of catalog tool steps
    3. validator   DAG steps  -> validated commands (anti-hallucination heart)
    4. executor    DAG        -> real run (direct backend) + generated Nextflow
    5. provenance  run        -> reproducibility manifest
"""

__version__ = "0.1.0"
