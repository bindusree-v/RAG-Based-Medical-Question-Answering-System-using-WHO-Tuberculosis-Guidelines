"""
MediRAG AI – Medical Query API Routes

POST /medical-query
POST /drug-interaction
POST /symptom-query
POST /treatment-protocol
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import get_db, User
from app.models.schemas import (
    MedicalQueryRequest, MedicalQueryResponse,
    DrugInteractionRequest, DrugInteractionResponse,
    SymptomQueryRequest, TreatmentProtocolRequest, TreatmentProtocolResponse,
)
from app.services.query_service import QueryService
from app.utils.security import get_current_user

router = APIRouter()


@router.post("/medical-query", response_model=MedicalQueryResponse)
async def medical_query(
    request: MedicalQueryRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Answer a medical question using RAG and the appropriate AI agent.
    Response includes grounded answer, source citations, and confidence score.
    """
    service = QueryService(db)
    return await service.medical_query(request=request, user_id=current_user.id)


@router.post("/drug-interaction", response_model=DrugInteractionResponse)
async def drug_interaction(
    request: DrugInteractionRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Analyze interactions between two or more drugs.
    Returns severity, mechanism, clinical effects, and management recommendations.
    """
    service = QueryService(db)
    return await service.drug_interaction_query(request=request, user_id=current_user.id)


@router.post("/symptom-query", response_model=MedicalQueryResponse)
async def symptom_query(
    request: SymptomQueryRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Retrieve medical knowledge based on presenting symptoms.
    Includes relevant differential considerations from medical literature.
    """
    service = QueryService(db)
    return await service.symptom_query(request=request, user_id=current_user.id)


@router.post("/treatment-protocol", response_model=TreatmentProtocolResponse)
async def treatment_protocol(
    request: TreatmentProtocolRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Retrieve evidence-based treatment protocols for a medical condition.
    Includes guidelines, first-line treatments, and monitoring parameters.
    """
    service = QueryService(db)
    return await service.treatment_protocol_query(request=request, user_id=current_user.id)
