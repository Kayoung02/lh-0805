import json
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st


st.set_page_config(
    page_title="서울시 행정동 출동 대시보드",
    page_icon="🚑",
    layout="wide",
)

DATA_PATH = Path(__file__).parent / "data" / "dong_emergency_count.geojson"
SEOUL_CITY_HALL = {"lat": 37.5665, "lon": 126.9780}
RISK_ORDER = ["매우 낮음", "낮음", "보통", "높음", "매우 높음"]
RISK_COLORS = {
    "매우 낮음": "#fff5f0",
    "낮음": "#fcbba1",
    "보통": "#fc9272",
    "높음": "#ef3b2c",
    "매우 높음": "#99000d",
}


@st.cache_data
def load_data(path: Path) -> tuple[dict, pd.DataFrame]:
    with path.open(encoding="utf-8") as file:
        geojson = json.load(file)

    rows = []
    for feature in geojson["features"]:
        properties = feature["properties"]
        rows.append(
            {
                "BASE_DATE": str(properties.get("BASE_DATE", "")),
                "ADM_CD": str(properties["ADM_CD"]),
                "ADM_NM": str(properties["ADM_NM"]),
                "emergency_count": properties["emergency_count"],
            }
        )

    frame = pd.DataFrame(rows)
    frame["emergency_count"] = pd.to_numeric(frame["emergency_count"])
    frame["top_percent"] = (
        frame["emergency_count"]
        .rank(method="average", ascending=False, pct=True)
        .mul(100)
        .round(1)
    )
    frame["risk_level"] = pd.qcut(
        frame["emergency_count"].rank(method="first"),
        q=5,
        labels=RISK_ORDER,
    )
    return geojson, frame


def create_continuous_map(geojson: dict, frame: pd.DataFrame):
    low = frame["emergency_count"].min()
    high = frame["emergency_count"].max()
    if low == high:
        high = low + 1

    figure = px.choropleth_mapbox(
        frame,
        geojson=geojson,
        locations="ADM_CD",
        featureidkey="properties.ADM_CD",
        color="emergency_count",
        color_continuous_scale=[(0, "#ffffff"), (1, "#d7191c")],
        range_color=(low, high),
        custom_data=["ADM_NM", "ADM_CD", "risk_level", "top_percent"],
        center=SEOUL_CITY_HALL,
        zoom=10.4,
        mapbox_style="carto-positron",
        opacity=0.8,
    )
    figure.update_traces(
        marker_line_color="#777777",
        marker_line_width=0.45,
        hovertemplate=(
            "<b>%{customdata[0]}</b><br>"
            "행정동 코드: %{customdata[1]}<br>"
            "출동건수: %{z:,}건<br>"
            "전체 대비: 상위 %{customdata[3]:.1f}%<br>"
            "위험등급: %{customdata[2]}<extra></extra>"
        ),
    )
    figure.update_layout(
        margin={"l": 0, "r": 0, "t": 0, "b": 0},
        coloraxis_colorbar={"title": "출동건수", "tickformat": ","},
        height=650,
    )
    return figure


def create_risk_map(geojson: dict, frame: pd.DataFrame):
    figure = px.choropleth_mapbox(
        frame,
        geojson=geojson,
        locations="ADM_CD",
        featureidkey="properties.ADM_CD",
        color="risk_level",
        color_discrete_map=RISK_COLORS,
        category_orders={"risk_level": RISK_ORDER},
        custom_data=["ADM_NM", "ADM_CD", "emergency_count", "top_percent"],
        center=SEOUL_CITY_HALL,
        zoom=10.4,
        mapbox_style="carto-positron",
        opacity=0.82,
        labels={"risk_level": "위험등급"},
    )
    figure.update_traces(
        marker_line_color="#777777",
        marker_line_width=0.45,
        hovertemplate=(
            "<b>%{customdata[0]}</b><br>"
            "행정동 코드: %{customdata[1]}<br>"
            "출동건수: %{customdata[2]:,}건<br>"
            "전체 대비: 상위 %{customdata[3]:.1f}%<extra></extra>"
        ),
    )
    figure.update_layout(
        margin={"l": 0, "r": 0, "t": 0, "b": 0},
        legend={"title": "출동 위험등급", "orientation": "h", "y": 0.01},
        height=650,
    )
    return figure


def create_ranking_chart(frame: pd.DataFrame, count: int):
    ranking = frame.nlargest(count, "emergency_count").sort_values("emergency_count")
    figure = px.bar(
        ranking,
        x="emergency_count",
        y="ADM_NM",
        orientation="h",
        color="emergency_count",
        color_continuous_scale=["#fcae91", "#99000d"],
        custom_data=["ADM_CD", "top_percent"],
        text="emergency_count",
        labels={"ADM_NM": "행정동", "emergency_count": "출동건수"},
    )
    figure.update_traces(
        texttemplate="%{text:,}건",
        textposition="outside",
        hovertemplate=(
            "<b>%{y}</b><br>행정동 코드: %{customdata[0]}<br>"
            "출동건수: %{x:,}건<br>전체 대비: 상위 %{customdata[1]:.1f}%"
            "<extra></extra>"
        ),
    )
    figure.update_layout(
        coloraxis_showscale=False,
        margin={"l": 10, "r": 80, "t": 10, "b": 10},
        height=max(420, count * 34),
        yaxis_title=None,
    )
    return figure


st.title("🚑 서울시 행정동별 출동건수")
st.caption("지역별 출동 집중도를 지도와 순위로 함께 살펴보세요.")

if not DATA_PATH.exists():
    st.error("데이터 파일을 찾을 수 없습니다: data/dong_emergency_count.geojson")
    st.stop()

geojson, data = load_data(DATA_PATH)

total = int(data["emergency_count"].sum())
average = data["emergency_count"].mean()
median = data["emergency_count"].median()
top_row = data.loc[data["emergency_count"].idxmax()]

metric_1, metric_2, metric_3, metric_4 = st.columns(4)
metric_1.metric("전체 출동건수", f"{total:,}건")
metric_2.metric("행정동 평균", f"{average:,.1f}건")
metric_3.metric("행정동 중앙값", f"{median:,.1f}건")
metric_4.metric(
    f"최다 출동 · {top_row['ADM_NM']}",
    f"{int(top_row['emergency_count']):,}건",
)

st.divider()

map_tab, ranking_tab = st.tabs(["🗺️ 공간 집중도", "📊 출동 상위 지역"])

with map_tab:
    view_mode = st.radio(
        "지도 표현 방식",
        ["연속 색상", "5단계 위험등급"],
        horizontal=True,
        help="연속 색상은 건수의 세밀한 차이를, 위험등급은 지역 간 단계 차이를 보여줍니다.",
    )
    if view_mode == "연속 색상":
        map_figure = create_continuous_map(geojson, data)
    else:
        map_figure = create_risk_map(geojson, data)
    st.plotly_chart(map_figure, use_container_width=True, config={"displayModeBar": False})
    st.caption("지도는 처음 열릴 때 서울시청을 중심으로 표시됩니다. 행정동 위에 마우스를 올리면 상세 정보를 볼 수 있습니다.")

with ranking_tab:
    top_n = st.slider("표시할 상위 행정동 수", min_value=5, max_value=30, value=15, step=5)
    share = data.nlargest(top_n, "emergency_count")["emergency_count"].sum() / total
    st.info(f"상위 {top_n}개 행정동이 전체 출동의 {share:.1%}를 차지합니다.")
    st.plotly_chart(
        create_ranking_chart(data, top_n),
        use_container_width=True,
        config={"displayModeBar": False},
    )

base_date = data["BASE_DATE"].dropna().max()
if len(base_date) == 8:
    base_date = f"{base_date[:4]}-{base_date[4:6]}-{base_date[6:]}"
st.caption(f"데이터 기준일: {base_date} · 행정동 {len(data):,}개")
