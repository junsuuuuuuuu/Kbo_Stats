"""조건 검색과 수치 기반 유사 선수 추천 도메인 서비스."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

import numpy as np
import pandas as pd
from sklearn.decomposition import PCA
from sklearn.impute import SimpleImputer
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.neighbors import NearestNeighbors
from sklearn.preprocessing import StandardScaler

from app.ml.recommendation_config import METRIC_LABELS, RECOMMENDATION_SPECS, RecommendationSpec


@dataclass(frozen=True, slots=True)
class NumericCondition:
    """허용된 기록 컬럼에 적용할 선택적 최솟값과 최댓값."""

    column: str
    minimum: float | None = None
    maximum: float | None = None


@dataclass(frozen=True, slots=True)
class SimilarPlayerResult:
    """추천 목록과 Plotly에서 바로 사용할 PCA 좌표."""

    reference: dict[str, object]
    recommendations: pd.DataFrame
    pca_coordinates: pd.DataFrame
    pca_explained_variance_ratio: tuple[float, float]


class PlayerRecommendationEngine:
    """역할별 데이터 접근, 조건 검색, 유사도 계산을 캡슐화한다."""

    def __init__(self, frames: Mapping[str, pd.DataFrame] | None = None) -> None:
        self._frames = {key: value.copy() for key, value in (frames or {}).items()}

    def _spec(self, role: str) -> RecommendationSpec:
        try:
            return RECOMMENDATION_SPECS[role]
        except KeyError as exception:
            raise ValueError(f"지원하지 않는 선수 역할입니다: {role}") from exception

    def _load(self, role: str) -> tuple[pd.DataFrame, RecommendationSpec]:
        spec = self._spec(role)
        frame = self._frames.get(role)
        if frame is None:
            frame = pd.read_csv(spec.source_path, low_memory=False)
            self._frames[role] = frame

        required = {
            "player_id",
            "player_name",
            "season",
            "team",
            spec.opportunity_column,
            *spec.similarity_features,
        }
        missing = sorted(required.difference(frame.columns))
        if missing:
            raise ValueError(f"{role} 추천 데이터에 필수 컬럼이 없습니다: {missing}")
        return frame.copy(), spec

    @staticmethod
    def _resolve_season(frame: pd.DataFrame, season: int | None) -> int:
        if frame.empty:
            raise ValueError("추천 데이터가 비어 있습니다.")
        return int(frame["season"].max()) if season is None else season

    def search_by_conditions(
        self,
        role: str,
        conditions: tuple[NumericCondition, ...] = (),
        *,
        season: int | None = None,
        team: str | None = None,
        position: str | None = None,
        sort_by: str | None = None,
        ascending: bool | None = None,
        limit: int = 50,
    ) -> pd.DataFrame:
        """동일 시즌의 충분한 표본을 가진 선수를 안전한 컬럼 집합으로 검색한다."""

        frame, spec = self._load(role)
        target_season = self._resolve_season(frame, season)
        candidates = frame.loc[
            (frame["season"] == target_season)
            & (frame[spec.opportunity_column] >= spec.minimum_opportunity)
        ].copy()

        for condition in conditions:
            if condition.column not in spec.filterable_columns:
                raise ValueError(f"조건 검색을 지원하지 않는 컬럼입니다: {condition.column}")
            if condition.minimum is not None:
                candidates = candidates.loc[candidates[condition.column] >= condition.minimum]
            if condition.maximum is not None:
                candidates = candidates.loc[candidates[condition.column] <= condition.maximum]

        if team is not None:
            candidates = candidates.loc[candidates["team"] == team]
        if position is not None:
            if role != "batting" or "position" not in candidates.columns:
                raise ValueError("포지션 조건은 타자 검색에서만 지원합니다.")
            candidates = candidates.loc[candidates["position"] == position]

        order_column = sort_by or spec.default_sort_column
        if order_column not in spec.filterable_columns:
            raise ValueError(f"정렬을 지원하지 않는 컬럼입니다: {order_column}")
        order_ascending = spec.default_sort_ascending if ascending is None else ascending
        return (
            candidates.sort_values([order_column, "player_id"], ascending=[order_ascending, True])
            .head(max(limit, 0))
            .reset_index(drop=True)
        )

    def recommend_similar(
        self,
        role: str,
        player_id: int,
        *,
        season: int | None = None,
        top_k: int = 10,
        same_position: bool = False,
    ) -> SimilarPlayerResult:
        """Cosine과 KNN 점수를 결합하고 추천 근거와 PCA 좌표를 반환한다."""

        frame, spec = self._load(role)
        player_rows = frame.loc[frame["player_id"] == player_id]
        if player_rows.empty:
            raise ValueError(f"선수를 찾을 수 없습니다: {player_id}")
        target_season = self._resolve_season(player_rows, season)
        reference_rows = player_rows.loc[player_rows["season"] == target_season]
        if reference_rows.empty:
            raise ValueError(f"해당 시즌의 선수 기록이 없습니다: {player_id}/{target_season}")
        reference = reference_rows.iloc[0]

        candidates = frame.loc[
            (frame["season"] == target_season)
            & (frame["player_id"] != player_id)
            & (frame[spec.opportunity_column] >= spec.minimum_opportunity)
        ].copy()
        if same_position:
            if role != "batting" or "position" not in frame.columns:
                raise ValueError("동일 포지션 추천은 타자에게만 적용할 수 있습니다.")
            candidates = candidates.loc[candidates["position"] == reference["position"]]
        if candidates.empty:
            raise ValueError("유사도를 계산할 추천 후보가 없습니다.")

        feature_columns = list(spec.similarity_features)
        comparison = pd.concat([reference.to_frame().T, candidates], ignore_index=True)[
            feature_columns
        ].apply(pd.to_numeric, errors="coerce")
        imputed = SimpleImputer(strategy="median").fit_transform(comparison)
        scaled = StandardScaler().fit_transform(imputed)
        reference_vector, candidate_vectors = scaled[[0]], scaled[1:]

        cosine_scores = (cosine_similarity(reference_vector, candidate_vectors)[0] + 1.0) / 2.0
        # 명시적인 단일 작업으로 제한해 배포 환경의 CPU 탐지 차이를 제거한다.
        neighbors = NearestNeighbors(metric="euclidean", n_jobs=1).fit(candidate_vectors)
        distances, indices = neighbors.kneighbors(
            reference_vector, n_neighbors=len(candidate_vectors)
        )
        knn_scores = np.zeros(len(candidates), dtype=float)
        knn_scores[indices[0]] = 1.0 / (1.0 + distances[0])

        candidates["cosine_score"] = cosine_scores
        candidates["knn_score"] = knn_scores
        candidates["similarity_score"] = (cosine_scores + knn_scores) / 2.0
        selected = candidates.nlargest(
            min(max(top_k, 1), len(candidates)), "similarity_score"
        ).copy()
        selected.insert(0, "rank", range(1, len(selected) + 1))
        selected["reasons"] = selected.apply(
            lambda row: self._build_reasons(reference, row, spec, frame), axis=1
        )

        pca = PCA(n_components=2, random_state=42)
        coordinates = pca.fit_transform(scaled)
        coordinate_frame = pd.DataFrame(
            {
                "player_id": pd.concat([reference.to_frame().T, candidates], ignore_index=True)[
                    "player_id"
                ].astype(int),
                "player_name": pd.concat([reference.to_frame().T, candidates], ignore_index=True)[
                    "player_name"
                ],
                "pca_x": coordinates[:, 0],
                "pca_y": coordinates[:, 1],
            }
        )
        visible_ids = {player_id, *selected["player_id"].astype(int).tolist()}
        coordinate_frame = coordinate_frame.loc[
            coordinate_frame["player_id"].isin(visible_ids)
        ].reset_index(drop=True)
        coordinate_frame["is_reference"] = coordinate_frame["player_id"] == player_id

        return SimilarPlayerResult(
            reference={
                "player_id": int(reference["player_id"]),
                "player_name": str(reference["player_name"]),
                "season": target_season,
                "team": str(reference["team"]),
            },
            recommendations=selected.reset_index(drop=True),
            pca_coordinates=coordinate_frame,
            pca_explained_variance_ratio=(
                float(pca.explained_variance_ratio_[0]),
                float(pca.explained_variance_ratio_[1]),
            ),
        )

    @staticmethod
    def _build_reasons(
        reference: pd.Series,
        candidate: pd.Series,
        spec: RecommendationSpec,
        population: pd.DataFrame,
    ) -> list[str]:
        """인구 표준편차 대비 차이가 작은 핵심 기록 3개를 설명한다."""

        comparable: list[tuple[float, str, float]] = []
        for column in spec.reason_features:
            reference_value = pd.to_numeric(reference[column], errors="coerce")
            candidate_value = pd.to_numeric(candidate[column], errors="coerce")
            if pd.isna(reference_value) or pd.isna(candidate_value):
                continue
            standard_deviation = pd.to_numeric(population[column], errors="coerce").std()
            denominator = float(standard_deviation) if standard_deviation > 0 else 1.0
            difference = abs(float(reference_value) - float(candidate_value))
            comparable.append((difference / denominator, column, difference))

        reasons = []
        for _, column, difference in sorted(comparable)[:3]:
            label = METRIC_LABELS.get(column, column)
            precision = (
                3
                if column
                in {
                    "batting_average",
                    "on_base_percentage",
                    "slugging_percentage",
                    "on_base_plus_slugging",
                    "earned_run_average",
                }
                else 1
            )
            reasons.append(f"{label} 차이 {difference:.{precision}f}")
        return reasons
