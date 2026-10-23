# Build the React bundle; Node is not included in the serving image.
FROM node:24-bookworm-slim AS frontend
WORKDIR /build/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --include=dev
COPY frontend/ ./
RUN npm run build

FROM python:3.12-slim-bookworm AS runtime
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    OMP_NUM_THREADS=1 \
    OPENBLAS_NUM_THREADS=1 \
    MKL_NUM_THREADS=1 \
    MALLOC_ARENA_MAX=2 \
    FRONTEND_DIST=/app/frontend/dist
WORKDIR /app/backend
COPY backend/requirements.txt ./
RUN python -m pip install --no-cache-dir -r requirements.txt \
    && python -m pip check \
    && useradd --uid 10001 --create-home --shell /usr/sbin/nologin helpdesk
COPY backend/app/ ./app/
COPY backend/data/ ./data/
COPY backend/alembic/ ./alembic/
COPY backend/alembic.ini ./
COPY --from=frontend /build/frontend/dist/ /app/frontend/dist/
USER 10001:10001
EXPOSE 10000
CMD ["python", "-m", "app.start"]
