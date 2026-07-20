"""학습과 API 추론이 공유하는 ML 파이프라인."""

import os

# 일부 Windows 환경에서 joblib의 물리 CPU 탐지 출력이 잘못 디코딩되는 문제를 방지한다.
os.environ.setdefault("LOKY_MAX_CPU_COUNT", os.getenv("ML_N_JOBS", "1"))
