import json
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st


st.set_page_config(page_title="서울시 행정동별 출동건수", page_icon="🚑", layout="wide")

DATA_PATH = Path(__file__).parent / "data" / "dong_emergency_count.geojson"
SEOUL_CITY_HALL = {"lat": 37.5665, "lon": 126.9780}


@st.cache_data
def load_data(path: Path) -> tuple[dict, pd.DataFrame]:
    """GeoJSON과 시각화에 사용할 속성 테이블을 읽어 옵니다."""
    with path.open(encoding="utf-8") as file:
        geojson = json.load(file)

    frame = pd.DataFrame(
        [
            {
                "ADM_CD": feature["properties"]["ADM_CD"],
                "ADM_NM": feature["properties"]["ADM_NM"],
                "emergency_count": feature["properties"]["emergency_count"],
            }
            for feature in geojson["features"]
        ]
    )
    frame["ADM_CD"] = frame["ADM_CD"].astype(str)
    frame["ADM_NM"] = frame["ADM_NM"].astype(str)
    frame["emergency_count"] = pd.to_numeric(frame["emergency_count"])
    return geojson, frame


def create_map(geojson: dict, frame: pd.DataFrame):
    low, high = frame["emergency_count"].min(), frame["emergency_count"].max()
    # 출동건수가 모두 같은 경우에도 색상 스케일이 동작하도록 범위를 보정합니다.
    if low == high:
        high = low + 1

    figure = px.choropleth_map(
        frame,
        geojson=geojson,
        locations="ADM_CD",
        featureidkey="properties.ADM_CD",
        color="emergency_count",
        color_continuous_scale=[(0, "#ffffff"), (1, "#e31a1c")],
        range_color=(low, high),
        custom_data=["ADM_NM", "ADM_CD"],
        center=SEOUL_CITY_HALL,
        zoom=10.5,
        map_style="carto-positron",
        opacity=0.78,
        labels={"emergency_count": "출동건수"},
    )
    figure.update_traces(
        marker_line_color="#777777",
        marker_line_width=0.45,
        hovertemplate=(
            "<b>%{customdata[0]}</b><br>"
            "행정동 코드: %{customdata[1]}<br>"
            "출동건수: %{z:,}건<extra></extra>"
        ),
    )
    figure.update_layout(
        margin={"l": 0, "r": 0, "t": 0, "b": 0},
        coloraxis_colorbar={"title": "출동건수", "tickformat": ","},
    )
    return figure


st.title("서울시 행정동별 출동건수")
st.caption("흰색에 가까울수록 적고, 빨간색에 가까울수록 출동건수가 많습니다.")

if not DATA_PATH.exists():
    st.error("데이터 파일을 찾을 수 없습니다: data/dong_emergency_count.geojson")
    st.stop()

geojson, data = load_data(DATA_PATH)
show_mok_dong_only = st.toggle("목x동만 보기", value=False)

display_data = data
if show_mok_dong_only:
    display_data = data[
        data["ADM_NM"].str.match(r"^목.+동$", na=False)
    ].copy()

if display_data.empty:
    st.warning("현재 GeoJSON에는 ‘목x동’에 해당하는 행정동이 없습니다.")
    st.stop()

st.plotly_chart(create_map(geojson, display_data), use_container_width=True)
st.caption(f"표시 행정동 수: {len(display_data):,}개")
