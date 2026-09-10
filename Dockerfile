FROM python:3.12-slim

RUN groupadd --system mcp && \
    useradd --system \
    --gid mcp \
    --no-create-home \
    --shell /usr/sbin/nologin \
    mcp

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .

# /app/data (capture.py's SESSIONS_LOG) is where the named volume mounts --
# create and chown it here, before switching users, so a fresh volume
# inherits ownership the non-root process can actually write to. Same fix
# mirage-crawl and mirage-core both needed for their own data volumes.
RUN mkdir -p /app/data && chown -R mcp:mcp /app/data

USER mcp
EXPOSE 8765
CMD ["python", "run.py"]
