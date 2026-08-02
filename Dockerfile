# The Seventh Councilor — containerized analyzers.
#
# Usage and the reasoning behind the read-only mounts: SECURITY.md § Running it in a container.
#
# There is deliberately no `pip install` step: the analyzers are standard-library only, so
# nothing is fetched at build time beyond the base image, and there is no dependency supply
# chain to compromise.

FROM python:3.12-slim

# Run as a normal user, not root.
RUN useradd --create-home --uid 1000 councilor

WORKDIR /app
COPY --chown=councilor:councilor . /app

USER councilor

# Your saves and game install are mounted read-only at /saves and /game — the container
# cannot modify either. Point config.json at those paths (see SECURITY.md).
CMD ["bash"]
