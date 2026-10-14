FROM python:3.10-slim-buster

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY ./src/backend/requirements.txt /app/

RUN pip install --upgrade pip && \
    pip install --default-timeout=100 --retries 10 \
    -i https://pypi.tuna.tsinghua.edu.cn/simple \
    -r requirements.txt && \
    rm -rf ~/.cache/pip

COPY ./src /app

EXPOSE 8000

CMD ["python3", "backend/manage.py", "runserver", "0.0.0.0:8000"]