import streamlit as st
import pandas as pd
import sqlite3
import plotly.express as px

# --- 1. 페이지 설정 및 제목 ---
st.set_page_config(page_title="서울시 통학러 대시보드", layout="wide")
st.title("🎓 대학생 통학 지옥 탈출 리포트")
st.markdown("매학기, 통학에 지친 대학생들을 위해! 서울시 대학 주변의 혼잡도를 분석하여 최적의 등교 시간을 찾아봅니다.")

# --- 2. 데이터베이스 연결 함수 ---
def run_query(query):
    # 데이터베이스에 연결하고 쿼리를 실행한 뒤 결과를 표(DataFrame)로 돌려줍니다.
    with sqlite3.connect("통학러.db") as conn:
        return pd.read_sql(query, conn)

# --- [차트 1] 대학 환승 지옥 리포트 ---
st.header("1. 🚌 자치구별 버스 하차량")

# SQL: 자치구별 대학 수와 버스 하차객 비교
query1 = """
SELECT 
    u."행정구" AS 자치구, 
    COUNT(DISTINCT u."학교명") AS 대학교수,
    SUM(b."8시하차총승객수" + b."9시하차총승객수") AS 버스하차총합
FROM "서울시대학" u
JOIN "버스정류장" b ON u."행정구" = b."버스정류장 위치(자치구)"
GROUP BY 자치구
"""
df1 = run_query(query1)

fig1 = px.bar(df1, x="자치구", y="버스하차총합", color="대학교수",
             title="자치구별 대학 밀집도에 따른 버스 하차량",
             labels={"버스하차총합": "오전 피크 하차객 수", "대학교수": "대학 수"})
st.plotly_chart(fig1, use_container_width=True)


# --- [차트 2] 모든 대학 혼잡도 추이 (누락 해결) ---
st.header("2. ⏳ 대학별 혼잡도 지속 시간 비교")

query2 = """
SELECT 
    u."학교명", 
    s."출발역" AS "인근역", 
    s."8시00분", s."8시30분", s."9시00분", s."9시30분"
FROM "서울시대학" u 
JOIN "지하철혼잡도" s ON (s."출발역" LIKE '%' || SUBSTR(u."학교명", 1, 2) || '%') -- 2글자 매칭으로 완화
WHERE s."요일구분" = '평일'
GROUP BY u."학교명"
ORDER BY s."9시00분" DESC
"""
df2 = run_query(query2)
df2_melted = df2.melt(id_vars=['학교명'], value_vars=['8시00분', '8시30분', '9시00분', '9시30분'],
                      var_name='시간대', value_name='혼잡도')

fig2 = px.line(df2_melted, x="시간대", y="혼잡도", color="학교명", 
                title="대학별 오전 등교 피크타임 혼잡도 변화")
st.plotly_chart(fig2, use_container_width=True)


# --- [차트 3] 18시까지 확장된 최적 등교 시간 ---
st.header("3. ⏰ 언제 등교해야 가장 쾌적할까? (08시-18시)")

# 시간대별 컬럼 리스트 자동 생성 및 평균 계산 (SQL 생략, 개념 위주)
query3 = """
SELECT '지하철' AS "교통수단", 
       AVG("8시00분") AS "08:00", AVG("10시00분") AS "10:00", 
       AVG("12시00분") AS "12:00", AVG("14시00분") AS "14:00", 
       AVG("16시00분") AS "16:00", AVG("18시00분") AS "18:00"
FROM "지하철혼잡도" WHERE "요일구분" = '평일'
UNION ALL
SELECT '버스' AS "교통수단", 
       AVG("8시하차총승객수")/10, AVG("10시하차총승객수")/10,
       AVG("12시하차총승객수")/10, AVG("14시하차총승객수")/10,
       AVG("16시하차총승객수")/10, AVG("18시하차총승객수")/10
FROM "버스정류장"
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
