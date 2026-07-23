import time
import uuid
import logging
import jwt

from fastapi import APIRouter, Request

from models import ChatCompletionRequestBody

router = APIRouter()
logger = logging.getLogger(__name__)

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

    # Extract JWT
    token = req.headers.get("x-openwebui-user-jwt")
    if token:
        try:
            # Decode without verification (verify=False)
            # To verify, you need the secret key from open-webui
            decoded = jwt.decode(token, options={"verify_signature": False})
            logger.info("JWT payload: {0}".format(decoded))
            # Access fields: decoded["email"], decoded["name"], decoded["role"], etc.
        except jwt.DecodeError as e:
            logger.error("JWT decode failed: {0}".format(e))

    logger.info("Body: {0}".format(request))

    return {
        "id": f"chatcmpl-{uuid.uuid4()}",
        "object": "chat.completion",
        "created": int(time.time()),
        "model": request.model,
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": "Hello from my FastAPI backend!",
                },
                "finish_reason": "stop",
            }
        ],
    }