"""
NyayGuru AI Pro - Chat API Routes
Handles chat interactions and query processing.
"""

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect, Depends
from fastapi.responses import StreamingResponse
from typing import List
import json
import asyncio
from datetime import datetime
import uuid

from app.schemas import (
    ChatMessageRequest, 
    ChatMessageResponse, 
    ChatStreamChunk,
    AgentInfo,
    AgentPipelineStatus
)
from app.agents.orchestrator import get_orchestrator
from app.services.auth_service import get_current_user_optional, get_current_user
from app.services.chat_service import get_chat_service
from app.database import get_db

router = APIRouter(prefix="/api/chat", tags=["chat"])


@router.post("/", response_model=dict)
async def process_chat_message(
    request: ChatMessageRequest,
    current_user: dict = Depends(get_current_user_optional),
    db = Depends(get_db)
):
    """
    Process a legal query through the multi-agent pipeline.
    Returns comprehensive legal information with citations.
    Messages are saved to database for chat history.
    """
    import logging
    logger = logging.getLogger(__name__)
    
    # DEBUG: Log incoming request to verify domain is received
    print(f"\n{'#'*60}")
    print(f"[CHAT API] ===== NEW CHAT REQUEST =====")
    print(f"[CHAT API] Content: '{request.content[:80]}...'")
    print(f"[CHAT API] Domain: '{request.domain}'")
    print(f"[CHAT API] Language: '{request.language}'")
    print(f"[CHAT API] Session ID: '{request.session_id}'")
    print(f"{'#'*60}\n")
    
    logger.info(f"[CHAT API] Received request - Content: '{request.content[:50]}...'")
    logger.info(f"[CHAT API] Domain from frontend: '{request.domain}'")
    logger.info(f"[CHAT API] Language: '{request.language}'")
    logger.info(f"[CHAT API] Session ID: '{request.session_id}'")
    
    orchestrator = get_orchestrator()
    chat_service = get_chat_service()
    
    try:
        # Get user ID from current_user
        user_id = current_user.get("user_id") if current_user else None
        
        # Get or create chat session
        session = chat_service.get_or_create_session(
            db=db,
            session_id=request.session_id,
            user_id=user_id,
            language=request.language.value,
            domain=request.domain
        )
        
        # Save user message to database
        chat_service.save_message(
            db=db,
            session_id=session.session_id,
            role="user",
            content=request.content
        )
        
        # Process query through AI pipeline
        result = await orchestrator.process_query(
            query=request.content,
            language=request.language.value,
            session_id=session.session_id,
            domain=request.domain
        )
        
        # Extract response content
        ai_content = result.get("response", {}).get("content", "")
        ai_content_hi = result.get("response", {}).get("content_hi")
        citations = result.get("citations", [])
        
        # Save AI response to database
        chat_service.save_message(
            db=db,
            session_id=session.session_id,
            role="assistant",
            content=ai_content,
            content_hi=ai_content_hi,
            citations=citations,
            agent_path=[step.get("agent") for step in result.get("agent_pipeline", [])]
        )
        
        # Format response
        response = {
            "id": result.get("id"),
            "session_id": session.session_id,
            "role": "assistant",
            "content": ai_content,
            "content_hi": ai_content_hi,
            "citations": citations,
            "statutes": result.get("statutes", []),
            "case_laws": result.get("case_laws", []),
            "ipc_bns_mappings": result.get("ipc_bns_mappings", []),
            "agent_pipeline": result.get("agent_pipeline", []),
            "detected_domain": result.get("detected_domain"),
            "detected_language": result.get("detected_language"),
            "execution_time_seconds": result.get("execution_time_seconds"),
            "timestamp": datetime.now().isoformat()
        }
        
        return response
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/stream")
async def process_chat_message_stream(
    request: ChatMessageRequest,
    current_user: dict = Depends(get_current_user_optional)
):
    """
    Process a legal query with streaming updates.
    Returns server-sent events for real-time UI updates.
    Messages are saved to database for chat history.
    """
    import logging
    from app.database import get_db_context
    logger = logging.getLogger(__name__)
    
    # DEBUG: Log incoming streaming request
    print(f"\n{'#'*60}")
    print(f"[CHAT STREAM API] ===== NEW STREAMING REQUEST =====")
    print(f"[CHAT STREAM API] Content: '{request.content[:80]}...'")
    print(f"[CHAT STREAM API] Domain: '{request.domain}'")
    print(f"[CHAT STREAM API] Language: '{request.language}'")
    print(f"[CHAT STREAM API] Session ID: '{request.session_id}'")
    print(f"{'#'*60}\n")
    
    logger.info(f"[CHAT STREAM API] Received request - Content: '{request.content[:50]}...'")
    logger.info(f"[CHAT STREAM API] Domain from frontend: '{request.domain}'")
    
    orchestrator = get_orchestrator()
    chat_service = get_chat_service()
    
    # Get database session and set up chat session
    user_id = current_user.get("user_id") if current_user else None
    
    with get_db_context() as db:
        session = chat_service.get_or_create_session(
            db=db,
            session_id=request.session_id,
            user_id=user_id,
            language=request.language.value,
            domain=request.domain
        )
        
        # Save user message
        chat_service.save_message(
            db=db,
            session_id=session.session_id,
            role="user",
            content=request.content
        )
    
    async def generate():
        try:
            final_response = None
            final_response_hi = None
            final_citations = []
            
            async for chunk in orchestrator.process_query_streaming(
                query=request.content,
                language=request.language.value,
                session_id=session.session_id,
                domain=request.domain
            ):
                # Capture final response for saving
                if chunk.type == "response":
                    final_response = chunk.data.get("content", "")
                    final_response_hi = chunk.data.get("content_hi")
                    final_citations = chunk.data.get("citations", [])
                
                yield f"data: {json.dumps(chunk.model_dump())}\n\n"
                await asyncio.sleep(0.01)
            
            # Save AI response to database after streaming completes
            if final_response:
                try:
                    with get_db_context() as db_inner:
                        chat_service.save_message(
                            db=db_inner,
                            session_id=session.session_id,
                            role="assistant",
                            content=final_response,
                            content_hi=final_response_hi,
                            citations=final_citations
                        )
                except Exception as save_error:
                    # Log but don't fail the stream
                    import logging
                    logging.error(f"Failed to save AI response: {save_error}")
                    
        except Exception as e:
            error_chunk = {"type": "error", "data": {"message": str(e)}}
            yield f"data: {json.dumps(error_chunk)}\n\n"
    
    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


@router.websocket("/ws/{session_id}")
async def websocket_chat(websocket: WebSocket, session_id: str):
    """
    WebSocket endpoint for real-time chat.
    Provides streaming updates for agent processing.
    """
    await websocket.accept()
    orchestrator = get_orchestrator()
    
    try:
        while True:
            # Receive message from client
            data = await websocket.receive_text()
            message_data = json.loads(data)
            
            query = message_data.get("content", "")
            language = message_data.get("language", "en")
            
            # Stream processing updates
            async for chunk in orchestrator.process_query_streaming(
                query=query,
                language=language,
                session_id=session_id
            ):
                await websocket.send_text(json.dumps(chunk.model_dump()))
            
    except WebSocketDisconnect:
        pass
    except Exception as e:
        error_msg = {"type": "error", "data": {"message": str(e)}}
        await websocket.send_text(json.dumps(error_msg))


@router.get("/agents", response_model=List[AgentInfo])
def get_agents():
    """Get information about all available agents."""
    orchestrator = get_orchestrator()
    
    agents_info = orchestrator.get_agent_info()
    
    # Add full descriptions
    descriptions = {
        "query": {
            "description": "Analyzes queries for language, legal domain, and intent",
            "description_hi": "भाषा, कानूनी क्षेत्र और आशय के लिए प्रश्नों का विश्लेषण करता है"
        },
        "statute": {
            "description": "Retrieves relevant IPC, BNS, and other statute sections",
            "description_hi": "संबंधित IPC, BNS और अन्य विधि अनुभाग प्राप्त करता है"
        },
        "case": {
            "description": "Finds relevant Supreme Court and High Court judgments",
            "description_hi": "प्रासंगिक सर्वोच्च न्यायालय और उच्च न्यायालय के निर्णय खोजता है"
        },
        "regulatory": {
            "description": "Filters by jurisdiction and regulatory category",
            "description_hi": "क्षेत्राधिकार और नियामक श्रेणी द्वारा फ़िल्टर करता है"
        },
        "citation": {
            "description": "Generates verifiable citations to official sources",
            "description_hi": "आधिकारिक स्रोतों के लिए सत्यापित उद्धरण उत्पन्न करता है"
        },
        "summary": {
            "description": "Summarizes legal documents and extracts key information",
            "description_hi": "कानूनी दस्तावेजों का सारांश और मुख्य जानकारी निकालता है"
        },
        "response": {
            "description": "Synthesizes comprehensive legal responses",
            "description_hi": "व्यापक कानूनी प्रतिक्रियाओं का संश्लेषण करता है"
        }
    }
    
    for agent in agents_info:
        agent_id = agent.get("id", "")
        if agent_id in descriptions:
            agent.update(descriptions[agent_id])
    
    return agents_info


@router.get("/history")
def get_chat_history(
    limit: int = 20,
    current_user: dict = Depends(get_current_user)
):
    """
    Get chat history for the current user.
    Returns a list of chat sessions with their titles and dates.
    """
    from app.database import get_db
    from app.models import ChatSession, ChatMessage
    from sqlalchemy import desc
    
    try:
        db = next(get_db())
        
        # Query chat sessions for the current user
        user_id = current_user.get("user_id") if current_user else None
        
        query = db.query(ChatSession)
        if user_id:
            query = query.filter(ChatSession.user_id == user_id)
        
        sessions = query.order_by(desc(ChatSession.last_activity)).limit(limit).all()
        
        result = []
        for session in sessions:
            # Get message count
            message_count = db.query(ChatMessage).filter(
                ChatMessage.session_id == session.id
            ).count()
            
            # Get first user message as title
            first_message = db.query(ChatMessage).filter(
                ChatMessage.session_id == session.id,
                ChatMessage.role == "user"
            ).first()
            
            title = first_message.content[:50] + "..." if first_message and len(first_message.content) > 50 else (first_message.content if first_message else "New Chat")
            
            # Format date
            if session.last_activity:
                from datetime import datetime, timedelta
                now = datetime.now()
                diff = now - session.last_activity
                
                if diff < timedelta(hours=1):
                    date_str = f"{int(diff.seconds / 60)} minutes ago"
                elif diff < timedelta(days=1):
                    date_str = f"{int(diff.seconds / 3600)} hours ago"
                elif diff < timedelta(days=7):
                    date_str = f"{diff.days} days ago"
                else:
                    date_str = session.last_activity.strftime("%b %d")
            else:
                date_str = "Unknown"
            
            result.append({
                "id": session.session_id,
                "title": title,
                "date": date_str,
                "messageCount": message_count,
                "language": session.language or "en",
                "domain": session.domain or "all"
            })
        
        return {"sessions": result}
        
    except Exception as e:
        # Log the actual error for debugging
        import logging
        logging.error(f"Error fetching chat history: {e}")
        # Return empty list if database not available or any error
        return {"sessions": []}


@router.get("/history/{session_id}")
def get_session_messages(
    session_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Get all messages for a specific chat session.
    """
    from app.database import get_db
    from app.models import ChatSession, ChatMessage
    
    try:
        db = next(get_db())
        
        # Find session
        session = db.query(ChatSession).filter(
            ChatSession.session_id == session_id
        ).first()
        
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        # Get all messages
        messages = db.query(ChatMessage).filter(
            ChatMessage.session_id == session.id
        ).order_by(ChatMessage.created_at).all()
        
        result = []
        for msg in messages:
            result.append({
                "id": str(msg.id),
                "role": msg.role,
                "content": msg.content,
                "contentHindi": msg.content_hi,
                "citations": msg.citations or [],
                "timestamp": msg.created_at.isoformat() if msg.created_at else None
            })
        
        return {
            "messages": result, 
            "sessionId": session_id,
            "domain": session.domain or "all"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/history/{session_id}")
def delete_session(
    session_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Delete a chat session and all its messages.
    """
    from app.database import get_db
    from app.models import ChatSession, ChatMessage
    
    try:
        db = next(get_db())
        
        # Find session
        session = db.query(ChatSession).filter(
            ChatSession.session_id == session_id
        ).first()
        
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        # Delete messages first
        db.query(ChatMessage).filter(
            ChatMessage.session_id == session.id
        ).delete()
        
        # Delete session
        db.delete(session)
        db.commit()
        
        return {"success": True, "message": "Session deleted"}
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

