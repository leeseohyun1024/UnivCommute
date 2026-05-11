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
st.markdown("> 각 구의 대학 수와 실제 버스 이용량을 비교하여 버스 혼잡도를 파악합니다.")

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
    st.write("① **성북구/서대문구** 등 대학 밀집 지역은 타 구 대비 버스 하차량이 압도적으로 높아, 정류장 인근 병목 현상이 예상됩니다.")
    st.write("② 대학 수는 적으나 하차량이 많은 구는 해당 지역이 주요 **환승 거점**임을 시사합니다. 편안한 통학을 원하신다면, **서초구, 관악구, 송파구**에서 환승하기보다는 다른 방법을 추천합니다.")

# --- [차트 2] 자치구별 지하철 혼잡도 리포트 ---
st.header("2. 🚇 자치구별 지하철 혼잡도 리포트")
st.markdown("> 자치구별 대학 수와 지하철 혼잡도를 결합하여 분석합니다.")

# SQL: 자치구별 대학교 수와 지하철 혼잡도 평균을 함께 추출
query_subway_gu = """
SELECT 
    u."행정구" AS 자치구, 
    COUNT(DISTINCT u."학교명") AS 대학교수,
    AVG(s."9시00분") AS 평균지하철혼잡도
FROM "서울시대학" u
JOIN "지하철혼잡도" s ON (s."출발역" LIKE '%' || SUBSTR(u."학교명", 1, 2) || '%')
WHERE s."요일구분" = '평일'
GROUP BY u."행정구"
ORDER BY 평균지하철혼잡도 DESC
"""
df_subway_gu = run_query(query_subway_gu)

col1, col2 = st.columns([2, 1])

with col1:
    # Y축은 혼잡도(높이), 색상은 대학교 수(밀집도)로 설정
    fig_subway_gu = px.bar(df_subway_gu, 
                          x="자치구", 
                          y="평균지하철혼잡도", 
                          color="대학교수",  # 색상을 대학교 수로 변경
                          color_continuous_scale="Viridis", # 대학 밀집도를 나타내기 좋은 컬러셋
                          title="자치구별 지하철 혼잡도 (높이) 및 대학교 밀집도 (색상)",
                          labels={"평균지하철혼잡도": "평균 혼잡도 (%)", "대학교수": "대학교 수"})
    
    st.plotly_chart(fig_subway_gu, use_container_width=True)

with col2:
    st.subheader("🔍 인사이트")
    st.write("① **성북구, 은평구** 등은 인근 대학가 역의 혼잡도가 매우 높게 형성되어 있어 하차 시 병목 현상이 예상됩니다.")
    st.write("② **성북구**는 가장 많이 대학이 밀집된 지역입니다. 가장 높은 혼잡도와 더불어 가장 높은 대학교 수를 가지고 있어 체감 밀집도는 더욱 높아질 수 있습니다. 지하철 노선 중 가장 붐비는 4호선이 지나는 성북구이므로 성북구의 노선에 다니는 지하철의 배차를 많이 편성할 필요가 있습니다.")

# --- [차트 2] 대학별 혼잡도 지속 비교 ---
st.header("3. ⏳ 대학별 혼잡도 지속 시간 비교")
st.markdown("> 각 대학별 혼잡도와 혼잡지속도를 판단하고 가장 밀집도가 높은 등교 시간을 파악합니다.")

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
ORDER BY u."학교명" ASC -- 중복 ORDER BY 제거 및 가나다순 설정
"""
df2 = run_query(query2)
df2_melted = df2.melt(id_vars=['학교명', '인근역'], 
                      value_vars=['8시00분', '8시30분', '9시00분', '9시30분', '10시00분', '10시30분'],
                      var_name='시간대', value_name='혼잡도')

col1, col2 = st.columns([2, 1])
with col1:
    fig2 = px.line(df2_melted, x="시간대", y="혼잡도", color="학교명", 
                    markers=True, title="전체 대학별 등교 시간대 혼잡도 변화")
    st.plotly_chart(fig2, use_container_width=True)
with col2:
    st.subheader("🔍 인사이트")
    st.write("①대부분 출근시간인 8시에 혼잡도가 가장 높고 9시까지 점차 줄어드는 경향을 보인다. 9시부터는 각 대학별로 혼잡도가 낮아지거나 높아지므로 대학별 수치를 잘 확인하여 등교 시간을 결정해야 합니다.")
    st.write("② **동국대학교**는 아침 시간대에 높은 혼잡도를 보입니다. 따라서 등교 시간을 추세가 내려가는 10시로 가져가는 것을 추천합니다.")
    
# --- [차트 3] 버스 등교 골든타임 분석 ---
st.header("4. ⏰ 버스 등교 골든타임 분석")
st.markdown("> 언덕에 위치한 학교는 버스가 필수죠? 대학가 주변 버스 정류장의 시간대별 하차 인원을 분석하여 가장 여유로운 등교 시간을 제안합니다.")

# SQL: 버스 데이터 추출
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

# 데이터 재구조화 (Melt)
df_bus_only = df3.melt(id_vars='교통수단', var_name='시간', value_name='하차인원')

# 레이아웃 분할: 왼쪽 2(그래프), 오른쪽 1(인사이트)
col1, col2 = st.columns([2, 1])

with col1:
    # 시각화: 버스 단독 영역 차트
    fig_bus = px.area(df_bus_only, x="시간", y="하차인원", 
                     title="🚌 대학가 버스 시간대별 평균 하차 인원 추이",
                     color_discrete_sequence=['#ff7f0e'], 
                     markers=True)
    
    fig_bus.update_layout(xaxis_title="시간대", yaxis_title="평균 하차 승객 수 (명)", showlegend=False)
    st.plotly_chart(fig_bus, use_container_width=True)

with col2:
    st.subheader("🔍 버스 통학 인사이트")
    st.write("① **등/하교 피크 뚜렷**: 08시와 18시에 하차 인원이 집중됩니다. 대학가 특성상 저녁 유입 인원도 많으므로 하교 시간대 정류장 혼잡에 주의해야 합니다.")
    st.write("② **오후의 여유**: 10시부터 14시 사이는 하차 인원이 적습니다. 이 시간대를 등교 시간으로 활용하면 훨씬 쾌적한 이동이 가능합니다.")
st.info("👣 매학기, 통학으로 고통받는 모든 대학생을 응원합니다!🚶‍♀️")
