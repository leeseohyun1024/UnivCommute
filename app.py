import streamlit as st
import pandas as pd
import sqlite3
import plotly.express as px

# --- 1. 페이지 설정 및 제목 ---
st.set_page_config(page_title="서울시 통학러 대시보드", layout="wide")
st.title("🎓 대학생 통학 지옥 탈출 리포트")
st.markdown("통학에 지친 대학생들을 위해, 서울시 대학 주변의 버스와 지하철 혼잡도를 분석하여 최적의 등교 시간을 찾아봅니다.")

# --- 데이터베이스 연결 함수 ---
def run_query(query):
    with sqlite3.connect("통학러.db") as conn:
        return pd.read_sql(query, conn)

# --- [차트 1] 자치구별 분석 ---
st.header("1. 🚌 자치구별 대학 밀집도 및 버스 하차량")
st.markdown("> 각 구의 대학 수와 실제 버스 이용량을 비교하여 '버스 의존도'를 파악합니다.")

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

col1, col2 = st.columns([2, 1])
with col1:
    fig1 = px.bar(df1, x="자치구", y="버스하차총합", color="대학교수",
                  text_auto='.2s', title="자치구별 대학 수 대비 버스 하차량")
    st.plotly_chart(fig1, use_container_width=True)
with col2:
    st.subheader("🔍 인사이트")
    st.write("① **광진구/마포구** 등 대학 밀집 지역은 타 구 대비 버스 하차량이 압도적으로 높아, 정류장 인근 병목 현상이 예상됩니다.")
    st.write("② 대학 수는 적으나 하차량이 많은 구는 해당 지역이 주요 **환승 거점**임을 시사합니다.")

# --- [추가] 1-2. 지하철 버전 자치구 리포트 ---
st.header("1-2. 🚇 자치구별 지하철 혼잡도 리포트")
st.markdown("> 자치구 내 주요 대학가 역들의 평균 혼잡도를 분석합니다.")

query_subway_gu = """
SELECT 
    u."행정구" AS 자치구, 
    AVG(s."9시00분") AS 평균지하철혼잡도
FROM "서울시대학" u
JOIN "지하철혼잡도" s ON (s."출발역" LIKE '%' || SUBSTR(u."학교명", 1, 2) || '%')
WHERE s."요일구분" = '평일'
GROUP BY u."행정구"
ORDER BY 평균지하철혼잡도 DESC
"""
df_subway_gu = run_query(query_subway_gu)

fig_subway_gu = px.bar(df_subway_gu, x="자치구", y="평균지하철혼잡도", 
                      color="평균지하철혼잡도", color_continuous_scale="Reds",
                      title="자치구별 대학 인근역 평균 지하철 혼잡도")
st.plotly_chart(fig_subway_gu, use_container_width=True)

# --- [차트 2] 대학별 혼잡도 지속 비교 ---
st.header("2. ⏳ 대학별 혼잡도 지속 시간 비교")
st.markdown("> 요청하신 주요 대학 매칭 로직을 적용하여 모든 대학을 가나다순으로 표시합니다.")

query2 = """
SELECT 
    u."학교명", 
    s."출발역" AS "인근역", 
    s."8시00분", s."8시30분", s."9시00분", s."9시30분"
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
ORDER BY u."학교명" ASC -- 중복 ORDER BY 제거 및 가나다순 설정
"""
df2 = run_query(query2)
df2_melted = df2.melt(id_vars=['학교명', '인근역'], 
                      value_vars=['8시00분', '8시30분', '9시00분', '9시30분'],
                      var_name='시간대', value_name='혼잡도')

col1, col2 = st.columns([2, 1])
with col1:
    fig2 = px.line(df2_melted, x="시간대", y="혼잡도", color="학교명", 
                    markers=True, title="전체 대학별 등교 시간대 혼잡도 변화")
    st.plotly_chart(fig2, use_container_width=True)
with col2:
    st.subheader("🔍 인사이트")
    st.write("① **고원형 그래프**: 8시부터 9시 30분까지 혼잡도가 유지되는 역은 상습 정체 구간으로, 1교시 등교가 매우 힘든 대학입니다.")
    st.write("② **급경사형 그래프**: 9시에 혼잡도가 폭발하는 대학은 9시 수업 집중도가 높으므로 지각 위험이 큽니다.")

# --- [차트 3] 골든타임 분석 (정규화 버전) ---
st.header("3. ⏰ 수단별 등교 골든타임 추이 비교")
st.markdown("> 버스(인원수)와 지하철(%)의 단위가 다르므로, 각 수단의 최대치를 기준으로 상대적 혼잡도를 비교합니다.")

query3 = """
SELECT '지하철' AS "교통수단", 
       AVG("8시00분") AS "08시", AVG("10시00분") AS "10시", 
       AVG("12시00분") AS "12시", AVG("14시00분") AS "14시", 
       AVG("16시00분") AS "16시", AVG("18시00분") AS "18시"
FROM "지하철혼잡도" 
WHERE "요일구분" = '평일' AND "출발역" IN (SELECT DISTINCT SUBSTR("학교명", 1, 2) FROM "서울시대학")
UNION ALL
SELECT '버스' AS "교통수단", 
       AVG("8시하차총승객수") AS "08시", AVG("10시하차총승객수") AS "10시",
       AVG("12시하차총승객수") AS "12시", AVG("14시하차총승객수") AS "14시",
       AVG("16시하차총승객수") AS "16시", AVG("18시하차총승객수") AS "18시"
FROM "버스정류장" 
WHERE "버스정류장 위치(자치구)" IN (SELECT DISTINCT "행정구" FROM "서울시대학")
"""
df3 = run_query(query3)

# --- 데이터 정규화(Normalization) 처리 ---
# 각 행(수단)별로 최대값으로 나누어 0~1 사이 값으로 변환합니다.
time_cols = ["08시", "10시", "12시", "14시", "16시", "18시"]
df3_values = df3[time_cols]
df3_norm = df3_values.div(df3_values.max(axis=1), axis=0) # 행별 최대값으로 나누기
df3_norm["교통수단"] = df3["교통수단"]

# 시각화를 위한 Melt
df3_melted = df3_norm.melt(id_vars='교통수단', var_name='시간', value_name='상대적혼잡도')

# 한 그래프에 겹쳐서 그리기
fig3 = px.line(df3_melted, x="시간", y="상대적혼잡도", color="교통수단",
              line_shape="spline", markers=True,
              title="버스 vs 지하철 시간대별 상대적 혼잡도 추이 (Max=1.0)",
              labels={"상대적혼잡도": "상대적 혼잡 수준 (0~1)"})

# Y축 범위를 0~1.1로 고정하여 가독성 확보
fig3.update_yaxes(range=[0, 1.1])
st.plotly_chart(fig3, use_container_width=True)

st.subheader("🔍 인사이트")
st.write("① **피크 타임 일치 여부**: 지하철과 버스의 정점이 일치하는 08시~09시 사이가 가장 피함이 권장되는 '레드 타임'입니다.")
st.write("② **수단별 회복 탄력성**: 지하철은 오전 피크 이후 급격히 쾌적해지는 반면, 버스는 오후 시간대에도 상대적으로 높은 유동 인구를 유지합니다.")

st.info("💡 모든 데이터는 SQLite 데이터베이스를 기반으로 실시간 쿼리된 결과입니다. 매학기, 통학으로 고통받는 모든 대학생을 응원합니다!")
