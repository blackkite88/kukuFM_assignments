"""Automated legal document generation in .docx format with placeholders and draft banners."""

from pathlib import Path

from docx import Document

from src.flow import CaseFile


def generate_document(case_file: CaseFile, output_path: Path | str) -> str:
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)

    doc = Document()
    doc.add_paragraph(
        "DRAFT ONLY — REVIEW CAREFULLY WITH LEGAL COUNSEL / DLSA (15100) BEFORE SIGNING OR DISPATCHING",
        style="Intense Quote",
    )

    parties = case_file.parties or "[MISSING: Opposing Party Full Name & Address]"
    amount = case_file.amount or "[MISSING: Exact Claim Amount in INR]"
    dates = case_file.dates or "[MISSING: Relevant Transaction / Eviction Dates]"
    evidence_str = (
        ", ".join(case_file.evidence)
        if case_file.evidence
        else "[MISSING: Payment receipts, lease contract, or correspondence proof]"
    )

    if case_file.issue_type == "deposit":
        doc.add_heading("FORMAL LEGAL NOTICE FOR REFUND OF TENANCY SECURITY DEPOSIT", level=1)
        doc.add_paragraph(f"To,\n{parties}\nAddress: [MISSING: Landlord Registered Address]")
        doc.add_paragraph("From,\n[MISSING: Tenant Full Legal Name]\nAddress: [MISSING: Tenant Present Address]")
        doc.add_paragraph(
            f"Date: [MISSING: Today's Date]\n"
            f"Subject: Demand Notice under Model Tenancy Act, 2021 (Section 11) for refund of unreturned security deposit of {amount}."
        )
        doc.add_paragraph(
            "Sir/Madam,\nUnder instructions and authority from my client (the Tenant), this legal notice is hereby served upon you:"
        )
        doc.add_paragraph(
            f"1. That the Tenant was in lawful occupation of the rented residential premises under agreement dated {dates}."
        )
        doc.add_paragraph(
            f"2. That at the inception of tenancy, the Tenant deposited a sum of {amount} as refundable security deposit."
        )
        doc.add_paragraph(
            "3. That peaceful and vacant possession of the premises was handed over on [MISSING: Handover Date], with all electricity and water utility dues fully cleared."
        )
        doc.add_paragraph(
            "4. That under Section 11 of the Model Tenancy Act, 2021 and general contract principles, the security deposit must be refunded upon handing over vacant possession."
        )
        doc.add_paragraph(
            "5. That despite repeated reminders, you have wrongfully withheld the deposit without furnishing any itemized deduction bill or lawful justification."
        )
        doc.add_paragraph(f"6. Supporting evidence on record: {evidence_str}.")
        doc.add_paragraph(
            f"DEMAND: You are hereby called upon to refund the full security deposit sum of {amount} "
            "with 12% interest within 15 days of receipt of this notice, failing which appropriate legal proceedings "
            "before the Rent Court / Civil Authority shall be instituted at your risk and cost."
        )

    elif case_file.issue_type == "consumer":
        doc.add_heading("BEFORE THE DISTRICT CONSUMER DISPUTES REDRESSAL COMMISSION", level=1)
        doc.add_heading("CONSUMER COMPLAINT UNDER SECTION 35 OF CONSUMER PROTECTION ACT, 2019", level=2)
        doc.add_paragraph(
            f"IN THE MATTER OF:\n[MISSING: Complainant Name & Address] ... COMPLAINANT\nVERSUS\n{parties} ... OPPOSITE PARTY"
        )
        doc.add_paragraph(f"1. That the Complainant purchased goods/services for consideration of {amount} on {dates}.")
        doc.add_paragraph(
            "2. That the purchased product/service suffered from gross defect/deficiency under Section 2(10) "
            "and Section 2(11) of the Consumer Protection Act, 2019."
        )
        doc.add_paragraph(
            "3. That the Opposite Party failed to rectify the defect or grant refund despite formal complaints."
        )
        doc.add_paragraph(f"4. Supporting Documents Annexed: {evidence_str}.")
        doc.add_paragraph(
            f"PRAYER: The Complainant respectfully prays for an order under Section 39 directing the Opposite Party "
            f"to refund {amount} along with compensation for harassment and litigation costs."
        )

    else:
        doc.add_heading("FORMAL DEMAND NOTICE FOR UNPAID WAGES AND STATUTORY DUES", level=1)
        doc.add_paragraph(f"To,\n{parties}\nAddress: [MISSING: Employer / Company Registered Address]")
        doc.add_paragraph("From,\n[MISSING: Employee Full Name & Staff ID]\nAddress: [MISSING: Employee Address]")
        doc.add_paragraph(
            f"Subject: Notice for non-payment of earned wages amounting to {amount} under "
            "Payment of Wages Act, 1936 / Code on Wages, 2019."
        )
        doc.add_paragraph(f"1. That the undersigned was employed as [MISSING: Designation] during the period {dates}.")
        doc.add_paragraph(
            f"2. That wages for the period [MISSING: Unpaid Months] totaling {amount} have been unlawfully "
            "withheld in violation of Section 5 of the Payment of Wages Act, 1936."
        )
        doc.add_paragraph("3. That no statutory deduction under Section 7 applies to justify this non-payment.")
        doc.add_paragraph(f"4. Evidentiary records available: {evidence_str}.")
        doc.add_paragraph(
            f"DEMAND: You are called upon to remit the outstanding amount of {amount} within 7 working days, "
            "failing which an application under Section 15 of the Payment of Wages Act before the Labour Commissioner shall be filed."
        )

    doc.add_paragraph("\n\nSincerely,\n_________________________\n[SIGNATURE OF SENDER]\n[DATE & PLACE]")
    doc.save(str(out))
    return str(out)
