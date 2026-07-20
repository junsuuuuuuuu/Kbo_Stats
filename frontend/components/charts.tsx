"use client";

import dynamic from "next/dynamic";
import type { Data, Layout } from "plotly.js";

import type { GrowthPoint, SimilarResponse } from "@/types/api";

const Plot = dynamic(async () => {
  const [{ default: createPlotlyComponent }, { default: Plotly }, { default: scatter }, { default: scatterpolar }] = await Promise.all([
    import("react-plotly.js/factory"),
    import("plotly.js/lib/core"),
    import("plotly.js/lib/scatter"),
    import("plotly.js/lib/scatterpolar"),
  ]);
  Plotly.register([scatter, scatterpolar]);
  return createPlotlyComponent(Plotly);
}, { ssr: false });

const baseLayout: Partial<Layout> = {
  paper_bgcolor: "transparent",
  plot_bgcolor: "transparent",
  font: { color: "#84919d", family: "IBM Plex Sans KR" },
  margin: { l: 54, r: 20, t: 24, b: 48 },
  legend: { orientation: "h", y: 1.12 },
  hovermode: "x unified",
};

export function LineChart({ traces, height = 380 }: { traces: Data[]; height?: number }) {
  const hasSecondaryAxis = traces.some((trace) => "yaxis" in trace && trace.yaxis === "y2");
  return <Plot data={traces} layout={{ ...baseLayout, height, yaxis2: hasSecondaryAxis ? { overlaying: "y", side: "right", showgrid: false } : undefined }} config={{ responsive: true, displaylogo: false }} useResizeHandler className="chart" />;
}

export function GrowthChart({ points }: { points: GrowthPoint[] }) {
  const metrics = [...new Set(points.map((point) => point.metric))];
  const traces: Data[] = metrics.map((metric) => {
    const rows = points.filter((point) => point.metric === metric);
    const usesCountAxis = ["home_runs", "strikeouts", "walks_allowed"].includes(metric);
    return { type: "scatter", mode: "lines+markers", name: rows[0]?.metric_label ?? metric, x: rows.map((row) => row.season), y: rows.map((row) => row.value), yaxis: usesCountAxis ? "y2" : "y", connectgaps: false, line: { width: 3 }, marker: { size: rows.map((row) => row.event === "breakout" || row.event === "decline" ? 11 : 6), color: rows.map((row) => row.event === "breakout" ? "#00a87b" : row.event === "decline" ? "#ff4d2e" : "#006eff") }, text: rows.map((row) => row.event), hovertemplate: "%{x} · %{y}<br>%{text}<extra></extra>" };
  });
  return <LineChart traces={traces} />;
}

export function PcaChart({ data }: { data: SimilarResponse }) {
  const trace: Data = { type: "scatter", mode: "text+markers", x: data.pca_coordinates.map((row) => row.pca_x), y: data.pca_coordinates.map((row) => row.pca_y), text: data.pca_coordinates.map((row) => row.player_name), textposition: "top center", marker: { size: data.pca_coordinates.map((row) => row.is_reference ? 18 : 11), color: data.pca_coordinates.map((row) => row.is_reference ? "#ff4d2e" : "#006eff"), opacity: .86 }, hovertemplate: "%{text}<extra></extra>" };
  return <Plot data={[trace]} layout={{ ...baseLayout, height: 400, xaxis: { title: { text: "PCA 1" }, zeroline: false }, yaxis: { title: { text: "PCA 2" }, zeroline: false }, showlegend: false }} config={{ responsive: true, displaylogo: false }} useResizeHandler className="chart" />;
}

export function RadarChart({ labels, players }: { labels: string[]; players: Array<{ name: string; values: number[] }> }) {
  const traces: Data[] = players.map((player) => ({ type: "scatterpolar", mode: "lines", fill: "toself", name: player.name, theta: labels, r: player.values, opacity: .68 }));
  return <Plot data={traces} layout={{ ...baseLayout, height: 430, polar: { bgcolor: "transparent", radialaxis: { visible: true, range: [0, 100] } } }} config={{ responsive: true, displaylogo: false }} useResizeHandler className="chart" />;
}
