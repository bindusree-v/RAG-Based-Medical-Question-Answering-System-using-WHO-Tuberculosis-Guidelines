"""
MediRAG AI – Validation Engine Tests
"""

import pytest
from app.validation.medical_validator import MedicalDocumentValidator, ValidationEngine


class TestMedicalDocumentValidator:
    """Unit tests for the keyword-based validation logic."""

    def setup_method(self):
        self.validator = MedicalDocumentValidator()

    def test_accepts_clinical_guideline(self):
        text = """
        This clinical guideline provides evidence-based recommendations for the
        diagnosis and treatment of hypertension. Patients with blood pressure
        exceeding 140/90 mmHg should receive antihypertensive therapy.
        Randomized controlled trials have demonstrated the efficacy of ACE inhibitors
        as first-line treatment. Dosage should be titrated based on clinical response.
        Adverse effects include cough and hyperkalemia. Regular monitoring of renal
        function is recommended. Cardiovascular risk stratification is essential.
        """
        result = self.validator.validate(text, "hypertension_guidelines.pdf")
        assert result.is_valid is True
        assert result.status == "accepted"

    def test_accepts_drug_database_text(self):
        text = """
        Metformin hydrochloride 500mg tablets. Pharmacokinetics: bioavailability 50-60%.
        Half-life 6.2 hours. Contraindications: renal impairment (eGFR < 30).
        Drug interactions: contrast media, alcohol. Adverse effects: gastrointestinal
        upset, lactic acidosis (rare). Dosage: 500mg twice daily with meals.
        Pharmacology: biguanide antidiabetic. Mechanism: reduces hepatic glucose
        production. Clinical trial data supports glycemic control in type 2 diabetes.
        """
        result = self.validator.validate(text, "metformin_drug_info.pdf")
        assert result.is_valid is True
        assert result.status == "accepted"

    def test_rejects_resume(self):
        text = """
        John Smith
        Curriculum Vitae
        Professional Summary: Experienced marketing professional with 10 years in
        the industry. Work Experience: Senior Marketing Manager at ABC Corp.
        Skills: Leadership, Communication, Project Management.
        References available upon request. LinkedIn: linkedin.com/in/johnsmith
        """
        result = self.validator.validate(text, "john_smith_cv.pdf")
        assert result.is_valid is False
        assert result.status == "rejected"

    def test_rejects_bank_statement(self):
        text = """
        Bank Statement - Account Number: 1234567890
        Transaction History: January 2024
        Opening Balance: $5,000.00
        Credit: Salary $3,000.00
        Debit: Invoice payment $500.00
        Accounts payable balance sheet quarterly earnings routing number
        """
        result = self.validator.validate(text, "bank_statement.pdf")
        assert result.is_valid is False
        assert result.status == "rejected"

    def test_rejects_empty_text(self):
        result = self.validator.validate("   ", "empty.pdf")
        assert result.is_valid is False
        assert result.rejection_reason == "insufficient_content"

    def test_accepts_research_paper(self):
        text = """
        Abstract: This systematic review and meta-analysis evaluated the efficacy of
        statins in the primary prevention of cardiovascular disease. Methods: We
        searched PubMed, MEDLINE, and Cochrane Library. Randomized controlled trials
        with a minimum follow-up of 12 months were included. Results: 27 RCTs
        involving 175,000 patients were analyzed. Statins significantly reduced
        all-cause mortality (RR 0.91). Discussion: The evidence supports statin
        therapy for high-risk patients. DOI: 10.1016/example.2023.
        """
        result = self.validator.validate(text, "statin_meta_analysis.pdf")
        assert result.is_valid is True

    def test_confidence_score_range(self):
        text = "Patient presents with chest pain, dyspnea, and tachycardia. ECG shows ST elevation."
        result = self.validator.validate(text, "case_report.pdf")
        assert 0.0 <= result.confidence_score <= 1.0


class TestValidationEngine:
    """Integration tests for the full validation engine."""

    def setup_method(self):
        self.engine = ValidationEngine()

    def test_rejects_unsupported_file_type(self):
        ok, msg = self.engine.validate_file_type("resume.exe", "application/octet-stream")
        assert ok is False
        assert ".exe" in msg

    def test_accepts_pdf_extension(self):
        ok, msg = self.engine.validate_file_type("guidelines.pdf", "application/pdf")
        assert ok is True

    def test_accepts_docx_extension(self):
        ok, msg = self.engine.validate_file_type("protocol.docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document")
        assert ok is True

    def test_full_validation_rejected(self):
        text = "This is a marketing brochure for our new product. Buy now! Limited time offer! Advertisement."
        result = self.engine.validate_document(text, "marketing.pdf", "application/pdf")
        assert result.status == "rejected"
