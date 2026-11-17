FROM python:3.11-alpine

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY planta_gemela.py ./

EXPOSE 5020

CMD ["python", "-u", "planta_gemela.py", "--planta", "1", "--puerto", "5020", "--dt", "0.25", "--vel", "1.0"]
