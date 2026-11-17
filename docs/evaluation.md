# Helix AI — Benchmark Evaluation Report

- **Evaluation Mode:** `offline`
- **Benchmark Corpus Size:** `25` manually reviewed biomedical research questions
- **Methodology:** All 25 benchmark questions are strictly separated from the 5 development queries. Each of the five quality dimensions is measured and reported independently without combining scores into an artificial aggregate.

## Independent Evaluation Results

| Dimension | Correct | Incorrect | Denominator | Score (%) |
| :--- | :---: | :---: | :---: | :---: |
| A. Retrieval Relevance | 24 | 1 | 25 | **96.00%** |
| B. Publication–GEO Linking Accuracy | 24 | 1 | 25 | **96.00%** |
| C. Extraction Accuracy | 99 | 1 | 100 | **99.00%** |
| D. Citation Validity (PMID & GSE) | 48 | 0 | 48 | **100.00%** |
| E. Claim-Level Grounding | 64 | 78 | 142 | **45.07%** |

## Claim-Level Grounding Status Breakdown

| Verification Status | Field Count |
| :--- | :---: |
| Partially supported | 21 |
| Source unavailable | 108 |
| Unsupported | 57 |
| Verified | 64 |

## Observed Error Categories & Diagnostic Findings

### A. Retrieval Relevance
- `BENCH-14: Expected PMID 20473322 not retrieved for 'Transcriptional dynamics during human induced pluripotent stem cell reprogramming'`

### B. Publication–GEO Linking Accuracy
- `BENCH-01 (PMID 24925914): Expected GEO ['GSE57872'], got []`

### C. Extraction Accuracy
- `BENCH-09.experimental_methodology: Expected 'Pretreatment tumor RNA sequencing', got 'Bulk mRNA sequencing of tumor biopsies'`

### D. Citation Validity (PMID & GSE)
- No errors observed in this dimension.

### E. Claim-Level Grounding
- `BENCH-01.organism: Status=Unsupported (Extracted value is not supported by the cited passage (token_overlap=0.00).)`
- `BENCH-01.experimental_methodology: Status=Partially supported (Passage located in source (sim=1.00), but claim involves paraphrasing/synthesis (overlap=0.33).)`
- `BENCH-01.genes_or_biomarkers: Status=Unsupported (Extracted value is not supported by the cited passage (token_overlap=0.00).)`
- `BENCH-02.organism: Status=Unsupported (Extracted value is not supported by the cited passage (token_overlap=0.00).)`
- `BENCH-02.experimental_methodology: Status=Partially supported (Passage located in source (sim=1.00), but claim involves paraphrasing/synthesis (overlap=0.20).)`
- `BENCH-02.genes_or_biomarkers: Status=Unsupported (Extracted value is not supported by the cited passage (token_overlap=0.33).)`
- `BENCH-03.organism: Status=Unsupported (Extracted value is not supported by the cited passage (token_overlap=0.00).)`
- `BENCH-03.experimental_methodology: Status=Unsupported (Extracted value is not supported by the cited passage (token_overlap=0.00).)`
- `BENCH-03.genes_or_biomarkers: Status=Unsupported (Extracted value is not supported by the cited passage (token_overlap=0.33).)`
- `BENCH-04.organism: Status=Unsupported (Extracted value is not supported by the cited passage (token_overlap=0.00).)`
- `BENCH-04.experimental_methodology: Status=Partially supported (Passage located in source (sim=1.00), but claim involves paraphrasing/synthesis (overlap=0.50).)`
- `BENCH-04.genes_or_biomarkers: Status=Unsupported (Extracted value is not supported by the cited passage (token_overlap=0.00).)`
- `BENCH-05.organism: Status=Unsupported (Extracted value is not supported by the cited passage (token_overlap=0.00).)`
- `BENCH-05.experimental_methodology: Status=Partially supported (Passage located in source (sim=1.00), but claim involves paraphrasing/synthesis (overlap=0.60).)`
- `BENCH-05.genes_or_biomarkers: Status=Unsupported (Extracted value is not supported by the cited passage (token_overlap=0.00).)`
- `BENCH-06.organism: Status=Unsupported (Extracted value is not supported by the cited passage (token_overlap=0.00).)`
- `BENCH-06.genes_or_biomarkers: Status=Unsupported (Extracted value is not supported by the cited passage (token_overlap=0.00).)`
- `BENCH-07.organism: Status=Unsupported (Extracted value is not supported by the cited passage (token_overlap=0.00).)`
- `BENCH-07.experimental_methodology: Status=Partially supported (Passage located in source (sim=1.00), but claim involves paraphrasing/synthesis (overlap=0.40).)`
- `BENCH-07.genes_or_biomarkers: Status=Unsupported (Extracted value is not supported by the cited passage (token_overlap=0.00).)`
- `BENCH-08.organism: Status=Unsupported (Extracted value is not supported by the cited passage (token_overlap=0.00).)`
- `BENCH-08.genes_or_biomarkers: Status=Unsupported (Extracted value is not supported by the cited passage (token_overlap=0.00).)`
- `BENCH-09.disease_or_condition: Status=Partially supported (Passage located in source (sim=1.00), but claim involves paraphrasing/synthesis (overlap=0.50).)`
- `BENCH-09.organism: Status=Unsupported (Extracted value is not supported by the cited passage (token_overlap=0.00).)`
- `BENCH-09.experimental_methodology: Status=Unsupported (Extracted value is not supported by the cited passage (token_overlap=0.20).)`
- `BENCH-09.genes_or_biomarkers: Status=Unsupported (Extracted value is not supported by the cited passage (token_overlap=0.00).)`
- `BENCH-10.organism: Status=Unsupported (Extracted value is not supported by the cited passage (token_overlap=0.00).)`
- `BENCH-10.experimental_methodology: Status=Unsupported (Extracted value is not supported by the cited passage (token_overlap=0.33).)`
- `BENCH-10.genes_or_biomarkers: Status=Unsupported (Extracted value is not supported by the cited passage (token_overlap=0.00).)`
- `BENCH-11.disease_or_condition: Status=Partially supported (Passage located in source (sim=1.00), but claim involves paraphrasing/synthesis (overlap=0.00).)`
- `BENCH-11.organism: Status=Unsupported (Extracted value is not supported by the cited passage (token_overlap=0.00).)`
- `BENCH-11.experimental_methodology: Status=Partially supported (Passage located in source (sim=1.00), but claim involves paraphrasing/synthesis (overlap=0.60).)`
- `BENCH-11.genes_or_biomarkers: Status=Unsupported (Extracted value is not supported by the cited passage (token_overlap=0.33).)`
- `BENCH-12.disease_or_condition: Status=Partially supported (Passage located in source (sim=1.00), but claim involves paraphrasing/synthesis (overlap=0.50).)`
- `BENCH-12.organism: Status=Unsupported (Extracted value is not supported by the cited passage (token_overlap=0.00).)`
- `BENCH-12.experimental_methodology: Status=Partially supported (Passage located in source (sim=1.00), but claim involves paraphrasing/synthesis (overlap=0.60).)`
- `BENCH-12.genes_or_biomarkers: Status=Unsupported (Extracted value is not supported by the cited passage (token_overlap=0.00).)`
- `BENCH-13.disease_or_condition: Status=Unsupported (Numeric values ['19'] in extracted claim do not appear in source text.)`
- `BENCH-13.organism: Status=Unsupported (Extracted value is not supported by the cited passage (token_overlap=0.00).)`
- `BENCH-13.experimental_methodology: Status=Unsupported (Extracted value is not supported by the cited passage (token_overlap=0.25).)`
- `BENCH-13.genes_or_biomarkers: Status=Unsupported (Extracted value is not supported by the cited passage (token_overlap=0.00).)`
- `BENCH-14.organism: Status=Unsupported (Extracted value is not supported by the cited passage (token_overlap=0.00).)`
- `BENCH-14.experimental_methodology: Status=Partially supported (Passage located in source (sim=1.00), but claim involves paraphrasing/synthesis (overlap=0.40).)`
- `BENCH-14.genes_or_biomarkers: Status=Unsupported (Extracted value is not supported by the cited passage (token_overlap=0.00).)`
- `BENCH-15.disease_or_condition: Status=Partially supported (Passage located in source (sim=1.00), but claim involves paraphrasing/synthesis (overlap=0.00).)`
- `BENCH-15.organism: Status=Unsupported (Extracted value is not supported by the cited passage (token_overlap=0.00).)`
- `BENCH-15.experimental_methodology: Status=Partially supported (Passage located in source (sim=1.00), but claim involves paraphrasing/synthesis (overlap=0.50).)`
- `BENCH-15.genes_or_biomarkers: Status=Unsupported (Extracted value is not supported by the cited passage (token_overlap=0.00).)`
- `BENCH-16.disease_or_condition: Status=Unsupported (Extracted value is not supported by the cited passage (token_overlap=0.00).)`
- `BENCH-16.organism: Status=Unsupported (Extracted value is not supported by the cited passage (token_overlap=0.00).)`
- `BENCH-16.genes_or_biomarkers: Status=Unsupported (Extracted value is not supported by the cited passage (token_overlap=0.00).)`
- `BENCH-17.organism: Status=Unsupported (Extracted value is not supported by the cited passage (token_overlap=0.00).)`
- `BENCH-17.experimental_methodology: Status=Partially supported (Passage located in source (sim=1.00), but claim involves paraphrasing/synthesis (overlap=0.50).)`
- `BENCH-17.genes_or_biomarkers: Status=Unsupported (Extracted value is not supported by the cited passage (token_overlap=0.00).)`
- `BENCH-18.disease_or_condition: Status=Unsupported (Extracted value is not supported by the cited passage (token_overlap=0.25).)`
- `BENCH-18.organism: Status=Unsupported (Extracted value is not supported by the cited passage (token_overlap=0.00).)`
- `BENCH-18.experimental_methodology: Status=Partially supported (Passage located in source (sim=1.00), but claim involves paraphrasing/synthesis (overlap=0.33).)`
- `BENCH-18.genes_or_biomarkers: Status=Unsupported (Extracted value is not supported by the cited passage (token_overlap=0.33).)`
- `BENCH-19.disease_or_condition: Status=Partially supported (Passage located in source (sim=1.00), but claim involves paraphrasing/synthesis (overlap=0.50).)`
- `BENCH-19.organism: Status=Unsupported (Extracted value is not supported by the cited passage (token_overlap=0.00).)`
- `BENCH-19.genes_or_biomarkers: Status=Unsupported (Extracted value is not supported by the cited passage (token_overlap=0.00).)`
- `BENCH-20.disease_or_condition: Status=Partially supported (Passage located in source (sim=1.00), but claim involves paraphrasing/synthesis (overlap=0.60).)`
- `BENCH-20.organism: Status=Unsupported (Extracted value is not supported by the cited passage (token_overlap=0.00).)`
- `BENCH-20.experimental_methodology: Status=Partially supported (Passage located in source (sim=1.00), but claim involves paraphrasing/synthesis (overlap=0.50).)`
- `BENCH-20.genes_or_biomarkers: Status=Unsupported (Extracted value is not supported by the cited passage (token_overlap=0.00).)`
- `BENCH-21.organism: Status=Unsupported (Extracted value is not supported by the cited passage (token_overlap=0.00).)`
- `BENCH-21.experimental_methodology: Status=Partially supported (Passage located in source (sim=1.00), but claim involves paraphrasing/synthesis (overlap=0.43).)`
- `BENCH-21.genes_or_biomarkers: Status=Unsupported (Extracted value is not supported by the cited passage (token_overlap=0.00).)`
- `BENCH-22.organism: Status=Unsupported (Extracted value is not supported by the cited passage (token_overlap=0.00).)`
- `BENCH-22.experimental_methodology: Status=Partially supported (Passage located in source (sim=1.00), but claim involves paraphrasing/synthesis (overlap=0.50).)`
- `BENCH-22.genes_or_biomarkers: Status=Unsupported (Extracted value is not supported by the cited passage (token_overlap=0.00).)`
- `BENCH-23.organism: Status=Unsupported (Extracted value is not supported by the cited passage (token_overlap=0.00).)`
- `BENCH-23.experimental_methodology: Status=Partially supported (Passage located in source (sim=1.00), but claim involves paraphrasing/synthesis (overlap=0.00).)`
- `BENCH-24.disease_or_condition: Status=Unsupported (Extracted value is not supported by the cited passage (token_overlap=0.00).)`
- `BENCH-24.organism: Status=Unsupported (Extracted value is not supported by the cited passage (token_overlap=0.00).)`
- `BENCH-24.experimental_methodology: Status=Unsupported (Extracted value is not supported by the cited passage (token_overlap=0.12).)`
- `BENCH-24.genes_or_biomarkers: Status=Unsupported (Extracted value is not supported by the cited passage (token_overlap=0.00).)`
- `BENCH-25.organism: Status=Unsupported (Extracted value is not supported by the cited passage (token_overlap=0.00).)`
