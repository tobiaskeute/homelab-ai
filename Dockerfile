FROM python:3.14

WORKDIR /src/backend

# Copy requirements first for better caching
COPY ./backend/requirements.txt .
RUN pip install --no-cache-dir --upgrade -r requirements.txt

# Copy the rest of the application
COPY ./backend/src .

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "80"]
