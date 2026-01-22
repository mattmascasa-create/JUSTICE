"""
AI Chat Router - AI Attorney chat functionality
"""
import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, Depends

from app.db.database import db
from app.core.security import get_current_user
from app.services.ai_service import create_llm_chat, AI_ATTORNEY_SYSTEM_PROMPT
from app.models.schemas import ChatMessage, ChatResponse

try:
    from emergentintegrations.llm.chat import UserMessage
except ImportError:
    UserMessage = None

router = APIRouter(prefix="/ai", tags=["AI Attorney"])


@router.post("/chat", response_model=ChatResponse)
async def ai_chat(message: ChatMessage, current_user: dict = Depends(get_current_user)):
    """Chat with AI Attorney"""
    session_id = message.session_id or f"chat_{current_user['user_id']}_{uuid.uuid4().hex[:8]}"
    
    # Get or create conversation
    conversation = await db.ai_conversations.find_one(
        {"session_id": session_id},
        {"_id": 0}
    )
    
    if not conversation:
        conversation = {
            "session_id": session_id,
            "user_id": current_user["user_id"],
            "messages": [],
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        await db.ai_conversations.insert_one(conversation)
    
    # Add user message to history
    await db.ai_conversations.update_one(
        {"session_id": session_id},
        {"$push": {"messages": {
            "role": "user",
            "content": message.message,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }}}
    )
    
    # Generate AI response
    response_text = "I'm here to help you understand your civil rights."
    violation_detected = False
    violation_type = None
    rights_reminder = None
    
    llm = create_llm_chat(session_id, AI_ATTORNEY_SYSTEM_PROMPT)
    
    if llm and UserMessage:
        try:
            response = await llm.send_message(UserMessage(text=message.message))
            if response:
                response_text = response
                
                # Check for violation keywords
                msg_lower = message.message.lower()
                if any(word in msg_lower for word in ['search', 'searched', 'trunk', 'bag']):
                    violation_detected = True
                    violation_type = "4th Amendment - Search & Seizure"
                    rights_reminder = "You have the right to refuse consent to a search."
                elif any(word in msg_lower for word in ['arrest', 'detained', 'handcuff']):
                    violation_detected = True
                    violation_type = "Potential Unlawful Detention"
                    rights_reminder = "Ask: 'Am I being detained or am I free to go?'"
                elif any(word in msg_lower for word in ['hit', 'pushed', 'force', 'taser']):
                    violation_detected = True
                    violation_type = "Excessive Force"
                    rights_reminder = "Do not resist physically, but remember to document everything."
        except Exception as e:
            response_text = f"I apologize, but I'm having trouble processing your request. Please try again. Error: {str(e)}"
    
    # Add AI response to history
    await db.ai_conversations.update_one(
        {"session_id": session_id},
        {"$push": {"messages": {
            "role": "assistant",
            "content": response_text,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "violation_detected": violation_detected,
            "violation_type": violation_type
        }}}
    )
    
    return ChatResponse(
        response=response_text,
        session_id=session_id,
        violation_detected=violation_detected,
        violation_type=violation_type,
        rights_reminder=rights_reminder
    )


@router.get("/conversations")
async def get_conversations(current_user: dict = Depends(get_current_user)):
    """Get user's AI conversation history"""
    conversations = await db.ai_conversations.find(
        {"user_id": current_user["user_id"]},
        {"_id": 0}
    ).sort("created_at", -1).to_list(20)
    
    return conversations


@router.get("/conversations/{session_id}")
async def get_conversation(session_id: str, current_user: dict = Depends(get_current_user)):
    """Get specific conversation"""
    conversation = await db.ai_conversations.find_one(
        {"session_id": session_id, "user_id": current_user["user_id"]},
        {"_id": 0}
    )
    
    if not conversation:
        return {"session_id": session_id, "messages": []}
    
    return conversation


@router.delete("/conversations/{session_id}")
async def delete_conversation(session_id: str, current_user: dict = Depends(get_current_user)):
    """Delete a conversation"""
    result = await db.ai_conversations.delete_one(
        {"session_id": session_id, "user_id": current_user["user_id"]}
    )
    
    return {"deleted": result.deleted_count > 0}
