FROM python:3.13-slim@sha256:09a17cad02668ae61ece136b4fd36ac3849e14f670ebedb637ea3e15580525bc AS base
WORKDIR /app
ARG APP_REVISION=local
LABEL org.opencontainers.image.revision=$APP_REVISION
LABEL org.opencontainers.image.source="https://github.com/johanniemann/delopgave2-iot-mvp"
ENV APP_REVISION=$APP_REVISION
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 UV_LINK_MODE=copy UV_NO_CACHE=1
RUN pip install --no-cache-dir uv==0.9.27
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project
COPY app ./app
USER 10001:10001
EXPOSE 8000
CMD ["/app/.venv/bin/uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--no-proxy-headers"]

FROM base AS test
USER root
RUN uv sync --frozen --no-install-project
COPY tests ./tests
USER 10001:10001
CMD ["/app/.venv/bin/python", "-m", "pytest", "-q", "-p", "no:cacheprovider"]

FROM base AS runtime
