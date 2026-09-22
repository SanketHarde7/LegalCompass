from typing import List, Optional
from pydantic import BaseModel, Field, ConfigDict
from .contract import RiskLevel


from pydantic import BaseModel, Field, ConfigDict, model_validator

class TriggeredClauseItem(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    clause_id: str = Field(alias="clauseId", description="Referenced clause ID")
    clause_title: str = Field(alias="clauseTitle", description="Referenced clause heading")
    impact: str = Field(description="Concrete impact of this clause on the scenario")


class SimulateScenarioRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    session_id: str = Field(alias="sessionId", description="Active contract session UUID")
    scenario_prompt: str = Field(
        default="", alias="scenarioPrompt", description="Hypothetical inquiry or scenario trigger"
    )

    @model_validator(mode="before")
    @classmethod
    def handle_scenario_alias(cls, data: dict):
        if isinstance(data, dict):
            if not data.get("scenarioPrompt") and not data.get("scenario_prompt") and data.get("scenario"):
                data["scenarioPrompt"] = data["scenario"]
        return data


class ScenarioSimulationResult(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    scenario_title: str = Field(alias="scenarioTitle", description="Short title of the scenario")
    triggered_clauses: List[TriggeredClauseItem] = Field(
        alias="triggeredClauses", default_factory=list, description="Clauses invoked by this scenario"
    )
    risk_evaluation: str = Field(
        alias="riskEvaluation", description="Deep legal outcome and leverage analysis"
    )
    financial_exposure: str = Field(
        alias="financialExposure", description="Quantified or qualitative financial threat"
    )
    recommended_action: str = Field(
        alias="recommendedAction", description="Actionable immediate steps to mitigate risk"
    )
    risk_level: RiskLevel = Field(
        default="HIGH", alias="riskLevel", description="Overall risk level of the scenario"
    )
