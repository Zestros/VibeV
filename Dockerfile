FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    QT_QPA_PLATFORM=offscreen

RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 \
    python3-venv \
    python3-pip \
    libdbus-1-3 \
    libegl1 \
    libfontconfig1 \
    fonts-dejavu-core \
    fonts-liberation \
    libgl1 \
    libgl1-mesa-dri \
    libglib2.0-0 \
    libnss3 \
    libpulse0 \
    libx11-xcb1 \
    libxkbcommon-x11-0 \
    libxcb-cursor0 \
    libxcb-icccm4 \
    libxcb-image0 \
    libxcb-keysyms1 \
    libxcb-randr0 \
    libxcb-render-util0 \
    libxcb-shape0 \
    libxcb-xfixes0 \
    libxcb-xinerama0 \
    libva2 \
    libva-x11-2 \
    xauth \
    xvfb \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
RUN python3 -m venv /opt/vibe-venv
ENV PATH="/opt/vibe-venv/bin:$PATH"

COPY requirements.txt requirements-dev.txt ./
RUN pip install --no-cache-dir --upgrade pip setuptools wheel \
    && pip install --no-cache-dir -r requirements-dev.txt

COPY . .
RUN pip install --no-cache-dir --no-build-isolation --no-deps -e .

CMD ["pytest", "-q"]
