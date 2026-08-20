"""
MediRAG AI – Query Service
Bridges API endpoints with RAG pipeline and agent orchestrator.
Uses run_in_executor to avoid blocking the async event loop during LLM inference.
"""

import asyncio
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, List, Optional, Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.agent_orchestrator import get_agent_orchestrator
from app.models.database import QueryLog
from app.models.schemas import (
    MedicalQueryRequest, MedicalQueryResponse,
    DrugInteractionRequest, DrugInteractionResponse, InteractionDetail,
    SymptomQueryRequest, TreatmentProtocolRequest, TreatmentProtocolResponse,
)
from app.rag.rag_pipeline import get_rag_pipeline
from app.utils.logger import logger
import json

# Thread pool for blocking LLM calls
_executor = ThreadPoolExecutor(max_workers=2)


class QueryService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self._orchestrator = get_agent_orchestrator()
        self._rag = get_rag_pipeline()

    def _run_orchestrator(self, query, query_type, top_k):
        """Run orchestrator in thread (blocking LLM call)."""
        return self._orchestrator.run(query=query, query_type=query_type, top_k=top_k)

    def _run_rag_direct(self, query, k):
        """Run RAG pipeline directly in thread."""
        return self._rag.medical_query(query=query, k=k)

    async def medical_query(
        self,
        request: MedicalQueryRequest,
        user_id: Optional[str] = None,
    ) -> MedicalQueryResponse:
        start = time.time()
        loop = asyncio.get_event_loop()

        try:
            state = await loop.run_in_executor(
                _executor,
                lambda: self._run_orchestrator(
                    request.query, request.query_type, request.top_k or 5
                )
            )
        except Exception as exc:
            logger.error(f"Orchestrator error: {exc}")
            return MedicalQueryResponse(
                query=request.query,
                answer=f"Unable to process query: {exc}",
                confidence_score=0.0, sources=[],
                agent_used="Error Handler",
                response_time_ms=int((time.time() - start) * 1000),
            )

        if state.get("error"):
            return MedicalQueryResponse(
                query=request.query,
                answer=f"Agent error: {state['error']}",
                confidence_score=0.0, sources=[],
                agent_used="Error Handler",
                response_time_ms=int((time.time() - start) * 1000),
            )

        result = state.get("result", {})
        if "answer" in result:
            response = MedicalQueryResponse(
                query=request.query,
                answer=result.get("answer", ""),
                confidence_score=result.get("confidence_score", 0.0),
                sources=result.get("sources", []),
                agent_used=state.get("agent_used", "Medical QA Agent"),
                response_time_ms=result.get("response_time_ms", int((time.time() - start) * 1000)),
            )
        else:
            response = await loop.run_in_executor(
                _executor,
                lambda: self._run_rag_direct(request.query, request.top_k or 5)
            )

        # Log query
        await self._log_query(
            user_id=user_id,
            query_type="medical_query",
            query_text=request.query,
            response_summary=response.answer[:500],
            confidence=response.confidence_score,
            response_time_ms=response.response_time_ms,
        )

        return response

    async def drug_interaction_query(
        self,
        request: DrugInteractionRequest,
        user_id: Optional[str] = None,
    ) -> DrugInteractionResponse:
        """Process drug interaction query."""
        start = time.time()

        loop = asyncio.get_event_loop()
        state = await loop.run_in_executor(
            _executor,
            lambda: self._orchestrator.run(
                query=f"drug interaction {request.drug_a} and {request.drug_b}",
                query_type="drug_interaction",
                drug_a=request.drug_a,
                drug_b=request.drug_b,
                top_k=5,
            )
        )

        result = state.get("result", {})
        elapsed = int((time.time() - start) * 1000)

        if "drugs_queried" in result:
            response = DrugInteractionResponse(**result)
        else:
            # Build a minimal response from raw answer
            raw = self._rag.drug_interaction_query(
                drug_a=request.drug_a, drug_b=request.drug_b
            )
            all_drugs = [request.drug_a, request.drug_b] + (request.additional_drugs or [])
            response = DrugInteractionResponse(
                drugs_queried=all_drugs,
                interactions_found=[
                    InteractionDetail(
                        drugs_involved=[request.drug_a, request.drug_b],
                        interaction_type="Clinical Interaction",
                        severity="See analysis",
                        clinical_effects=raw["answer"],
                        management="Consult a clinical pharmacist.",
                    )
                ],
                overall_risk_level="Evaluate per clinical context",
                clinical_summary=raw["answer"],
                monitoring_recommendations="See clinical guidelines.",
                sources=raw["citations"],
                confidence_score=raw["confidence"],
            )

        await self._log_query(
            user_id=user_id,
            query_type="drug_interaction",
            query_text=f"{request.drug_a} + {request.drug_b}",
            response_summary=response.clinical_summary[:500],
            confidence=response.confidence_score,
            response_time_ms=elapsed,
        )

        return response

    async def symptom_query(
        self,
        request: SymptomQueryRequest,
        user_id: Optional[str] = None,
    ) -> MedicalQueryResponse:
        """Symptom-based knowledge retrieval."""
        start = time.time()
        loop = asyncio.get_event_loop()
        state = await loop.run_in_executor(
            _executor,
            lambda: self._orchestrator.run(
                query=" ".join(request.symptoms),
                query_type="symptom",
                symptoms=request.symptoms,
                top_k=5,
            )
        )
        result = state.get("result", {})
        elapsed = int((time.time() - start) * 1000)

        response = MedicalQueryResponse(
            query=", ".join(request.symptoms),
            answer=result.get("answer", "Unable to retrieve information."),
            confidence_score=result.get("confidence_score", 0.0),
            sources=result.get("sources", []),
            agent_used=state.get("agent_used", "Symptom Knowledge Agent"),
            response_time_ms=elapsed,
        )
        return response

    async def treatment_protocol_query(
        self,
        request: TreatmentProtocolRequest,
        user_id: Optional[str] = None,
    ) -> TreatmentProtocolResponse:
        """Treatment protocol retrieval."""
        start = time.time()
        loop = asyncio.get_event_loop()
        state = await loop.run_in_executor(
            _executor,
            lambda: self._orchestrator.run(
                query=f"treatment protocol guidelines {request.condition}",
                query_type="treatment",
                condition=request.condition,
                top_k=5,
            )
        )
        result = state.get("result", {})
        elapsed = int((time.time() - start) * 1000)

        if "condition" in result:
            return TreatmentProtocolResponse(**result)

        raw = self._rag.treatment_protocol_query(condition=request.condition)
        lines = raw["answer"].split("\n")
        steps = [l.strip() for l in lines if l.strip()]

        return TreatmentProtocolResponse(
            condition=request.condition,
            protocol_summary=raw["answer"],
            treatment_steps=steps[:10],
            sources=raw["citations"],
            confidence_score=raw["confidence"],
        )

    async def _log_query(
        self,
        query_type: str,
        query_text: str,
        response_summary: str,
        confidence: float,
        response_time_ms: int,
        user_id: Optional[str] = None,
        source_ids: Optional[List[str]] = None,
    ) -> None:
        log = QueryLog(
            user_id=user_id,
            query_type=query_type,
            query_text=query_text,
            response_summary=response_summary,
            sources_used=json.dumps(source_ids or []),
            confidence_score=confidence,
            response_time_ms=response_time_ms,
        )
        self.db.add(log)
