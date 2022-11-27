FROM python:3.11-slim-bullseye

RUN apt-get update -y && apt-get -y install \
        build-essential \
    && python -m pip install --upgrade pip \
    && pip install \
        fastapi==0.87.0 \
        uvicorn==0.20.0 \
    && apt-get -y autoremove --purge && apt-get clean

RUN mkdir /app /cache
RUN useradd -d /home -r app \
    && chown app /home /app /cache

USER app
WORKDIR /app
COPY src .

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8888"]
