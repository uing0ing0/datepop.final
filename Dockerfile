# 사용할 기본 이미지. Python 3.9와 Debian Buster를 사용하는 이미지를 기반으로 합니다.
FROM python:3.12

# 작업 디렉토리 설정
WORKDIR /app

# Selenium과 Firefox를 사용하기 위한 종속성 설치
RUN apt-get -y update && apt-get install -y \
    firefox-esr \
    wget \
    && rm -rf /var/lib/apt/lists/*

# GeckoDriver 설치 (Selenium 4부터 필요 없을 수 있으나, 명시적 설치를 권장합니다.)
RUN wget https://github.com/mozilla/geckodriver/releases/download/v0.34.0/geckodriver-v0.34.0-linux64.tar.gz \
    && tar -xzf geckodriver-v0.34.0-linux64.tar.gz \
    && mv geckodriver /usr/local/bin \
    && rm geckodriver-v0.34.0-linux64.tar.gz

ENV PATH="/usr/local/bin:${PATH}"

# 프로젝트의 종속성 파일 복사
COPY poetry.lock pyproject.toml ./

# Poetry 설치
RUN pip install poetry

# 프로젝트의 종속성 설치
RUN poetry config virtualenvs.create false \
    && poetry install --no-dev

# 프로젝트 파일 복사
COPY . .

# 컨테이너 실행 시 기본으로 실행할 명령어 설정 (Celery Worker 실행)
CMD ["celery", "-A", "eagle_eye", "worker", "--loglevel=info", "--concurrency=1"]
