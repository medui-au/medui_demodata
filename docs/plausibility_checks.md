# Plausibility checks

The maintainers' `tools/checks.sql` runs these against the full demo databases (`tools/sq.sh tools/checks.sql`). A check that finds nothing prints nothing, or prints 0.

| # | Check | Rule | Result (2026-11-08 build) |
|---|---|---|---|
| A1 | Nothing before birth | No visit, observation, vaccine, medicine, result, letter, history year or appointment before the DOB | 0 |
| A2 | Nothing after death | Deceased patients have no later events or bookings | 0 |
| A3 | Nothing in the future | Except bookings and due dates | 0 |
| A4 | Ages plausible | Age ≤ 105 and a DOB for every patient | 1: patient 30, who died in 2016 aged 101 (plausible) |
| A5 | Childhood vaccines at childhood ages | Infant and childhood schedule vaccines given before 15 | 0 |
| A6 | Inbox is recent | Inbox reports collected in the last 90 days | 0 older |
| B1 | Sex-specific tests | PSA only for males; cervical, mammogram and pregnancy tests only for females | 0 |
| B2 | Sex-specific history | Prostate conditions only for males; gynaecological history only for females | 0 |
| B3 | Height, weight and BMI fit age | Children's values below adult limits; adults 140–205 cm and 38–170 kg; BMI 12–50 | 0 |
| B4 | Vital signs plausible | Systolic 85–200, pulse 45–150, temperature 35–40 | 0 |
| B5 | Medicines fit age | No adult-only medicines under 12 (statins, anticoagulants, sedatives, adult inhaler and antihistamine strengths) | 0 |
| B6 | Social history fits age | No smoking or alcohol under 14 | 0 |
| C1 | Medicines ↔ history | Each current medicine has its condition; patients with asthma, diabetes, high blood pressure, AF or hypothyroidism have at least one current medicine | 0 |
| C2 | Pathology ↔ history | Diabetics' latest HbA1c 6.0–8.0 and no diabetic-range HbA1c without diabetes; eGFR < 60 only with CKD or heart failure; treated hypothyroid TSH in range; latest LDL ≤ 3.0 on a statin; no pathology before 18 | 0 |
| C3 | Ceased medicines | Every current patient has at least one, with a date and reason | 0 without |
| C4 | Allergies | A share of patients with a reaction | 19 patients |
| C5 | Recent visits | Every active patient has a visit in the last 24 months | 0 without |
| C6 | Visit notes | Every visit has a progress note | 0 without |
| C7 | Correspondence | Every current patient has specialist letters | 0 without |
| C8 | Diagnoses count in the Disease Profile | Coded history items are active (STATUSCODE 1); MedUI's Disease Profile ignores inactive ones | 0 inactive (fixed 2026-11-08: all were 0) |

## What the data shows off in MedUI

| Feature | Demo data behind it |
|---|---|
| Trend charts | eGFR (patient 32), HbA1c (patient 15), cholesterol (patient 8), TSH (patient 18), iron (patient 37) |
| FIB-4 | Liver tests and platelets (patient 9) |
| Results Outside Range | 60 unchecked inbox reports with filed history to compare |
| Criterion review | Active patients with recent visits and HbA1c or eGFR results |
| Disease Profile badges | Coded, active diagnoses: IHD 8, hypertension 12, high cholesterol 9, AF 8, diabetes 6, CKD 1 (current patients) |
| Care-plan eligibility | 965 due, 967 due, Neither, None prior, 721 only (4 patients each) |
| Health assessment 75+ | Due, done and declined |
| NIP vaccine eligibility | Vaccines carry MedUI's vaccine IDs; full childhood schedule; flu, shingles, COVID and pneumococcal for the 65+ patients |
| Other patient-record panels | Allergy panel, social and family history, ceased medicines, next booking, recalls and actions |
| Letters and documents | Specialist letters (PDF) in the document viewer; referrals out, with letter text |
| Day sheet | About 20 bookings each weekday and 4 or 5 on Saturday mornings, for today and the next three weeks, none on Sundays; completed appointments and invoices on past visit days |

## Other checks

- **MedUI's queries:** all 113 query files were run as the read-only login. 112 run; `condition_term_names` needs BPSDrugs, which isn't part of the demo, so it is skipped.
- **Identifier scan:** a private list of 355 names and 105 number strings that must not appear was checked against every text and binary column, including inside PDFs and zipped reports. **0 hits.** Twelve everyday words were taken off the list after review, because they are ordinary vocabulary rather than identifiers: family, main, heavy, pathology, psychology, radiology, surgery, muscle, public, nursing, home, school.
- **Restore:** the backups were restored on a throwaway server with `restore/restore.sh`, and the queries ran there as the reader.
