FROM python:3.12-slim

LABEL org.opencontainers.image.source="https://github.com/codesphere-u/ai-wrapped"
LABEL org.opencontainers.image.description="Offline ChatGPT, Claude & Gemini Wrapped story + Portable AI Brain generator"
LABEL org.opencontainers.image.licenses="MIT"

WORKDIR /app
COPY pyproject.toml README.md LICENSE ./
COPY skills ./skills

RUN pip install --no-cache-dir . && useradd -m -u 10001 runner
USER runner
WORKDIR /data

ENTRYPOINT ["ai-wrapped"]
CMD ["--help"]
