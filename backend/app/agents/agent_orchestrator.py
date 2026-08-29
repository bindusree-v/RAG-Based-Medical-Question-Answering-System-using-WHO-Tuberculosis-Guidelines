"""
MediRAG AI – LangGraph Agent Orchestrator

Defines five specialized medical agents orchestrated via LangGraph:
  1. Medical Literature Agent
  2. Drug Interaction Agent
  3. Treatment Protocol Agent
  4. Medical QA Agent
  5. Knowledge Base Agent

LangGraph routes queries to the appropriate agent based on query type.
"""

from typing import Any, Dict, List, Literal, Optional, TypedDict

from langchain_community.llms import Ollama
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langgraph.graph import StateGraph, END

from app.config import settings
from app.models.schemas import (
    MedicalQueryResponse, DrugInteractionResponse, InteractionDetail,
    TreatmentProtocolResponse, SourceCitation,
)
from app.rag.rag_pipeline import get_rag_pipeline
from app.utils.logger import logger


# ---------------------------------------------------------------------------
# LangGraph State
# ---------------------------------------------------------------------------

class AgentState(TypedDict):
    query: str
    query_type: str  # "medical_qa" | "drug_interaction" | "treatment" | "symptom" | "literature"
    drug_a: Optional[str]
    drug_b: Optional[str]
    symptoms: Optional[List[str]]
    condition: Optional[str]
    top_k: int
    result: Optional[Dict[str, Any]]
    agent_used: str
    error: Optional[str]


# ---------------------------------------------------------------------------
# Router – classifies query type from natural language
# ---------------------------------------------------------------------------

ROUTER_PROMPT = PromptTemplate(
    input_variables=["query"],
    template="""Classify the following medical query into exactly one category.

QUERY: {query}

CATEGORIES:
- drug_interaction: Query is about drug interactions, contraindications, or drug combinations
- treatment: Query is about treatment protocols, guidelines, or management of a condition
- symptom: Query is about symptoms, differential diagnosis, or clinical presentation
- literature: Query is about medical research, studies, clinical evidence, or journals
- medical_qa: General medical question that doesn't fit the above

Respond with ONLY the category name, nothing else.

CATEGORY:""",
)


# ---------------------------------------------------------------------------
# Agent Node Functions
# ---------------------------------------------------------------------------

def route_query(state: AgentState) -> AgentState:
    """Route query to the appropriate agent using keyword matching only (no LLM call)."""
    query_lower = state["query"].lower()

    if any(w in query_lower for w in ["drug interaction", "contraindication", "adverse drug", "drug-drug"]):
        state["query_type"] = "drug_interaction"
    elif any(w in query_lower for w in ["treatment", "protocol", "guideline", "management", "therapy"]):
        state["query_type"] = "treatment"
    elif any(w in query_lower for w in ["symptom", "presenting", "differential", "complain"]):
        state["query_type"] = "symptom"
    elif any(w in query_lower for w in ["research", "study", "trial", "evidence", "journal", "literature"]):
        state["query_type"] = "literature"
    else:
        state["query_type"] = "medical_qa"

    logger.info(f"Query routed to: {state['query_type']}")
    return state


def medical_literature_agent(state: AgentState) -> AgentState:
    """Agent 1: Retrieves and synthesizes medical research literature."""
    rag = get_rag_pipeline()
    try:
        result = rag.medical_query(
            query=state["query"],
            k=state.get("top_k", 5),
            agent_name="Medical Literature Agent",
        )
        state["result"] = result.dict()
        state["agent_used"] = "Medical Literature Agent"
    except Exception as exc:
        logger.error(f"Medical Literature Agent error: {exc}")
        state["error"] = str(exc)
    return state


def drug_interaction_agent(state: AgentState) -> AgentState:
    """Agent 2: Analyzes drug-drug interactions and safety."""
    rag = get_rag_pipeline()
    try:
        drug_a = state.get("drug_a", "")
        drug_b = state.get("drug_b", "")

        # If drugs not explicitly provided, extract from query
        if not drug_a or not drug_b:
            result = rag.medical_query(
                query=state["query"],
                k=state.get("top_k", 5),
                agent_name="Drug Interaction Agent",
            )
            state["result"] = result.dict()
        else:
            raw = rag.drug_interaction_query(drug_a=drug_a, drug_b=drug_b, k=state.get("top_k", 5))
            response = DrugInteractionResponse(
                drugs_queried=[drug_a, drug_b],
                interactions_found=[
                    InteractionDetail(
                        drugs_involved=[drug_a, drug_b],
                        interaction_type="See analysis below",
                        severity="Refer to clinical context",
                        clinical_effects=raw["answer"],
                        management="Consult prescribing information and clinical pharmacist.",
                    )
                ],
                overall_risk_level="Evaluate per clinical context",
                clinical_summary=raw["answer"],
                monitoring_recommendations="Monitor as per clinical guidelines.",
                sources=raw["citations"],
                confidence_score=raw["confidence"],
            )
            state["result"] = response.dict()

        state["agent_used"] = "Drug Interaction Agent"
    except Exception as exc:
        logger.error(f"Drug Interaction Agent error: {exc}")
        state["error"] = str(exc)
    return state


def treatment_protocol_agent(state: AgentState) -> AgentState:
    """Agent 3: Retrieves clinical treatment protocols and pathways."""
    rag = get_rag_pipeline()
    try:
        condition = state.get("condition") or state["query"]
        raw = rag.treatment_protocol_query(condition=condition, k=state.get("top_k", 5))

        # Parse treatment steps from the LLM output
        lines = raw["answer"].split("\n")
        steps = [line.strip() for line in lines if line.strip() and not line.startswith("#")]

        response = TreatmentProtocolResponse(
            condition=condition,
            protocol_summary=raw["answer"],
            treatment_steps=steps[:10],
            sources=raw["citations"],
            confidence_score=raw["confidence"],
        )
        state["result"] = response.dict()
        state["agent_used"] = "Treatment Protocol Agent"
    except Exception as exc:
        logger.error(f"Treatment Protocol Agent error: {exc}")
        state["error"] = str(exc)
    return state


def medical_qa_agent(state: AgentState) -> AgentState:
    """Agent 4: Handles general evidence-based medical Q&A."""
    rag = get_rag_pipeline()
    try:
        result = rag.medical_query(
            query=state["query"],
            k=state.get("top_k", 5),
            agent_name="Medical QA Agent",
        )
        state["result"] = result.dict()
        state["agent_used"] = "Medical QA Agent"
    except Exception as exc:
        logger.error(f"Medical QA Agent error: {exc}")
        state["error"] = str(exc)
    return state


def symptom_agent(state: AgentState) -> AgentState:
    """Handles symptom-based queries (routes to literature for now)."""
    rag = get_rag_pipeline()
    try:
        symptoms = state.get("symptoms") or [state["query"]]
        raw = rag.symptom_query(symptoms=symptoms, k=state.get("top_k", 5))

        result = MedicalQueryResponse(
            query=state["query"],
            answer=raw["answer"],
            confidence_score=raw["confidence"],
            sources=raw["citations"],
            agent_used="Symptom Knowledge Agent",
            response_time_ms=raw["response_time_ms"],
        )
        state["result"] = result.dict()
        state["agent_used"] = "Symptom Knowledge Agent"
    except Exception as exc:
        logger.error(f"Symptom Agent error: {exc}")
        state["error"] = str(exc)
    return state


# ---------------------------------------------------------------------------
# Conditional Router
# ---------------------------------------------------------------------------

def choose_agent(
    state: AgentState,
) -> Literal["medical_literature", "drug_interaction", "treatment_protocol", "medical_qa", "symptom"]:
    qtype = state.get("query_type", "medical_qa")
    mapping = {
        "literature": "medical_literature",
        "drug_interaction": "drug_interaction",
        "treatment": "treatment_protocol",
        "symptom": "symptom",
        "medical_qa": "medical_qa",
    }
    return mapping.get(qtype, "medical_qa")


# ---------------------------------------------------------------------------
# Build LangGraph
# ---------------------------------------------------------------------------

def build_agent_graph() -> StateGraph:
    graph = StateGraph(AgentState)

    # Add nodes
    graph.add_node("router", route_query)
    graph.add_node("medical_literature", medical_literature_agent)
    graph.add_node("drug_interaction", drug_interaction_agent)
    graph.add_node("treatment_protocol", treatment_protocol_agent)
    graph.add_node("medical_qa", medical_qa_agent)
    graph.add_node("symptom", symptom_agent)

    # Entry point
    graph.set_entry_point("router")

    # Conditional routing after router
    graph.add_conditional_edges(
        "router",
        choose_agent,
        {
            "medical_literature": "medical_literature",
            "drug_interaction": "drug_interaction",
            "treatment_protocol": "treatment_protocol",
            "medical_qa": "medical_qa",
            "symptom": "symptom",
        },
    )

    # All agents finish at END
    for node in ["medical_literature", "drug_interaction", "treatment_protocol", "medical_qa", "symptom"]:
        graph.add_edge(node, END)

    return graph.compile()


# ---------------------------------------------------------------------------
# Orchestrator Class
# ---------------------------------------------------------------------------

class AgentOrchestrator:
    """High-level interface for running the LangGraph agent pipeline."""

    def __init__(self):
        self._graph = build_agent_graph()

    def run(
        self,
        query: str,
        query_type: Optional[str] = None,
        drug_a: Optional[str] = None,
        drug_b: Optional[str] = None,
        symptoms: Optional[List[str]] = None,
        condition: Optional[str] = None,
        top_k: int = 5,
    ) -> AgentState:
        """
        Execute the agent graph with the given inputs.
        Returns the final AgentState containing the result.
        """
        initial_state: AgentState = {
            "query": query,
            "query_type": query_type or "medical_qa",
            "drug_a": drug_a,
            "drug_b": drug_b,
            "symptoms": symptoms,
            "condition": condition,
            "top_k": top_k,
            "result": None,
            "agent_used": "Unknown",
            "error": None,
        }

        # If query_type is provided, skip the router
        if query_type:
            initial_state["query_type"] = query_type

        final_state = self._graph.invoke(initial_state)
        return final_state


_orchestrator_instance: Optional[AgentOrchestrator] = None


def get_agent_orchestrator() -> AgentOrchestrator:
    global _orchestrator_instance
    if _orchestrator_instance is None:
        _orchestrator_instance = AgentOrchestrator()
    return _orchestrator_instance
