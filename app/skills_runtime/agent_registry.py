from __future__ import annotations

from pydantic import BaseModel, Field


class AgentRegistration(BaseModel):
    name: str
    version: str
    allowed_skills: list[str] = Field(default_factory=list)
    allowed_tools: list[str] = Field(default_factory=list)
    may_request_production_promotion: bool = False
    may_approve_production: bool = False


class AgentRegistry:
    def __init__(self, registrations: list[AgentRegistration]) -> None:
        self._agents = {a.name: a for a in registrations}

    def get(self, name: str) -> AgentRegistration:
        if name not in self._agents:
            raise KeyError("agent_not_registered")
        return self._agents[name]

    def authorize_skill(self, agent_name: str, skill_name: str) -> bool:
        agent = self.get(agent_name)
        return skill_name in agent.allowed_skills or "*" in agent.allowed_skills

    def assert_no_self_approval(self) -> None:
        if any(a.may_approve_production for a in self._agents.values()):
            raise ValueError("agent_production_approval_forbidden")
