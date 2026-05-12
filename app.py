import streamlit as st
import pandas as pd
import sqlite3
import plotly.express as px

# --- 1. 페이지 설정 및 제목 ---
st.set_page_config(page_title="서울시 통학러 대시보드", layout="wide")
st.title("🎓 대학생 통학 지옥 탈출 리포트")
st.markdown("통학에 지친 대학생들을 위해 서울시 대학가 주변의 교통 혼잡도를 분석합니다.")

# --- 데이터베이스 연결 함수 ---
def run_query(query):
    with sqlite3.connect("통학러.db") as conn:
        return pd.read_sql(query, conn)

# --- [섹션 A] 1번 & 2번 차트 양옆 배치 ---
st.divider()
col_left, col_right = st.columns(2)

# --- 1번 차트: 버스 혼잡도 (기준 데이터) ---
query1 = """
SELECT 
    u."행정구" AS 자치구, 
    COUNT(DISTINCT u."학교명") AS 대학교수,
    SUM(b."8시하차총승객수" + b."9시하차총승객수") AS 버스하차총합
FROM "서울시대학" u
JOIN "버스정류장" b ON u."행정구" = b."버스정류장 위치(자치구)"
GROUP BY u."행정구"
ORDER BY 버스하차총합 DESC
"""
df1 = run_query(query1)

with col_left:
    st.header("1. 🚌 버스 혼잡도")
    fig1 = px.bar(df1, x="자치구", y="버스하차총합", color="대학교수",
                  text_auto='.2s', title="자치구별 대학 수 대비 버스 하차량",
                  color_continuous_scale="Viridis")
    st.plotly_chart(fig1, use_container_width=True)

# --- 2번 차트: 지하철 혼잡도 (대학 수 고정 로직) ---
query_subway_gu = """
SELECT 
    base.자치구, 
    base.대학교수,
    AVG(sub.평균혼잡도) AS 평균지하철혼잡도
FROM (
    SELECT "행정구" AS 자치구, COUNT(DISTINCT "학교명") AS 대학교수 
    FROM "서울시대학" GROUP BY "행정구"
) base
LEFT JOIN (
    SELECT u."행정구", AVG(s."9시00분") AS 평균혼잡도
    FROM "서울시대학" u
    JOIN "지하철혼잡도" s ON (
        s."출발역" LIKE '%' || SUBSTR(u."학교명", 1, 2) || '%'
        OR (u."학교명" LIKE '국민대%' AND s."출발역" = '길음')
        OR (u."학교명" LIKE '서경대%' AND s."출발역" = '성신여대입구')
        OR (u."학교명" LIKE '숙명여자%' AND s."출발역" = '숙대입구')
        OR (u."학교명" LIKE '동국대%' AND s."출발역" = '동대입구')
    )
    WHERE s."요일구분" = '평일'
    GROUP BY u."행정구"
) sub ON base.자치구 = sub.자치구
GROUP BY base.자치구
ORDER BY 평균지하철혼잡도 DESC
"""
df_subway_gu = run_query(query_subway_gu)

with col_right:
    st.header("2. 🚇 지하철 혼잡도")
    fig_subway_gu = px.bar(df_subway_gu, x="자치구", y="평균지하철혼잡도", 
                          color="대학교수", color_continuous_scale="Viridis",
                          title="자치구별 지하철 혼잡도 및 대학 밀집도")
    st.plotly_chart(fig_subway_gu, use_container_width=True)

# --- [섹션 B] 1&2번 통합 인사이트 및 SQL ---
st.subheader("🔍 인사이트")
ins_col1, ins_col2 = st.columns([1.5, 1])

with ins_col1:
    st.markdown("""
    ① **관악구**와 **서초구**는 압도적인 버스 하차량을 기록하고 있습니다. 특히 관악구는 서울대학교라는 부지가 넓은 대학이 존재하며, 지형 특성상 캠퍼스 내부로 진입하기 위한 버스 수요가 많은 것으로 파악됩니다.
    ② 버스 하차량과 지하철 혼잡도에 상위권을 차지하고 있는 **관악구(서울대)**와 **성북구(국민대, 서경대 등)**는 고지대나 산지에 위치한 캠퍼스가 많습니다. 이는 지하철역에서 내린 뒤 반드시 버스를 타야 하는 구조를 만듭니다.
    ③ **서대문구와 마포구** 역시 대학 밀집도가 높지만 버스 하차량 순위는 관악구보다 낮습니다. 이는 해당 지역의 대학들이 상대적으로 지하철 접근성이 더 좋거나, 주거지와 학교가 더 인접해 있을 가능성을 시사합니다.
    ④ 지하철 혼잡도에서는 **성북구**가 1위를 차지하고 있으며 대학이 가장 많이 밀집된 곳인만큼 유동인구가 많다고 추청할 수 있습니다. 또한, 성북구를 지나는 4호선은 가장 유동인구가 많은 지하철이기 때문에 대학 밀집도와 더불어 이동하는 일반 시민도 많을 것으로 추정됩니다.
    """) # <-- 이 부분에 닫는 따옴표를 추가했습니다.

with ins_col2:
    with st.expander("🛠️ 자치구 분석 SQL 확인"):
        st.write("**버스 데이터 쿼리:**")
        st.code(query1, language="sql")
        st.write("**지하철 데이터 쿼리(대학수 고정형):**")
        st.code(query_subway_gu, language="sql")

# --- 차트 3 & 4 (기존 로직 유지) ---
st.divider()
st.header("3. ⏳ 대학별 혼잡도 지속 시간 비교")

query2 = """
SELECT 
    u."학교명", 
    s."출발역" AS "인근역", 
    s."8시00분", s."8시30분", s."9시00분", s."9시30분", s."10시00분", s."10시30분"
FROM "서울시대학" u 
JOIN "지하철혼잡도" s ON (
    s."출발역" LIKE '%' || SUBSTR(u."학교명", 1, 2) || '%'
    OR (u."학교명" LIKE '숙명여자%' AND s."출발역" = '숙대입구')
    OR (u."학교명" LIKE '이화여자%' AND s."출발역" = '이대')
    OR (u."학교명" LIKE '연세대%' AND s."출발역" = '신촌')
    OR (u."학교명" LIKE '중앙대%' AND s."출발역" = '흑석')
    OR (u."학교명" LIKE '경희대%' AND s."출발역" = '회기')
    OR (u."학교명" LIKE '한국외국어%' AND s."출발역" = '외대앞')
    OR (u."학교명" LIKE '건국대%' AND s."출발역" = '건대입구')
    OR (u."학교명" LIKE '동국대%' AND s."출발역" = '동대입구')
)
WHERE s."요일구분" = '평일' 
GROUP BY u."학교명"
ORDER BY u."학교명" ASC
"""
df2_res = run_query(query2)
df2_melted = df2_res.melt(id_vars=['학교명', '인근역'], 
                      value_vars=['8시00분', '8시30분', '9시00분', '9시30분', '10시00분', '10시30분'],
                      var_name='시간대', value_name='혼잡도')

col3_1, col3_2 = st.columns([2, 1])
with col3_1:
    fig_line = px.line(df2_melted, x="시간대", y="혼잡도", color="학교명", 
                    markers=True, title="대학별 등교 시간대 혼잡도 추이")
    st.plotly_chart(fig_line, use_container_width=True)
with col3_2:
    with st.expander("🛠️ SQL문", expanded=True):
        st.code(query2, language="sql")
    st.subheader("🔍 인사이트")
    st.write("① 8시 정점 이후 9시까지 완만해지나, 대학별로 등교 피크가 다르므로 실시간 확인이 필요합니다.")
    st.write("② **동국대학교**는 오전 혼잡도가 특히 높으므로, 10시 이후 등교 시 가장 쾌적합니다.")

# --- 차트 4 ---
st.divider()
st.header("4. ⏰ 버스 등교 골든타임 분석")

query3 = """
SELECT 
    '버스' AS "교통수단", 
    AVG("8시하차총승객수") AS "08시", 
    AVG("10시하차총승객수") AS "10시",
    AVG("12시하차총승객수") AS "12시", 
    AVG("14시하차총승객수") AS "14시",
    AVG("16시하차총승객수") AS "16시", 
    AVG("18시하차총승객수") AS "18시"
FROM "버스정류장" 
WHERE "버스정류장 위치(자치구)" IN (SELECT DISTINCT "행정구" FROM "서울시대학")
"""
df3 = run_query(query3)
df_bus_only = df3.melt(id_vars='교통수단', var_name='시간', value_name='하차인원')

col4_1, col4_2 = st.columns([2, 1])
with col4_1:
    fig_bus = px.area(df_bus_only, x="시간", y="하차인원", 
                     title="🚌 대학가 버스 시간대별 평균 하차 인원 추이",
                     color_discrete_sequence=['#ff7f0e'], markers=True)
    st.plotly_chart(fig_bus, use_container_width=True)
with col4_2:
    with st.expander("🛠️ SQL문", expanded=True):
        st.code(query3, language="sql")
    st.subheader("🔍 인사이트")
    st.write("① **골든 타임**: 10시~14시 사이는 하차 승객이 가장 적어 앉아서 통학할 확률이 높습니다.")

st.info("👣 매학기, 통학으로 고통받는 모든 대학생을 응원합니다! 🚶‍♀️")
