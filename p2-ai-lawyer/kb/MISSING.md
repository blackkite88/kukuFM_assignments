# Knowledge Base Coverage and Missing Sections

The Knowledge Base is populated exclusively with verified statutory provisions fetched from official Government of India sources (Department of Consumer Affairs, Ministry of Labour & Employment, Ministry of Housing & Urban Affairs, and India Code).

## Populated Acts & Sections
1. **Consumer Protection Act, 2019** (`kb/consumer_protection_act_2019.json`):
   - Section 2(7) (Definition of Consumer)
   - Section 2(10) (Definition of Defect)
   - Section 2(11) (Definition of Deficiency)
   - Section 34 (Jurisdiction of District Commission)
   - Section 35 (Manner of filing complaint; e-Daakhil)
   - Section 39 (Reliefs granted by District Commission: refund, replacement, compensation)
   - Section 69 (Limitation period: 2 years)
   - *Source:* `https://consumeraffairs.gov.in/acts-in-force/consumer-protection-act-2019`, `https://edaakhil.nic.in`

2. **Payment of Wages Act, 1936 & Code on Wages, 2019** (`kb/payment_of_wages_act_1936.json`):
   - Payment of Wages Act, 1936: Section 3, Section 4, Section 5, Section 7, Section 15
   - Code on Wages, 2019: Section 17, Section 45
   - *Source:* `https://labour.gov.in/wages-payment-of-wages`

3. **Model Tenancy Act, 2021** (`kb/model_tenancy_act_2021.json`):
   - Section 11 (Security deposit limits and refund obligations)
   - Section 13 (Notice before entry)
   - Section 22 (Eviction and recovery of possession)
   - Section 30 (Bar of civil court jurisdiction)
   - *Source:* `https://mohua.gov.in/upload/uploadfiles/files/Model-Tenancy-Act-English-02_06_2021.pdf`

4. **Limitation Act, 1963** (`kb/limitation_act_1963.json`):
   - Section 3 (Bar of limitation)
   - Article 7 (Recovery of wages: 3 years)
   - Article 22 (Money deposited payable on demand: 3 years)
   - Article 113 (Residuary suits: 3 years)
   - *Source:* `https://www.indiacode.nic.in/handle/123456789/1567`

## Missing / Excluded Sections (For User Extension)
Because tenancy law in India is a State Subject, individual state-specific rent statutes must be populated for localized eviction disputes:
- **Delhi Rent Control Act, 1958**: Excluded (applies only to pre-existing tenancies under rent ceilings in NCT of Delhi).
- **Maharashtra Rent Control Act, 1999**: Excluded (requires local state gazette ingestion).
- **Payment of Gratuity Act, 1972**: Out of scope for everyday wage recovery under 1-2 turn intake.
- **Industrial Disputes Act, 1947 (Section 33C)**: Labor court execution applications for collective industrial disputes.

*Rule Enforced:* No section text has been generated from LLM memory. Any citation outside the populated KB chunks above is strictly rejected by `validator.py`.
