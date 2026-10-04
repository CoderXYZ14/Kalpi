FROM node:22-alpine AS frontend

WORKDIR /frontend
RUN corepack enable
COPY frontend/package.json frontend/pnpm-lock.yaml ./
RUN pnpm install --frozen-lockfile
COPY frontend/ ./
RUN pnpm build


FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY requirements.txt requirements-nodeps.txt ./
RUN pip install -r requirements.txt && pip install --no-deps -r requirements-nodeps.txt

COPY . .
COPY --from=frontend /frontend_dist ./frontend_dist
RUN python manage.py collectstatic --noinput && chmod +x entrypoint.sh

EXPOSE 8000

ENTRYPOINT ["./entrypoint.sh"]
