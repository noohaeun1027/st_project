iqr = q3 - q1
lower = q1 - 1.5 * iqr
upper = q3 + 1.5 * iqr
clean["이상치여부"] = (clean["소아환자수"] < lower) | (clean["소아환자수"] > upper)
outlier_count = int(clean["이상치여부"].sum())

st.subheader("📌 데이터 개요")
c1, c2, c3, c4 = st.columns(4)
c1.metric("질병 데이터 행 수", f"{len(disease):,}")
c2.metric("분석 가능한 공통 월", f"{len(clean):,}개월")
c3.metric("결측치 수", f"{missing_before:,}개")
c4.metric("IQR 기준 이상치", f"{outlier_count:,}개")

with st.expander("데이터 감식 및 전처리 내용 보기"):
    st.write("**질병 데이터 열:** 월, 연령대, 소아환자수")
    st.write("**기온 데이터 열:** 월, 평균기온")
    st.write("**자료형:** 월은 날짜형, 평균기온과 환자 수는 숫자형으로 변환했습니다.")
    st.write(f"**병합 전 질병 월별 자료:** {len(pediatric)}개월")
    st.write(f"**병합 후 기온·질병 공통 자료:** {len(merged)}개월")
    st.write(f"**결측치 제거 후 분석 자료:** {len(clean)}개월")
    st.write(f"**IQR 기준 이상치:** {outlier_count}개월")
    st.write(
        "전처리 기준: 기온과 환자 수가 모두 있는 월만 분석했습니다. "
        "이상치는 사분위수 범위(IQR)의 1.5배를 벗어난 값으로 표시했으며, "
        "실제 계절적 유행일 수도 있으므로 임의로 삭제하지 않았습니다."
    )
    st.dataframe(clean[["월표시", "소아환자수", "평균기온", "이상치여부"]], use_container_width=True)

if len(clean) < 2:
    st.error("기온과 질병 자료에서 공통으로 확인되는 월이 2개월 미만입니다.")
    st.stop()

st.divider()
st.subheader("📈 그래프 1. 월별 평균기온과 소아 환자 수 변화")
fig1 = go.Figure()
fig1.add_trace(go.Bar(
    x=clean["월표시"], y=clean["소아환자수"],
    name="소아 환자 수", yaxis="y1", opacity=0.65
))
fig1.add_trace(go.Scatter(
    x=clean["월표시"], y=clean["평균기온"],
    name="월평균기온(℃)", yaxis="y2", mode="lines+markers", line=dict(width=3)
))
fig1.update_layout(
    title="월별 소아 급성 비인두염 환자 수와 서울 평균기온",
    xaxis_title="연월", yaxis=dict(title="환자 수(명)"),
    yaxis2=dict(title="평균기온(℃)", overlaying="y", side="right"),
    legend_title="항목", hovermode="x unified"
)
st.plotly_chart(fig1, use_container_width=True)

st.subheader("📉 그래프 2. 평균기온과 소아 환자 수의 관계")
corr = clean["평균기온"].corr(clean["소아환자수"])
fig2 = px.scatter(
    clean, x="평균기온", y="소아환자수", text="월표시",
    title="월평균기온과 소아 환자 수의 산점도",
    labels={"평균기온": "월평균기온(℃)", "소아환자수": "소아 환자 수(명)"}
)
fig2.update_traces(textposition="top center")
if clean["평균기온"].nunique() > 1:
    xline = np.linspace(clean["평균기온"].min(), clean["평균기온"].max(), 100)
    slope, intercept = np.polyfit(clean["평균기온"], clean["소아환자수"], 1)
    fig2.add_trace(go.Scatter(
        x=xline, y=slope*xline+intercept, mode="lines",
        name="선형 추세선"
    ))
st.plotly_chart(fig2, use_container_width=True)
st.metric("기온과 환자 수의 상관계수", f"{corr:.3f}" if pd.notna(corr) else "계산 불가")
st.caption("상관계수는 두 값이 함께 변하는 정도를 나타내며, 기온이 환자 수 변화의 원인임을 증명하지는 않습니다.")

st.subheader("🍂 그래프 3. 계절별 평균 소아 환자 수")
season_order = ["봄", "여름", "가을", "겨울"]
season = (
    clean.groupby("계절", as_index=False)
    .agg(평균환자수=("소아환자수", "mean"), 평균기온=("평균기온", "mean"), 월수=("월표시", "count"))
)
season["계절"] = pd.Categorical(season["계절"], categories=season_order, ordered=True)
season = season.sort_values("계절")
fig3 = px.bar(
    season, x="계절", y="평균환자수", text_auto=".0f",
    title="계절별 월평균 소아 환자 수",
    labels={"계절": "계절", "평균환자수": "월평균 환자 수(명)"}
)
st.plotly_chart(fig3, use_container_width=True)
st.dataframe(season, use_container_width=True, hide_index=True)

st.subheader("👧 그래프 4. 연령대별 월별 환자 수")
age_month = disease.merge(weather, on="월", how="inner")
fig4 = px.line(
    age_month, x="월", y="소아환자수", color="연령대", markers=True,
    title="연령대별 월별 J00 환자 수",
    labels={"월": "연월", "소아환자수": "환자 수(명)", "연령대": "연령대"}
)
st.plotly_chart(fig4, use_container_width=True)

if total is not None:
    st.subheader("➕ 참고: 전체 연령 환자 수와 소아 환자 수")
    compare = clean.merge(total, on="월", how="inner")
    if len(compare):
        compare["소아환자 비율(%)"] = compare["소아환자수"] / compare["전체환자수"] * 100
        fig5 = px.line(
            compare, x="월", y="소아환자 비율(%)", markers=True,
            title="전체 J00 환자 중 소아 환자 비율",
            labels={"월": "연월", "소아환자 비율(%)": "소아 환자 비율(%)"}
        )
        st.plotly_chart(fig5, use_container_width=True)

st.divider()
st.subheader("🔎 분석 결과 요약")
highest = clean.loc[clean["소아환자수"].idxmax()]
lowest = clean.loc[clean["소아환자수"].idxmin()]
warmest = clean.loc[clean["평균기온"].idxmax()]
coldest = clean.loc[clean["평균기온"].idxmin()]
r1, r2 = st.columns(2)
with r1:
    st.write(f"**환자 수가 가장 많았던 달:** {highest['월표시']} · {highest['소아환자수']:,.0f}명")
    st.write(f"**환자 수가 가장 적었던 달:** {lowest['월표시']} · {lowest['소아환자수']:,.0f}명")
with r2:
    st.write(f"**가장 따뜻했던 달:** {warmest['월표시']} · {warmest['평균기온']:.1f}℃")
    st.write(f"**가장 추웠던 달:** {coldest['월표시']} · {coldest['평균기온']:.1f}℃")

st.warning(
    "해석할 때 주의할 점: 이 자료는 월별 환자 수이므로 실제 감염 위험이나 개인별 발병률과 같지 않습니다. "
    "인구 규모, 유행하는 바이러스, 마스크 착용, 의료 이용 변화 등 다른 요인의 영향도 받을 수 있습니다. "
    "또한 기온 자료와 질병 자료의 공통 기간에 한해 분석했으므로 결과를 모든 지역·연도에 일반화하기 어렵습니다."
)

st.subheader("📋 분석에 사용한 최종 데이터")
