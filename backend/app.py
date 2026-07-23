import logging

from fastapi import FastAPI
from routers import openai

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

app = FastAPI()

app.include_router(openai.router)