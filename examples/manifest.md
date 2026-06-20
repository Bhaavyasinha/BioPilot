# BioPilot reproducibility manifest

- **BioPilot:** 0.1.0
- **Generated (UTC):** 2026-06-19T09:25:59.190653+00:00
- **Prompt:** 'find variants in these reads against the reference genome'
- **Analysis:** variant_calling
- **Validation:** PASSED (0 errors, 0 warnings)

## Pipeline steps

1. `bwa index data/test/ref.fasta`
   - container: `quay.io/biocontainers/bwa:0.7.19`
2. `samtools faidx data/test/ref.fasta`
   - container: `quay.io/biocontainers/samtools:1.23.1`
3. `bwa mem -t 2 data/test/ref.fasta data/test/reads.fastq > runs/demo/aln.sam`
   - container: `quay.io/biocontainers/bwa:0.7.19`
4. `samtools sort -o runs/demo/aln.sorted.bam runs/demo/aln.sam`
   - container: `quay.io/biocontainers/samtools:1.23.1`
5. `samtools index runs/demo/aln.sorted.bam`
   - container: `quay.io/biocontainers/samtools:1.23.1`
6. `bcftools mpileup -f data/test/ref.fasta runs/demo/aln.sorted.bam -O u > runs/demo/pileup.bcf`
   - container: `quay.io/biocontainers/bcftools:1.23.1`
7. `bcftools call -mv -O v runs/demo/pileup.bcf > runs/demo/variants.vcf`
   - container: `quay.io/biocontainers/bcftools:1.23.1`

## Inputs (sha256)

- `reads.fastq` — `adfcbaa89c3f23da875495efba81aaa9dbf3469044892bd20b484f25a07a4aeb`
- `ref.fasta` — `8c90d1ebe43650e738160bedad7f5fa45b9b8bf9a9f9cbd9fee0e8171d86f68f`
- `aln.sam` — `6237f14f976012c34c7594cb0e4a1eefdf8d5b60e141c2bc9f41029f2302785d`
- `aln.sorted.bam` — `728406455db6befecad500b101223ada70aec340351f1f5fb5f97f72cdae596d`
- `pileup.bcf` — `a5aade2dd97329527ac39b8086ac315ba505dce2716aefe4afff4bba14032c3b`

## Outputs (sha256)

- `ref.fasta.amb` — `09d01496ec97842a2b03e30210ce209806bfcc7782329c385c7fd3ea18a08c9b`
- `ref.fasta.ann` — `8916f3b9ab1b6ac487d6cd06e94f54c7a96d829774b4918c8e825f1f7d16e83e`
- `ref.fasta.bwt` — `40ea69d2068696182fb6f31919216cf14cc217775be44e0e261f9b4afec0ca3d`
- `ref.fasta.fai` — `282e4d573b32c224f4c06c06730ac4331a8567306baec3a11f93a3d40ba4d47d`
- `ref.fasta.pac` — `ff296e45cc32dcdd2632c086cfe96f544ada002c7a7ebb1c028a6c3e8c7fea29`
- `ref.fasta.sa` — `31f51cb64db0622db42edfe61fe248f238ff6cc1dd02eafaf683f8a25abd02fe`
- `aln.sam` — `6237f14f976012c34c7594cb0e4a1eefdf8d5b60e141c2bc9f41029f2302785d`
- `aln.sorted.bam` — `728406455db6befecad500b101223ada70aec340351f1f5fb5f97f72cdae596d`
- `aln.sorted.bam.bai` — `2876c30cb3604d4393d1341ba10e55df8605ec5fbf0bfd01a41e48d5c3ef7f2d`
- `pileup.bcf` — `a5aade2dd97329527ac39b8086ac315ba505dce2716aefe4afff4bba14032c3b`
- `variants.vcf` — `d7df0eb654f70ab51edfd654c440e93297c27beff83d81f4be69827dc0b9bd56`
