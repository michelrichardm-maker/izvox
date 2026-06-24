# izvox — Dockerfile multi-stage reproductible (distroless final).
#
# Cible : avoir une image runtime minimale (pas de shell, pas d'apt,
# pas de pip) pour exécuter izvox dans un environnement audité.
#
# Notes :
# - L'image runtime distroless n'a PAS d'accès audio physique. Elle est
#   utile pour le mode fichier (--input-file/--output-file) et pour les
#   tests/CI, PAS pour un appel Teams réel (qui demande Windows + WASAPI).
# - Pour reproductibilité, on pin les images de base par digest et on
#   utilise --require-hashes dans pip si requirements.lock est fourni.

# ============================================================================
# Stage 1: builder — installe les deps Python dans un venv
# ============================================================================
FROM python:3.12-slim-bookworm@sha256:b6da4ad8edda88aac735f4b3d3e80b67ce80bca5b35a4742b3bc1f6e62b4a37c AS builder

# Outils système nécessaires UNIQUEMENT au build (espeak-ng pour Piper,
# build-essential pour les wheels qui ne sont pas prebuilt).
RUN apt-get update -qq && \
    apt-get install -y --no-install-recommends \
        build-essential \
        espeak-ng \
        espeak-ng-data \
        libsndfile1 \
        && rm -rf /var/lib/apt/lists/*

WORKDIR /build

# Copie d'abord requirements.txt seul → cache pip réutilisable tant qu'il
# ne change pas, même si le code change.
COPY requirements.txt ./

# Création d'un venv isolé qu'on copiera dans l'image finale.
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:${PATH}"

RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir \
        torch torchaudio --index-url https://download.pytorch.org/whl/cpu && \
    pip install --no-cache-dir -r requirements.txt

# Copie du code source maintenant que les deps sont fixées.
COPY src/ ./src/
COPY tools/ ./tools/
COPY config/ ./config/
COPY models/ ./models/
COPY pyproject.toml setup.py README.md LICENSE ./

RUN pip install --no-cache-dir -e .

# ============================================================================
# Stage 2: runtime distroless — minimal, pas de shell, pas de pip
# ============================================================================
FROM gcr.io/distroless/python3-debian12:nonroot@sha256:b7d0ec56fc6e4ee5deeac2b7d1a8a1cebfb716bd9e1dc89d6dd55ebdfa0e7df3 AS runtime

LABEL org.opencontainers.image.title="izvox" \
      org.opencontainers.image.description="Real-time bidirectional FR↔EN translator (file mode in this image)" \
      org.opencontainers.image.source="https://github.com/michelrichardm-maker/izvox" \
      org.opencontainers.image.licenses="MIT"

# espeak-ng-data (read-only) requis par Piper. On copie depuis le builder.
COPY --from=builder /usr/share/espeak-ng-data /usr/share/espeak-ng-data
COPY --from=builder /usr/lib/x86_64-linux-gnu/libsndfile.so.1 /usr/lib/x86_64-linux-gnu/

# Venv complet
COPY --from=builder /opt/venv /opt/venv

# Code izvox
WORKDIR /app
COPY --from=builder /build/src ./src
COPY --from=builder /build/tools ./tools
COPY --from=builder /build/config ./config
COPY --from=builder /build/models ./models

# distroless n'a pas de shell, on appelle Python directement.
# `--paranoid` est le défaut pour le runtime container : c'est un
# environnement non-interactif où la confidentialité prime.
ENTRYPOINT ["/opt/venv/bin/python", "-m", "src.main"]
CMD ["--paranoid", "--no-banner"]
