# Data Assumptions

## Overview
This document outlines the data assumptions made for the TraceLoop traceability system.

## Material Types
- **PET**: Polyethylene Terephthalate (bottles, containers)
- **HDPE**: High-Density Polyethylene (milk jugs, detergent bottles)
- **PP**: Polypropylene (food containers, caps)
- **LDPE**: Low-Density Polyethylene (bags, films)
- **Mixed**: Combination of various plastic types

## Processing Stages
The 13-step lifecycle tracked in this system:

1. **Collection (COL)**: Raw waste collection from sources
2. **Segregation (SEG)**: Sorting by material type and grade
3. **Baling (BAL)**: Compression into bales for transport
4. **Weighing (WGH)**: Weight measurement and recording
5. **Transport (WTR)**: Transportation to processing facility
6. **Washing (WSH)**: Cleaning and decontamination
7. **QC Test (QCT)**: Quality control inspection
8. **Recycling (REC)**: Material processing and conversion
9. **Granulation (GRN)**: Shredding into flakes/pellets
10. **Dispatch (DSP)**: Shipping to end customer
11. **Receive (RCV)**: Customer receipt confirmation
12. **Production (PRD)**: Final product manufacturing
13. **End Use**: Consumer product tracking

## Loss Rate Assumptions

| Stage | Normal Loss | High Loss | Critical Loss |
|-------|-------------|-----------|---------------|
| Segregation | 5-10% | 10-15% | >15% |
| Washing | 5-12% | 12-18% | >18% |
| Recycling | 10-18% | 18-25% | >25% |
| Granulation | 2-5% | 5-8% | >8% |

## Batch Status Values
- `created`: Initial batch creation
- `collection`: Material collected
- `sorting`: In segregation process
- `processing`: Active processing
- `qc_pending`: Awaiting quality check
- `dispatched`: Shipped to customer
- `completed`: Full lifecycle complete
- `cancelled`: Batch cancelled

## Transaction Status Values
- `APPROVED`: Transaction verified and accepted
- `REJECTED`: Transaction failed QC or other check
- `CANCELLED`: Transaction voided
- `PENDING`: Awaiting verification

## Confidence Scoring
Data completeness score (0-100%) based on:
- Number of stages recorded (70% weight)
- Transaction approval rate (30% weight)

## Data Sources
All data is synthetically generated for demonstration purposes:
- 25+ mock batches with realistic weights
- 5 vendor profiles with reliability scores
- 5 processing locations
- 100+ transaction records

## Date Range
Mock data spans January 2024 to March 2024 for realistic time-series analysis.
