from fastapi import APIRouter, HTTPException, status
from app.schemas.simulate import SimulateScenarioRequest, ScenarioSimulationResult
from app.services.rag_engine import rag_engine
from app.services.llm_service import llm_service
from app.schemas.contract import Clause
from typing import List

router = APIRouter()


@router.post(
    "/simulate-scenario",
    response_model=ScenarioSimulationResult,
    summary="Runs deterministic What-If scenario simulation against active contract",
)
async def simulate_scenario(request: SimulateScenarioRequest):
    """Evaluates hypothetical real-world triggers against active contract clauses."""
    session_id = request.session_id
    prompt = request.scenario_prompt.strip()

    if not prompt:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "INVALID_INPUT", "message": "Scenario prompt cannot be empty."},
        )

    # 1. Retrieve RAG context with multi-clause coverage
    session = rag_engine.get_session(session_id)
    context_clauses: List[Clause] = []
    if session:
        context_clauses = rag_engine.retrieve_top_k(session_id, prompt, k=7)
        prompt_lower = prompt.lower()
        # If prompt is a cross-cutting scenario (e.g. client cancels midway), ensure termination & payment clauses are present
        if any(w in prompt_lower for w in ["cancel", "terminate", "stops paying", "midway"]):
            for c in session.clauses:
                if c.category in ["TERMINATION", "PAYMENT_TERMS"] and c not in context_clauses:
                    context_clauses.append(c)
                    if len(context_clauses) >= 9:
                        break

    # 2. Run simulation
    result = await llm_service.simulate_scenario(
        session_id=session_id,
        prompt=prompt,
        context_clauses=context_clauses,
    )

    return result
