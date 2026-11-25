
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from io import StringIO
import re

st.set_page_config(
    page_title="소아 호흡기 질환과 기온 분석",
    page_icon="🌡️",
    layout="wide"
)

st.title("🌡️ 계절과 기온 변화에 따른 소아 호흡기 질환 분석")
st.write("계절과 기온 변화에 따라 소아 감기 환자 수는 정말 달라질까?")

st.info(
    "질병 데이터는 J00(급성 비인두염)을 대상으로 합니다. "
    "소아는 5세 미만, 5~9세, 10~14세로 구분합니다."
)

# -------------------------
# 1. 데이터 업로드
# -------------------------

st.sidebar.header("데이터 파일 업로드")

disease_file = st.sidebar.file_uploader(
    "질병 데이터 (.xlsx)", type=["xlsx"]
)

weather_file = st.sidebar.file_uploader(
    "기온 데이터 (.xls, .xlsx, .txt)", 
    type=["xls", "xlsx", "txt"]
)

if disease_file is None or weather_file is None:
    st.warning("왼쪽에서 질병 데이터와 기온 데이터를 업로드해 주세요.")
    st.stop()


# -------------------------
# 2. 질병 데이터 읽기
# -------------------------

try:
    raw = pd.read_excel(disease_file, header=None)

    if raw.shape[0] < 5:
        st.error("질병 데이터의 행 구성을 확인해 주세요.")
        st.stop()

    month_columns = []

    for col in range(3, raw.shape[1], 5):
        month_label = None

        for r in range(min(3, raw.shape[0])):
            value = raw.iat[r, col]

            if pd.notna(value):
                match = re.search(
                    r"(\d{4})년\s*(\d{1,2})월",
                    str(value)
                )

                if match:
                    month_label = (
                        f"{int(match.group(1)):04d}-"
                        f"{int(match.group(2)):02d}"
                    )
                    break

        if month_label:
            month_columns.append((col, month_label))

    if not month_columns:
        st.error("질병 데이터에서 월별 항목을 찾지 못했습니다.")
        st.stop()

    data = raw.iloc[4:].copy()
    data[0] = data[0].astype(str).str.strip()
    data[1] = data[1].astype(str).str.strip()
    data[2] = data[2].astype(str).str.strip()

    age_names = {
        "5세미만": "5세 미만",
        "5_9세": "5~9세",
        "10_14세": "10~14세"
    }

    records = []

    for col, month in month_columns:

        for age_code, age_name in age_names.items():

            subset = data[
                (data[0] == "J00") &
                (data[2] == age_code) &
                (data[1].isin(["남", "여"]))
            ]

            values = pd.to_numeric(
                subset[col], errors="coerce"
            ).dropna()

            count = values.sum() if len(values) > 0 else np.nan

            records.append({
                "월": month,
                "연령대": age_name,
                "환자수": count
            })

    disease = pd.DataFrame(records)

    disease["월"] = pd.to_datetime(
        disease["월"], format="%Y-%m"
    )

    disease["환자수"] = pd.to_numeric(
        disease["환자수"], errors="coerce"
    )

except Exception as e:
    st.error(f"질병 데이터 오류: {e}")
    st.stop()


# -------------------------
# 3. 기온 데이터 읽기
# -------------------------

try:

    if weather_file.name.endswith(".xlsx"):
        weather_raw = pd.read_excel(weather_file)

    elif weather_file.name.endswith(".xls"):
        weather_raw = pd.read_excel(weather_file)

    else:
        content = weather_file.getvalue().decode(
            "cp949", errors="replace"
        )

        lines = content.splitlines()

        header_idx = None

        for i, line in enumerate(lines):
            if "일시" in line and "평균기온" in line:
                header_idx = i
                break

        if header_idx is None:
            st.error("기온 데이터의 제목 행을 찾지 못했습니다.")
            st.stop()

        weather_raw = pd.read_csv(
            StringIO("\n".join(lines[header_idx:])),
            sep="\t"
        )

    weather_raw.columns = (
        weather_raw.columns.astype(str).str.strip()
    )

    if "일시" not in weather_raw.columns:
        st.error("기온 데이터에 '일시' 열이 없습니다.")
        st.stop()

    temp_col = next(
        (
            c for c in weather_raw.columns
            if "평균기온" in c
        ),
        None
    )

    if temp_col is None:
        st.error("기온 데이터에 평균기온 열이 없습니다.")
        st.stop()

    weather = weather_raw[["일시", temp_col]].copy()

    weather["월"] = pd.to_datetime(
        weather["일시"].astype(str).str.strip(),
        format="%Y-%m",
        errors="coerce"
    )

    weather["평균기온"] = pd.to_numeric(
        weather[temp_col], errors="coerce"
    )

    weather = weather[
        ["월", "평균기온"]
    ].dropna(subset=["월"])

except Exception as e:
    st.error(f"기온 데이터 오류: {e}")
    st.stop()


# -------------------------
# 4. 데이터 합치기
# -------------------------

monthly = (
    disease.groupby("월", as_index=False)
    .agg(소아환자수=("환자수", "sum"))
)

merged = pd.merge(
    monthly,
    weather,
    on="월",
    how="inner"
)

merged = merged.sort_values("월").reset_index(drop=True)

merged["연도"] = merged["월"].dt.year
merged["월번호"] = merged["월"].dt.month
merged["월표시"] = merged["월"].dt.strftime("%Y-%m")

merged["계절"] = merged["월번호"].map({
    3: "봄", 4: "봄", 5: "봄",
    6: "여름", 7: "여름", 8: "여름",
    9: "가을", 10: "가을", 11: "가을",
    12: "겨울", 1: "겨울", 2: "겨울"
})

if merged.empty:
    st.error("두 자료에서 공통으로 확인되는 월이 없습니다.")
    st.stop()


# -------------------------
# 5. 결측치와 이상치 확인
# -------------------------

before_rows = len(merged)

missing_count = merged[
    ["소아환자수", "평균기온"]
].isna().sum().sum()

clean = merged.dropna(
    subset=["소아환자수", "평균기온"]
).copy()

after_rows = len(clean)

if clean.empty:
    st.error("분석할 수 있는 데이터가 없습니다.")
    st.stop()

# Q1과 Q3를 먼저 계산한 다음 IQR 계산
q1 = clean["소아환자수"].quantile(0.25)
q3 = clean["소아환자수"].quantile(0.75)

iqr = q3 - q1

lower = q1 - 1.5 * iqr
upper = q3 + 1.5 * iqr

clean["이상치"] = (
    (clean["소아환자수"] < lower) |
    (clean["소아환자수"] > upper)
)

outlier_count = int(clean["이상치"].sum())


# -------------------------
# 6. 데이터 개요
# -------------------------

st.header("📊 데이터 개요")

c1, c2, c3, c4 = st.columns(4)

c1.metric("전체 데이터 행 수", f"{before_rows}개")
c2.metric("분석 후 행 수", f"{after_rows}개")
c3.metric("결측치", f"{missing_count}개")
c4.metric("이상치", f"{outlier_count}개")

with st.expander("전처리 과정 확인"):

    st.write("결측치 처리: 기온 또는 환자 수가 없는 월 제외")

    st.write(
        f"처리 전 행 수: {before_rows}개"
    )

    st.write(
        f"처리 후 행 수: {after_rows}개"
    )

    st.write(
        f"IQR 기준 이상치: {outlier_count}개"
    )

    st.write(
        "이상치는 계절적 유행일 가능성이 있으므로 "
        "임의로 삭제하지 않고 표시만 했습니다."
    )

    st.dataframe(clean)


# -------------------------
# 7. 그래프 1
# 월별 기온과 환자 수
# -------------------------

st.divider()

st.header("📈 그래프 1. 월별 기온과 소아 환자 수")

fig1 = go.Figure()

fig1.add_trace(
    go.Bar(
        x=clean["월표시"],
        y=clean["소아환자수"],
        name="소아 환자 수",
        yaxis="y"
    )
)

fig1.add_trace(
    go.Scatter(
        x=clean["월표시"],
        y=clean["평균기온"],
        name="평균기온",
        yaxis="y2",
        mode="lines+markers"
    )
)

fig1.update_layout(
    title="월별 소아 환자 수와 평균기온 변화",
    xaxis_title="연월",
    yaxis=dict(title="환자 수(명)"),
    yaxis2=dict(
        title="평균기온(℃)",
        overlaying="y",
        side="right"
    ),
    hovermode="x unified"
)

st.plotly_chart(fig1, use_container_width=True)


# -------------------------
# 8. 그래프 2
# 산점도와 상관관계
# -------------------------

st.header("📉 그래프 2. 기온과 환자 수의 관계")

corr = clean["평균기온"].corr(
    clean["소아환자수"]
)

fig2 = px.scatter(
    clean,
    x="평균기온",
    y="소아환자수",
    text="월표시",
    title="평균기온과 소아 환자 수의 관계",
    labels={
        "평균기온": "평균기온(℃)",
        "소아환자수": "환자 수(명)"
    }
)

if clean["평균기온"].nunique() > 1:

    slope, intercept = np.polyfit(
        clean["평균기온"],
        clean["소아환자수"],
        1
    )

    x_line = np.linspace(
        clean["평균기온"].min(),
        clean["평균기온"].max(),
        100
    )

    fig2.add_trace(
        go.Scatter(
            x=x_line,
            y=slope * x_line + intercept,
            mode="lines",
            name="회귀선"
        )
    )

st.plotly_chart(fig2, use_container_width=True)

st.metric(
    "기온과 환자 수의 상관계수",
    f"{corr:.3f}" if pd.notna(corr) else "계산 불가"
)


# -------------------------
# 9. 그래프 3
# 계절별 환자 수
# -------------------------

st.header("🍂 그래프 3. 계절별 소아 환자 수")

season = (
    clean.groupby("계절", observed=True)
    .agg(
        평균환자수=("소아환자수", "mean"),
        평균기온=("평균기온", "mean"),
        월수=("월표시", "count")
    )
    .reset_index()
)

season_order = ["봄", "여름", "가을", "겨울"]

season["계절"] = pd.Categorical(
    season["계절"],
    categories=season_order,
    ordered=True
)

season = season.sort_values("계절")

fig3 = px.bar(
    season,
    x="계절",
    y="평균환자수",
    text_auto=".0f",
    title="계절별 월평균 소아 환자 수",
    labels={
        "계절": "계절",
        "평균환자수": "평균 환자 수(명)"
    }
)

st.plotly_chart(fig3, use_container_width=True)

st.dataframe(season, use_container_width=True)


# -------------------------
# 10. 그래프 4
# 연령대별 환자 수
# -------------------------

st.header("👧 그래프 4. 연령대별 환자 수")

age_data = disease.merge(
    weather,
    on="월",
    how="inner"
)

fig4 = px.line(
    age_data,
    x="월",
    y="환자수",
    color="연령대",
    markers=True,
    title="연령대별 월별 소아 환자 수",
    labels={
        "월": "연월",
        "환자수": "환자 수(명)",
        "연령대": "연령대"
    }
)

st.plotly_chart(fig4, use_container_width=True)


# -------------------------
# 11. 분석 결과
# -------------------------

st.divider()

st.header("🔎 분석 결과 요약")

highest = clean.loc[
    clean["소아환자수"].idxmax()
]

lowest = clean.loc[
    clean["소아환자수"].idxmin()
]

warmest = clean.loc[
    clean["평균기온"].idxmax()
]

coldest = clean.loc[
    clean["평균기온"].idxmin()
]

col1, col2 = st.columns(2)

with col1:

    st.write("**환자가 가장 많았던 달**")

    st.subheader(
        f"{highest['월표시']}"
    )

    st.write(
        f"{highest['소아환자수']:,.0f}명"
    )

    st.write("**환자가 가장 적었던 달**")

    st.subheader(
        f"{lowest['월표시']}"
    )

    st.write(
        f"{lowest['소아환자수']:,.0f}명"
    )

with col2:

    st.write("**가장 따뜻했던 달**")

    st.subheader(
        f"{warmest['월표시']}"
    )

    st.write(
        f"{warmest['평균기온']:.1f}℃"
    )

    st.write("**가장 추웠던 달**")

    st.subheader(
        f"{coldest['월표시']}"
    )

    st.write(
        f"{coldest['평균기온']:.1f}℃"
    )


# -------------------------
# 12. 한계와 주의점
# -------------------------

st.warning(
    "주의: 상관관계가 있다고 해서 기온이 환자 수 변화의 "
    "직접적인 원인이라고 단정할 수는 없습니다. "
    "바이러스 유행, 인구 규모, 의료 이용 변화 등 "
    "다른 요인도 영향을 줄 수 있습니다. "
    "또한 분석 기간과 지역이 제한되어 있어 "
    "모든 지역과 연도에 일반화하기 어렵습니다."
)

st.header("📋 최종 분석 데이터")

st.dataframe(
    clean[
        [
            "월표시",
            "소아환자수",
            "평균기온",
            "계절",
            "이상치"
        ]
    ],
    use_container_width=True
)

csv = clean.to_csv(
    index=False
).encode("utf-8-sig")

st.download_button(
    "분석 데이터 CSV 다운로드",
    data=csv,
    file_name="소아호흡기질환_기온분석.csv",
    mime="text/csv"
)
