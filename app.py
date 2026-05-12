import streamlit as st
import pandas as pd
import sqlite3
import plotly.express as px
import os

# --- 1. 페이지 설정 및 제목 ---
st.set_page_config(page_title="서울시 통학러 대시보드", layout="wide")
st.title("🎓 대학생 통학 지옥 탈출 리포트")
st.markdown("통학에 지친 대학생들을 위해 서울시 대학가 주변의 교통 혼잡도를 분석합니다.")

# --- 데이터베이스 연결 함수 (에러 처리 강화) ---
def run_query(query):
    db_path = "통학러.db"
    # 파일 존재 여부 확인
    if not os.path.exists(db_path):
        st.error(f"⚠️ 데이터베이스 파일('{db_path}')을 찾을 수 없습니다. 경로를 확인해주세요.")
        return pd.DataFrame()
    
    try:
        with sqlite3.connect(db_path) as conn:
            return pd.read_sql(query, conn)
    except Exception as e:
        st.error(f"❌ SQL 쿼리 실행 중 오류 발생: {e}")
        return pd.DataFrame()

# --- [섹션 A] 1번 & 2번 차트 데이터 준비 ---
st.divider()

# 1. 자치구별 대학교 수 기준 데이터
# 테이블명과 컬럼명을 모두 쌍따옴표로 감싸 식별자 오류 방지
query_univ_count = 'SELECT "행정구" AS 자치구, COUNT(DISTINCT "학교명") AS 대학교수 FROM "서울시대학" GROUP BY "행정구"'
df_univ_base = run_query(query_univ_count)

# 2. 버스 하차량 데이터
query_bus = """
SELECT "버스정류장 위치(자치구)" AS 자치구, SUM("8시하차총승객수" + "9시하차총승객수") AS 버스하차총합
FROM "버스정류장" 
GROUP BY "버스정류장 위치(자치구)"
"""
df_bus_data = run_query(query_bus)

# 3. 지하철 혼잡도 데이터
query_subway = """
SELECT u."행정구" AS 자치구, AVG(s."9시00분") AS 평균지하철혼잡도
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
"""
df_subway_data = run_query(query_subway)

# --- 데이터 결합 및 유효성 검사 ---
if not df_univ_base.empty:
    df1 = pd.merge(df_univ_base, df_bus_data, on="자치구", how="left").fillna(0)
    df2 = pd.merge(df_univ_base, df_subway_data, on="자치구", how="left").fillna(0)

    # --- 차트 그리기 ---
    col_left, col_right = st.columns(2)

    with col_left:
        st.header("1. 🚌 버스 혼잡도")
        fig1 = px.bar(df1.sort_values("버스하차총합", ascending=False), 
                      x="자치구", y="버스하차총합", color="대학교수",
                      text_auto='.2s', title="자치구별 대학 수 대비 버스 하차량",
                      color_continuous_scale="Viridis")
        st.plotly_chart(fig1, use_container_width=True)

    with col_right:
        st.header("2. 🚇 지하철 혼잡도")
        fig2 = px.bar(df2.sort_values("평균지하철혼잡도", ascending=False), 
                      x="자치구", y="평균지하철혼잡도", color="대학교수",
                      title="자치구별 지하철 혼잡도 및 대학 밀집도",
                      color_continuous_scale="Viridis")
        st.plotly_chart(fig2, use_container_width=True)
else:
    st.warning("분석할 데이터를 불러오지 못했습니다.")

# --- [섹션 B] 인사이트 & SQL ---
st.subheader("🔍 인사이트")
ins_col1, ins_col2 = st.columns([1.5, 1])

with ins_col1:
    st.markdown("""① **관악구**와 **서초구**는 압도적인 버스 하차량을 기록하고 있습니다. 특히 관악구는 서울대학교라는 부지가 넓은 대학이 존재하며, 지형 특성상 캠퍼스 내부로 진입하기 위한 버스 수요가 많은 것으로 파악됩니다.
    ② 버스 하차량과 지하철 혼잡도에 상위권을 차지하고 있는 **관악구(서울대)**와 **성북구(국민대, 서경대 등)**는 고지대나 산지에 위치한 캠퍼스가 많습니다. 이는 지하철역에서 내린 뒤 반드시 버스를 타야 하는 구조를 만듭니다.
    ③ **서대문구와 마포구** 역시 대학 밀집도가 높지만 버스 하차량 순위는 관악구보다 낮습니다. 이는 해당 지역의 대학들이 상대적으로 지하철 접근성이 더 좋거나, 주거지와 학교가 더 인접해 있을 가능성을 시사합니다.
    ④ 지하철 혼잡도에서는 **성북구**가 1위를 차지하고 있으며 대학이 가장 많이 밀집된 곳인만큼 유동인구가 많다고 추청할 수 있습니다. 또한, 성북구를 지나는 4호선은 가장 유동인구가 많은 지하철이기 때문에 대학 밀집도와 더불어 이동하는 일반 시민도 많을 것으로 추정됩니다.
    """)

with ins_col2:
    with st.expander("🛠️ 데이터 추출 쿼리 확인"):
        st.code(query_bus, language="sql")
        st.code(query_subway, language="sql")

# --- 차트 3 & 4 ---
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
    OR (u."학교명" LIKE '건국대%' AND s."출발역" = '
