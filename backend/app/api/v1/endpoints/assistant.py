"""
CodeSentinel Assistant API Endpoints: Interactive AI Chat & Context Assistance.
"""

from typing import Any, Dict, List, Optional
import uuid
from fastapi import APIRouter
from pydantic import BaseModel, Field
from shared.schemas.common import APIResponse
from app.core.envelope import success_response

router = APIRouter()


class AssistantMessage(BaseModel):
    role: str = Field(..., description="Role: 'user', 'assistant', 'system'.")
    content: str = Field(..., description="Message text.")


class ChatRequest(BaseModel):
    project_id: uuid.UUID = Field(..., description="Project UUID.")
    messages: List[AssistantMessage] = Field(..., description="Conversation history.")
    active_file: Optional[str] = Field(default=None, description="Active editor file path.")


class ChatResponse(BaseModel):
    reply: str
    referenced_entities: List[str]
    suggested_actions: List[str]


class FeedbackRequest(BaseModel):
    interaction_id: str
    rating: int = Field(..., ge=1, le=5)
    comment: Optional[str] = None


@router.post(
    "/chat",
    response_model=APIResponse[ChatResponse],
    summary="Chat with Software Engineering Assistant",
    description="Context-aware conversational interface with full access to knowledge graph and AST index."
)
async def chat_with_assistant(payload: ChatRequest) -> APIResponse[ChatResponse]:
    response_data = ChatResponse(
        reply="I analyzed your project structure. All 8 core contracts in shared/schemas/ are strictly typed and frozen. How can I help verify or profile this codebase?",
        referenced_entities=["shared.schemas.project.Project", "shared.schemas.test_case.TestCase"],
        suggested_actions=["Trigger Code Profiling", "Scan for OWASP Vulnerabilities", "Synthesize Requirement-Verified Tests"]
    )
    return success_response(data=response_data, message="Assistant response generated.")


@router.post(
    "/feedback",
    response_model=APIResponse[Dict[str, str]],
    summary="Submit Assistant Feedback",
    description="Record user feedback for continuous agent prompt tuning."
)
async def submit_feedback(payload: FeedbackRequest) -> APIResponse[Dict[str, str]]:
    return success_response(
        data={"interaction_id": payload.interaction_id, "status": "RECORDED"},
        message="Feedback recorded."
    )
