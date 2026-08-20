"""
MediRAG AI – Core RAG Pipeline

Pipeline:
  Query → Medical Check → Embed → Similarity Search → Context Assembly → Llama 3 → Response + Citations
"""

import time
from typing import Dict, List, Optional, Any

from langchain_community.llms import Ollama
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser

from app.config import settings
from app.models.schemas import MedicalQueryResponse, SourceCitation
from app.utils.logger import logger
from app.vectorstore.vector_store_manager import get_vector_store_manager


# ---------------------------------------------------------------------------
# Medical topic keywords – used to gate queries before hitting the LLM
# ---------------------------------------------------------------------------

MEDICAL_KEYWORDS = {
    # Diseases & conditions
    "disease", "disorder", "syndrome", "condition", "infection", "cancer", "tumor",
    "diabetes", "hypertension", "asthma", "arthritis", "alzheimer", "parkinson",
    "stroke", "heart", "cardiac", "renal", "hepatic", "pulmonary", "neurological",
    "psychiatric", "depression", "anxiety", "schizophrenia", "bipolar", "epilepsy",
    "anemia", "leukemia", "lymphoma", "sepsis", "pneumonia", "tuberculosis", "hiv",
    "aids", "malaria", "covid", "influenza", "dengue", "typhoid", "cholera",
    # Symptoms
    "symptom", "symptoms", "pain", "fever", "cough", "fatigue", "nausea",
    "vomiting", "diarrhea", "bleeding", "swelling", "rash", "headache",
    "dizziness", "breathlessness", "chest pain", "palpitation", "seizure",
    "paralysis", "weakness", "numbness", "itching", "jaundice", "edema",
    # Treatments & medications
    "treatment", "therapy", "medication", "medicine", "drug", "drugs", "dose",
    "dosage", "prescription", "antibiotic", "antiviral", "antifungal", "vaccine",
    "vaccination", "surgery", "procedure", "operation", "chemotherapy",
    "radiotherapy", "dialysis", "transplant", "rehabilitation", "physiotherapy",
    # Diagnostics
    "diagnosis", "diagnose", "test", "scan", "mri", "ct scan", "x-ray", "ultrasound",
    "biopsy", "blood test", "urine test", "ecg", "eeg", "endoscopy", "colonoscopy",
    "screening", "pathology", "lab", "laboratory", "specimen", "culture",
    # Anatomy & physiology
    "anatomy", "physiology", "organ", "tissue", "cell", "gene", "dna", "rna",
    "protein", "enzyme", "hormone", "receptor", "nerve", "muscle", "bone",
    "brain", "lung", "liver", "kidney", "stomach", "intestine", "colon",
    "pancreas", "thyroid", "adrenal", "pituitary", "spleen", "lymph",
    # Medical specialties
    "cardiology", "neurology", "oncology", "pediatrics", "gynecology", "obstetrics",
    "psychiatry", "dermatology", "ophthalmology", "orthopedic", "urology",
    "gastroenterology", "endocrinology", "immunology", "rheumatology", "hematology",
    "radiology", "pathology", "anesthesia", "emergency", "icu", "critical care",
    # Pharmacology
    "pharmacology", "pharmacokinetics", "pharmacodynamics", "interaction",
    "side effect", "adverse", "contraindication", "overdose", "toxicity",
    "ibuprofen", "paracetamol", "aspirin", "metformin", "insulin", "warfarin",
    "statin", "beta blocker", "ace inhibitor", "diuretic", "anticoagulant",
    # Clinical terms
    "clinical", "patient", "hospital", "ward", "icu", "emergency", "outpatient",
    "inpatient", "prognosis", "etiology", "pathogenesis", "complication",
    "mortality", "morbidity", "incidence", "prevalence", "epidemiology",
    "prophylaxis", "palliative", "chronic", "acute", "benign", "malignant",
    # Nutrition / health
    "nutrition", "diet", "vitamin", "mineral", "supplement", "calorie", "obesity",
    "bmi", "weight", "cholesterol", "blood pressure", "blood sugar", "glucose",
    "healthcare", "health", "medical", "medicine", "clinic", "physician", "doctor",
    "nurse", "surgeon", "specialist", "therapist",
}

NON_MEDICAL_REPLY = (
    "I'm MediRAG AI, a specialized Healthcare Knowledge Assistant. "
    "I can only answer medical and health-related questions such as diseases, symptoms, treatments, medications, anatomy, and clinical topics.\n\n"
    "Your question appears to be outside my area of expertise. "
    "Please ask me something related to healthcare or medicine and I'll be happy to help! 🏥"
)


def is_medical_query(query: str) -> bool:
    """
    Returns True if the query contains medical/health-related terms.
    Uses keyword matching for speed — no LLM call needed.
    """
    q = query.lower()
    # Check each keyword
    for kw in MEDICAL_KEYWORDS:
        if kw in q:
            return True
    return False


MEDICAL_QA_PROMPT = PromptTemplate(
    input_variables=["context", "question"],
    template="""You are MediRAG AI, a helpful and knowledgeable Healthcare Knowledge Assistant.

CONTEXT FROM KNOWLEDGE BASE:
{context}

QUESTION: {question}

INSTRUCTIONS:
- If the context contains relevant information, use it to give a thorough, helpful answer.
- If the context is not relevant or insufficient, use your general knowledge to answer helpfully.
- Never refuse to answer. Always provide the most useful response you can.
- Be clear, concise, and friendly.
- Do not add unnecessary disclaimers or repeat instructions in your answer.

ANSWER:""",
)

DRUG_INTERACTION_PROMPT = PromptTemplate(
    input_variables=["context", "drug_a", "drug_b"],
    template="""You are a clinical pharmacology AI assistant. Analyze drug interactions based strictly on the provided medical literature.

PHARMACOLOGICAL LITERATURE CONTEXT:
{context}

QUERY: Analyze the drug interaction between {drug_a} and {drug_b}.

PROVIDE:
1. **Interaction Summary**: Describe the interaction mechanism
2. **Risk Severity**: Categorize as Contraindicated / Major / Moderate / Minor
3. **Clinical Effects**: What may happen clinically
4. **Management**: How to manage or avoid this interaction
5. **Monitoring Recommendations**: Parameters to monitor

DISCLAIMER: Educational and informational use only. Not a substitute for professional clinical judgment.

RESPONSE:""",
)

SYMPTOM_QUERY_PROMPT = PromptTemplate(
    input_variables=["context", "symptoms"],
    template="""You are a clinical decision support AI assistant. Based on the medical literature context provided, analyze the following symptoms.

MEDICAL LITERATURE CONTEXT:
{context}

PRESENTING SYMPTOMS:
{symptoms}

PROVIDE:
1. Relevant differential diagnoses mentioned in the literature
2. Key distinguishing features from the sources
3. Recommended diagnostic workup from guidelines
4. When to seek urgent care (from evidence-based sources)

NOTE: This is NOT a diagnostic tool. Always refer to a qualified healthcare provider.

DISCLAIMER: Educational and informational use only. Not a substitute for professional clinical judgment.

RESPONSE:""",
)

TREATMENT_PROTOCOL_PROMPT = PromptTemplate(
    input_variables=["context", "condition"],
    template="""You are a clinical guidelines AI assistant. Retrieve and summarize treatment protocols from the provided medical literature.

CLINICAL GUIDELINES CONTEXT:
{context}

CONDITION: {condition}

PROVIDE:
1. **First-Line Treatment**: Recommended initial management
2. **Treatment Steps**: Step-by-step protocol
3. **Contraindications**: What to avoid
4. **Monitoring Parameters**: Key clinical parameters to track
5. **Evidence Level**: Grade of evidence if mentioned
6. **Guideline Source**: Which organization's guidelines

DISCLAIMER: Educational and informational use only. Not a substitute for professional clinical judgment.

RESPONSE:""",
)


class RAGPipeline:
    """
    Core Retrieval-Augmented Generation pipeline for MediRAG AI.
    """

    def __init__(self):
        self._llm: Optional[Ollama] = None
        self._vsm = get_vector_store_manager()

    def _get_llm(self) -> Ollama:
        """Lazy-load Ollama LLM."""
        if self._llm is None:
            self._llm = Ollama(
                base_url=settings.ollama_base_url,
                model=settings.llm_model,
                temperature=settings.llm_temperature,
                num_predict=settings.llm_max_tokens,
            )
            logger.info(f"Ollama LLM loaded: model={settings.llm_model}")
        return self._llm

    def _retrieve_context(
        self,
        query: str,
        k: int = None,
        filters: Optional[Dict] = None,
    ) -> tuple[str, List[SourceCitation]]:
        """
        Perform vector similarity search and assemble context string.
        Returns (context_text, list_of_source_citations).
        """
        k = k or settings.top_k_results
        results = self._vsm.search(query=query, k=k, filters=filters)

        if not results:
            return "No relevant medical literature found in the knowledge base.", []

        context_parts = []
        citations: List[SourceCitation] = []
        seen_docs = set()

        for doc, score in results:
            meta = doc.metadata
            source_text = f"""
[SOURCE: {meta.get('title', meta.get('filename', 'Unknown'))}]
Category: {meta.get('category', 'Unknown')}
Specialty: {meta.get('medical_specialty', 'Unknown')}
Section: {meta.get('section', 'N/A')}

{doc.page_content}
---"""
            context_parts.append(source_text)

            doc_id = meta.get("document_id", "unknown")
            if doc_id not in seen_docs:
                seen_docs.add(doc_id)
                citations.append(
                    SourceCitation(
                        document_id=doc_id,
                        filename=meta.get("filename", "Unknown"),
                        title=meta.get("title"),
                        category=meta.get("category"),
                        medical_specialty=meta.get("medical_specialty"),
                        page_number=meta.get("page_number"),
                        excerpt=doc.page_content[:300] + "..." if len(doc.page_content) > 300 else doc.page_content,
                        relevance_score=round(float(score), 4),
                    )
                )

        context = "\n".join(context_parts)
        return context, citations

    def _compute_confidence(self, citations: List[SourceCitation]) -> float:
        """Compute overall confidence from top citation scores."""
        if not citations:
            return 0.0
        scores = [c.relevance_score for c in citations[:3]]
        return round(sum(scores) / len(scores), 4)

    # ------------------------------------------------------------------
    # Public Pipeline Methods
    # ------------------------------------------------------------------

    def medical_query(
        self,
        query: str,
        k: int = None,
        filters: Optional[Dict] = None,
        agent_name: str = "Medical QA Agent",
    ) -> MedicalQueryResponse:
        """Answer a general medical question using RAG. Rejects non-medical queries instantly."""
        start = time.time()

        # Gate: reject non-medical queries without hitting the LLM
        if not is_medical_query(query):
            return MedicalQueryResponse(
                query=query,
                answer=NON_MEDICAL_REPLY,
                confidence_score=0.0,
                sources=[],
                agent_used="Medical Topic Filter",
                response_time_ms=int((time.time() - start) * 1000),
            )

        context, citations = self._retrieve_context(query, k, filters)
        answer = (MEDICAL_QA_PROMPT | self._get_llm() | StrOutputParser()).invoke(
            {"context": context, "question": query}
        )

        return MedicalQueryResponse(
            query=query,
            answer=answer.strip(),
            confidence_score=self._compute_confidence(citations),
            sources=citations,
            agent_used=agent_name,
            response_time_ms=int((time.time() - start) * 1000),
        )

    def drug_interaction_query(
        self,
        drug_a: str,
        drug_b: str,
        k: int = None,
    ) -> Dict[str, Any]:
        """Analyze drug interaction between two drugs."""
        start = time.time()
        combined_query = f"drug interaction {drug_a} {drug_b} contraindication adverse effect"
        context, citations = self._retrieve_context(combined_query, k)

        answer = (DRUG_INTERACTION_PROMPT | self._get_llm() | StrOutputParser()).invoke({"context": context, "drug_a": drug_a, "drug_b": drug_b})

        return {
            "answer": answer.strip(),
            "citations": citations,
            "confidence": self._compute_confidence(citations),
            "response_time_ms": int((time.time() - start) * 1000),
        }

    def symptom_query(
        self,
        symptoms: List[str],
        k: int = None,
    ) -> Dict[str, Any]:
        """Retrieve knowledge based on presenting symptoms."""
        start = time.time()
        symptoms_text = ", ".join(symptoms)
        query = f"diagnosis differential symptoms {symptoms_text} clinical presentation"
        context, citations = self._retrieve_context(query, k)

        answer = (SYMPTOM_QUERY_PROMPT | self._get_llm() | StrOutputParser()).invoke({"context": context, "symptoms": symptoms_text})

        return {
            "answer": answer.strip(),
            "citations": citations,
            "confidence": self._compute_confidence(citations),
            "response_time_ms": int((time.time() - start) * 1000),
        }

    def treatment_protocol_query(
        self,
        condition: str,
        k: int = None,
    ) -> Dict[str, Any]:
        """Retrieve treatment protocols for a medical condition."""
        start = time.time()
        query = f"treatment protocol guideline {condition} management therapy"
        context, citations = self._retrieve_context(query, k)

        answer = (TREATMENT_PROTOCOL_PROMPT | self._get_llm() | StrOutputParser()).invoke({"context": context, "condition": condition})

        return {
            "answer": answer.strip(),
            "citations": citations,
            "confidence": self._compute_confidence(citations),
            "response_time_ms": int((time.time() - start) * 1000),
        }


# Module-level singleton
_pipeline_instance: Optional[RAGPipeline] = None


def get_rag_pipeline() -> RAGPipeline:
    global _pipeline_instance
    if _pipeline_instance is None:
        _pipeline_instance = RAGPipeline()
    return _pipeline_instance
