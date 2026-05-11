import streamlit as st
import pandas as pd
import sqlite3
import plotly.express as px

# --- 1. 페이지 설정 및 제목 ---
st.set_page_config(page_title="서울시 통학러 대시보드", layout="wide")
st.title("🎓 대학생 통학 지옥 탈출 리포트")
st.markdown("서울시 대학 주변의 버스와 지하철 혼잡도를 분석하여 최적의 등교 시간을 찾아봅니다.")

# --- 2. 데이터베이스 연결 함수 ---
def run_query(query):
    # 데이터베이스에 연결하고 쿼리를 실행한 뒤 결과를 표(DataFrame)로 돌려줍니다.
    with sqlite3.connect("통학러.db") as conn:
        return pd.read_sql(query, conn)

# --- [차트 1] 대학 환승 지옥 리포트 ---
st.header("1. 🚌 자치구별 환승 지옥 리포트")

# SQL: 자치구별 버스 하차 총합과 지하철 전체 평균 혼잡도 비교
query1 = """
SELECT 
    "버스정류장 위치(자치구)" AS 자치구, 
    SUM("08시하차총승객수" + "09시하차총승객수") AS 버스하차총합,
    (SELECT AVG("9시00분") FROM "지하철혼잡도" WHERE "요일구분" = '평일') AS 평균지하철혼잡도
FROM "버스정류장"
GROUP BY 자치구
"""
df1 = run_query(query1)

col1, col2 = st.columns([2, 1])
with col1:
    # 시각화: 산점도
    fig1 = px.scatter(df1, x="버스하차총합", y="평균지하철혼잡도", text="자치구",
                     size="버스하차총합", color="자치구",
                     title="자치구별 버스 하차 승객 vs 지하철 혼잡도")
    st.plotly_chart(fig1, use_container_width=True)

with col2:
    st.subheader("🔍 인사이트")
    st.write("① (여기에 인사이트를 입력하세요)")
    st.write("② (여기에 인사이트를 입력하세요)")
    with st.expander("사용한 SQL 보기"):
        st.code(query1, language='sql')


# --- [차트 2] 대학별 혼잡도 지속 비교 ---
st.header("2. ⏳ 대학별 혼잡도 지속 시간 비교")

# SQL: 사용자가 제공한 쿼리 (대학별 인근역의 8시~9시30분 혼잡도 변화)
query2 = """
SELECT 
    u."학교명", 
    s."출발역" AS "인근역", 
    s."8시00분", s."8시30분", s."9시00분", s."9시30분"
FROM "서울시대학" u 
JOIN "지하철혼잡도" s ON (s."출발역" LIKE '%' || SUBSTR(u."학교명", 1, 3) || '%')
WHERE s."요일구분" = '평일' 
AND (s."8시30분" > 30 OR s."9시00분" > 30)
GROUP BY u."학교명"
ORDER BY s."9시00분" DESC
LIMIT 10 -- 상위 10개 대학만 표시
"""
df2 = run_query(query2)

# 차트를 위해 데이터 형태 변경 (Wide to Long)
df2_melted = df2.melt(id_vars=['학교명', '인근역'], 
                      value_vars=['8시00분', '8시30분', '9시00분', '9시30분'],
                      var_name='시간대', value_name='혼잡도')

col1, col2 = st.columns([2, 1])
with col1:
    # 시각화: 멀티 라인 차트
    fig2 = px.line(df2_melted, x="시간대", y="혼잡도", color="학교명", 
                   markers=True, title="주요 대학별 등교 시간대 혼잡도 변화")
    st.plotly_chart(fig2, use_container_width=True)

with col2:
    st.subheader("🔍 인사이트")
    st.write("① (여기에 인사이트를 입력하세요)")
    st.write("② (여기에 인사이트를 입력하세요)")
    with st.expander("사용한 SQL 보기"):
        st.code(query2, language='sql')


# --- [차트 3] 지옥철에서 등교는 안돼! (최적 등교 시간) ---
st.header("3. ⏰ 언제 등교해야 가장 쾌적할까?")

# SQL: 버스와 지하철의 시간대별 평균 혼잡도 비교 (UNION ALL)
query3 = """
SELECT '지하철' AS "교통수단", ROUND(AVG("8시00분"), 2) AS "08:00", ROUND(AVG("8시30분"), 2) AS "08:30", 
       ROUND(AVG("9시00분"), 2) AS "09:00", ROUND(AVG("9시30분"), 2) AS "09:30", ROUND(AVG("10시00분"), 2) AS "10:00" 
FROM "지하철혼잡도" 
WHERE "요일구분" = '평일' AND "출발역" IN (SELECT DISTINCT SUBSTR("학교명", 1, 3) FROM "서울시대학")
UNION ALL
SELECT '버스' AS "교통수단", ROUND(AVG("8시하차총승객수")/10, 2) AS "08:00", -- 스케일 조정을 위해 10으로 나눔
       ROUND((AVG("8시하차총승객수") + AVG("9시하차총승객수")) / 20, 2) AS "08:30",
       ROUND(AVG("9시하차총승객수")/10, 2) AS "09:00",
       ROUND((AVG("9시하차총승객수") + AVG("10시하차총승객수")) / 20, 2) AS "09:30",
       ROUND(AVG("10시하차총승객수")/10, 2) AS "10:00"
FROM "버스정류장" 
WHERE "버스정류장 위치(자치구)" IN (SELECT DISTINCT "행정구" FROM "서울시대학")
"""
df3 = run_query(query3)
df3_melted = df3.melt(id_vars='교통수단', var_name='시간', value_name='수치')

col1, col2 = st.columns([2, 1])
with col1:
    # 시각화: 영역 차트
    fig3 = px.area(df3_melted, x="시간", y="수치", color="교통수단",
                   title="버스 vs 지하철 시간대별 혼잡도 추이 (정규화)")
    st.plotly_chart(fig3, use_container_width=True)

with col2:
    st.subheader("🔍 인사이트")
    st.write("① (여기에 인사이트를 입력하세요)")
    st.write("② (여기에 인사이트를 입력하세요)")
    with st.expander("사용한 SQL 보기"):
        st.code(query3, language='sql')

st.info("💡 모든 데이터는 SQLite 데이터베이스를 기반으로 실시간 쿼리된 결과입니다.")