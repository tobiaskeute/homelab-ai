import time
import uuid
import logging
import jwt
import os

from fastapi import APIRouter, Request, HTTPException
from langchain_core.messages import AIMessage

from models import ChatCompletionRequestBody

from core.langgraph.graph import LangGraphAgent

agent = LangGraphAgent()

router = APIRouter()
logger = logging.getLogger(__name__)

JWT_SECRET = os.getenv("OPENWEBUI_JWT_SECRET")

@router.get("/v1/models")
def list_models(request: Request):
    logger.info("Headers: {0}".format(dict(request.headers)))

    return {
        "object": "list",
        "data": [
            {
                "id": "homelab-agent",
                "object": "model",
                "owned_by": "me",
            }
        ],
    }


@router.post("/v1/chat/completions")
def chat(request: ChatCompletionRequestBody, req: Request):
    logger.info("Headers: {0}".format(dict(req.headers)))

    # Extract and verify JWT
    token = req.headers.get("x-openwebui-user-jwt")
    if not token:
        raise HTTPException(status_code=401, detail="Missing JWT token")

    if not JWT_SECRET:
        logger.warning("OPENWEBUI_JWT_SECRET not set, skipping signature verification")
        decoded = jwt.decode(token, options={"verify_signature": False})
    else:
        try:
            decoded = jwt.decode(
                token,
                JWT_SECRET,
                algorithms=["HS256"],
                issuer="open-webui"
            )
            logger.info("JWT verified and decoded: {0}".format(decoded))
        except jwt.ExpiredSignatureError:
            raise HTTPException(status_code=401, detail="JWT token expired")
        except jwt.InvalidIssuerError:
            raise HTTPException(status_code=401, detail="Invalid JWT issuer")
        except jwt.InvalidSignatureError:
            raise HTTPException(status_code=401, detail="Invalid JWT signature")
        except jwt.DecodeError as e:
            raise HTTPException(status_code=401, detail="JWT decode failed: {0}".format(e))

    logger.info("Body: {0}".format(request))

    langgraph_agent_reponse = agent.get_response(
        chat_id = req.headers.get("x-openwebui-chat-id", ""),
        task_name = req.headers.get("x-task-name", ""),
        message = request.messages[-1],
    )
    for m in langgraph_agent_reponse.messages:
        logger.info("message: {}".format(m))
    last_message: AIMessage = langgraph_agent_reponse.messages[-1]

    return {
        "id": f"chatcmpl-{uuid.uuid4()}",
        "object": "chat.completion",
        "created": int(time.time()),
        "model": request.model,
        "choices": [
            {
                "index": 0,
                "message": {
                    "content": last_message.content,
                    "role": "assistant",
                },
                "finish_reason": "stop",
            }
        ],
    }