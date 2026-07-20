"""공통 전처리 Pipeline과 비교할 tree regression 모델 factory."""

from __future__ import annotations

from typing import Any

from lightgbm import LGBMRegressor
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestRegressor
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder
from xgboost import XGBRegressor

from app.ml.config import N_JOBS, RANDOM_STATE

MODEL_NAMES = ("random_forest", "lightgbm", "xgboost")


def tuning_candidates(model_name: str) -> list[dict[str, Any]]:
    """과도한 탐색 대신 작은 사전 정의 공간으로 시간순 holdout tuning을 수행한다."""

    candidates = {
        "random_forest": [
            {"n_estimators": 300, "max_depth": None, "min_samples_leaf": 4},
            {"n_estimators": 400, "max_depth": 12, "min_samples_leaf": 3},
        ],
        "lightgbm": [
            {"n_estimators": 350, "learning_rate": 0.03, "num_leaves": 15},
            {"n_estimators": 450, "learning_rate": 0.025, "num_leaves": 31},
        ],
        "xgboost": [
            {"n_estimators": 350, "learning_rate": 0.03, "max_depth": 3},
            {"n_estimators": 450, "learning_rate": 0.025, "max_depth": 4},
        ],
    }
    try:
        return candidates[model_name]
    except KeyError as exception:
        raise ValueError(f"지원하지 않는 모델입니다: {model_name}") from exception


def build_estimator(model_name: str, parameters: dict[str, Any]):
    """공정한 비교를 위해 공통 seed와 CPU 병렬 설정으로 estimator를 생성한다."""

    if model_name == "random_forest":
        return RandomForestRegressor(
            random_state=RANDOM_STATE,
            n_jobs=N_JOBS,
            max_features=0.8,
            **parameters,
        )
    if model_name == "lightgbm":
        return LGBMRegressor(
            random_state=RANDOM_STATE,
            n_jobs=N_JOBS,
            verbosity=-1,
            subsample=0.9,
            colsample_bytree=0.9,
            reg_lambda=0.1,
            **parameters,
        )
    if model_name == "xgboost":
        xgboost_parameters = parameters.copy()
        objective = xgboost_parameters.pop("objective", "reg:squarederror")
        return XGBRegressor(
            objective=objective,
            random_state=RANDOM_STATE,
            n_jobs=N_JOBS,
            subsample=0.9,
            colsample_bytree=0.9,
            reg_lambda=1.0,
            **xgboost_parameters,
        )
    raise ValueError(f"지원하지 않는 모델입니다: {model_name}")


def build_pipeline(
    model_name: str,
    parameters: dict[str, Any],
    numeric_features: list[str],
    categorical_features: list[str],
) -> Pipeline:
    """학습/추론에서 같은 결측 처리와 one-hot encoder를 재사용하는 Pipeline을 만든다."""

    numeric_pipeline = Pipeline(
        steps=[
            (
                "imputer",
                SimpleImputer(strategy="median", add_indicator=True, keep_empty_features=True),
            )
        ]
    )
    categorical_pipeline = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="most_frequent")),
            (
                "one_hot",
                OneHotEncoder(handle_unknown="ignore", sparse_output=False),
            ),
        ]
    )
    preprocessor = ColumnTransformer(
        transformers=[
            ("numeric", numeric_pipeline, numeric_features),
            ("categorical", categorical_pipeline, categorical_features),
        ],
        remainder="drop",
        verbose_feature_names_out=False,
    )
    return Pipeline(
        steps=[
            ("preprocessor", preprocessor),
            ("estimator", build_estimator(model_name, parameters)),
        ]
    )
