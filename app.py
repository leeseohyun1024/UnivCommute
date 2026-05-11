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

# --- 1번 차트: 버스 자치구 분석 ---
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
                  text_auto='.2s', title="자치구별 대학 수 대비 버스 하차량")
    st.plotly_chart(fig1, use_container_width=True)

# --- 2번 차트: 지하철 자치구 분석 ---
query_subway_gu = """
SELECT 
    u."행정구" AS 자치구, 
    COUNT(DISTINCT u."학교명") AS "대학교 수",
    AVG(s."9시00분") AS 평균지하철혼잡도
FROM "서울시대학" u
JOIN "지하철혼잡도" s ON (s."출발역" LIKE '%' || SUBSTR(u."학교명", 1, 2) || '%')
WHERE s."요일구분" = '평일'
GROUP BY u."행정구"
ORDER BY 평균지하철혼잡도 DESC
"""
df_subway_gu = run_query(query_subway_gu)

with col_right:
    st.header("2. 🚇 지하철 혼잡도")
    fig_subway_gu = px.bar(df_subway_gu, x="자치구", y="평균지하철혼잡도", 
                          color="대학교 수", color_continuous_scale="Viridis",
                          title="자치구별 지하철 혼잡도 및 대학 밀집도")
    st.plotly_chart(fig_subway_gu, use_container_width=True)

# --- [섹션 B] 1&2번 통합 인사이트 및 SQL ---
st.subheader("🔍 인사이트")
ins_col1, ins_col2 = st.columns([1.5, 1])

with ins_col1:
    st.markdown("""
    ①  **성북구/서대문구** 등 대학 밀집 지역은 버스 하차량과 지하철 혼잡도가 압도적으로 높아 병목 현상이 심각합니다.
    ② 특히 **성북구**는 대학 수와 혼잡도 모두 최상위권입니다. 가장 붐비는 호선인, **4호선의 배차 간격 조정**이 시급합니다. 
    ③ 버스 지표에서는 **서초/관악/송파**는 대학 수 대비 하차량이 많아 **주요 환승 거점**으로 파악됩니다.
    """)

with ins_col2:
    with st.expander("🛠️ 자치구 분석 SQL 확인"):
        st.write("**버스 데이터 쿼리:**")
        st.code(query1, language="sql")
        st.write("**지하철 데이터 쿼리:**")
        st.code(query_subway_gu, language="sql")

# --- [차트 3] 대학별 혼잡도 지속 비교 ---
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
df2 = run_query(query2)
df2_melted = df2.melt(id_vars=['학교명', '인근역'], 
                      value_vars=['8시00분', '8시30분', '9시00분', '9시30분', '10시00분', '10시30분'],
                      var_name='시간대', value_name='혼잡도')

col3_1, col3_2 = st.columns([2, 1])
with col3_1:
    fig2 = px.line(df2_melted, x="시간대", y="혼잡도", color="학교명", 
                    markers=True, title="대학별 등교 시간대 혼잡도 추이")
    st.plotly_chart(fig2, use_container_width=True)
with col3_2:
    with st.expander("🛠️ 대학별 데이터 SQL 확인", expanded=True):
        st.code(query2, language="sql")
    st.subheader("🔍 인사이트")
    st.write("① 8시 정점 이후 9시까지 완만해지나, 대학별로 9시 이후 반등하는 곳이 있으므로 개별 수치 확인이 필수입니다.")
    st.write("② **동국대학교**는 아침 시간대 혼잡도가 높으므로, 추세가 확실히 꺾이는 10시 이후 등교를 추천합니다.")

# --- [차트 4] 버스 등교 골든타임 분석 ---
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
    with st.expander("🛠️ 골든타임 데이터 SQL 확인", expanded=True):
        st.code(query3, language="sql")
    st.subheader("🔍 버스 통학 인사이트")
    st.write("① **피크 타임**: 08시와 18시에 하차 인원이 집중됩니다. 대학교 특성상 저녁에도 붐빌 수 있으니, 퇴근길 버스 정류장 혼잡에 주의하세요.")
    st.write("② **골든 타임**: 10시~14시 사이는 하차 인원이 가장 적어 쾌적한 이동이 가능합니다.")

st.info("👣 매학기, 통학으로 고통받는 모든 대학생을 응원합니다! 🚶‍♀️")
