FROM python:3.11-buster

RUN apt-get update && apt-get install -y \
    libgl1-mesa-glx \
    && rm -rf /var/lib/apt/lists/*

RUN mkdir app
WORKDIR /app
# RUN pip install google-api-python-client

COPY requirements.txt .
RUN pip install --upgrade pip && pip install --no-cache-dir -r requirements.txt

COPY src/ .

ENV PATH="${PATH}:/root/.local/bin"
ENV PYTHONPATH=.

# CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "5000", "--ssl-keyfile", "key.pem", "--ssl-certfile", "cert.pem"]

CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "5000", "--reload"]
