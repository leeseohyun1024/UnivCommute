import streamlit as st
import pandas as pd
import sqlite3
import plotly.express as px
import os

# --- 1. 페이지 설정 및 제목 ---
st.set_page_config(page_title="서울시 통학러 대시보드", layout="wide")
st.title("🎓 대학생 통학 지옥 탈출 리포트")
st.markdown("통학에 지친 대학생들을 위해 서울시 대학가 주변의 교통 혼잡도를 분석합니다.")

# --- 데이터베이스 연결 함수 ---
def run_query(query):
    db_path = "통학러.db"
    if not os.path.exists(db_path):
        st.error(f"데이터베이스 파일('{db_path}')을 찾을 수 없습니다.")
        return pd.DataFrame()
    try:
        with sqlite3.connect(db_path) as conn:
            # 쿼리 실행 전 공백 정리
            return pd.read_sql(query.strip(), conn)
    except Exception as e:
        st.error(f"SQL 실행 오류: {e}")
        return pd.DataFrame()

# --- [섹션 A] 데이터 준비 ---
st.divider()

# 1. 자치구별 대학교 수
query_univ_count = 'SELECT "행정구" AS 자치구, COUNT(DISTINCT "학교명") AS 대학교수 FROM "서울시대학" GROUP BY "행정구"'
df_univ_base = run_query(query_univ_count)

# 2. 버스 하차량
query_bus = 'SELECT "버스정류장 위치(자치구)" AS 자치구, SUM("8시하차총승객수" + "9시하차총승객수") AS 버스하차총합 FROM "버스정류장" GROUP BY "버스정류장 위치(자치구)"'
df_bus_data = run_query(query_bus)

# --- [섹션 A] 2번 지하철 혼잡도 쿼리 (전체 자치구 강제 노출 버전) ---
query_subway = '''
SELECT 
    u."행정구" AS 자치구, 
    IFNULL(AVG(s."9시00분"), 0) AS 평균지하철혼잡도
FROM "서울시대학" u
LEFT JOIN "지하철혼잡도" s ON (
    /* 1. 기본 이름 매칭 */
    s."출발역" LIKE "%" || SUBSTR(u."학교명", 1, 2) || "%"
    /* 추가. 용산구: 숙명여대(숙대입구) */
    OR (u."학교명" LIKE "%숙명%" AND s."출발역" LIKE "%숙대입구%")
    /* 2. 종로구: 성균관대(혜화), 배화여대(경복궁), 가톨릭대(혜화/동대문) */
    OR (u."학교명" LIKE "%성균관%" AND s."출발역" LIKE "%혜화%")
    OR (u."학교명" LIKE "%배화%" AND s."출발역" LIKE "%경복궁%")
    OR (u."학교명" LIKE "%가톨릭%" AND s."출발역" IN ("혜화", "동대문"))
    
    /* 3. 송파구: 한국체대(올림픽공원) */
    OR (u."학교명" LIKE "%한국체육%" AND s."출발역" LIKE "%올림픽공원%")
    
    /* 4. 강서구: 강서대/KC대(화곡) */
    OR (u."학교명" LIKE "%강서%" AND s."출발역" LIKE "%화곡%")
    OR (u."학교명" LIKE "%KC%" AND s."출발역" LIKE "%화곡%")
    OR (u."학교명" LIKE "%서울기독%" AND s."출발역" LIKE "%화곡%")
    
    /* 5. 도봉구/구로구/기타 */
    OR (u."학교명" LIKE "%덕성%" AND s."출발역" LIKE "%쌍문%")
    OR (u."학교명" LIKE "%동양미래%" AND s."출발역" LIKE "%구일%")
    OR (u."학교명" LIKE "%성공회%" AND s."출발역" LIKE "%온수%")
    OR (u."학교명" LIKE "%국민%" AND s."출발역" LIKE "%길음%")
    OR (u."학교명" LIKE "%서경%" AND s."출발역" LIKE "%성신여대%")
    OR (u."학교명" LIKE "%홍익%" AND s."출발역" LIKE "%홍대입구%")
    OR (u."학교명" LIKE "%서강%" AND s."출발역" LIKE "%대흥%")
    OR (u."학교명" LIKE "%건국%" AND s."출발역" LIKE "%건대입구%")
    OR (u."학교명" LIKE "%세종%" AND s."출발역" LIKE "%어린이대공원%")
)
WHERE (s."요일구분" = "평일" OR s."요일구분" IS NULL)
GROUP BY u."행정구"
'''
df_subway_data = run_query(query_subway)

# 데이터 병합 및 시각화
if not df_univ_base.empty:
    df1 = pd.merge(df_univ_base, df_bus_data, on="자치구", how="left").fillna(0)
    df2 = pd.merge(df_univ_base, df_subway_data, on="자치구", how="left").fillna(0)

    col_left, col_right = st.columns(2)
    with col_left:
        st.header("1. 🚌 버스 혼잡도")
        if not df1.empty:
            fig1 = px.bar(df1.sort_values("버스하차총합", ascending=False), x="자치구", y="버스하차총합", color="대학교수", text_auto=".2s", title="자치구별 대학 수 대비 버스 하차량", color_continuous_scale="Viridis")
            st.plotly_chart(fig1, use_container_width=True)

    with col_right:
        st.header("2. 🚇 지하철 혼잡도")
        if not df2.empty:
            fig2 = px.bar(df2.sort_values("평균지하철혼잡도", ascending=False), x="자치구", y="평균지하철혼잡도", color="대학교수", title="자치구별 지하철 혼잡도 및 대학 밀집도", color_continuous_scale="Viridis")
            st.plotly_chart(fig2, use_container_width=True)

# --- 인사이트 (수정 없이 유지) ---
st.subheader("🔍 인사이트")
ins_col1, ins_col2 = st.columns([1.5, 1])
with ins_col1:
    st.markdown(
        "① **관악구**와 **서초구**는 압도적인 버스 하차량을 기록하고 있습니다. "
        "특히 관악구는 서울대학교라는 부지가 넓은 대학이 존재하며, 지형 특성상 캠퍼스 내부로 진입하기 위한 버스 수요가 많은 것으로 파악됩니다.\n\n"
        "② 버스 하차량과 지하철 혼잡도에 상위권을 차지하고 있는 관악구(서울대)와 성북구(국민대, 서경대 등)는 고지대나 산지에 위치한 캠퍼스가 많습니다. "
        "이는 지하철역에서 내린 뒤 반드시 버스를 타야 하는 구조를 만듭니다.\n\n"
        "③ **서대문구와 마포구** 역시 대학 밀집도가 높지만 버스 하차량 순위는 관악구보다 낮습니다. "
        "이는 해당 지역의 대학들이 상대적으로 지하철 접근성이 더 좋거나, 주거지와 학교가 더 인접해 있을 가능성을 시사합니다.\n\n"
        "④ 지하철 혼잡도에서는 **성북구**가 1위를 차지하고 있으며 대학이 가장 많이 밀집된 곳인만큼 유동인구가 많다고 추정할 수 있습니다. "
        "또한, 성북구를 지나는 4호선은 가장 유동인구가 많은 지하철이기 때문에 대학 밀집도와 더불어 이동하는 일반 시민도 많을 것으로 추정됩니다."
    )
with ins_col2:
    with st.expander("🛠️ 데이터 추출 쿼리 확인"):
        st.code(query_bus, language="sql")
        st.code(query_subway, language="sql")

# --- 3. 대학별 혼잡도 지속 시간 비교 ---
st.divider()
st.header("3. ⏳ 대학별 혼잡도 지속 시간 비교")

query_time = '''
SELECT u."학교명", s."출발역" AS "인근역", s."8시00분", s."8시30분", s."9시00분", s."9시30분", s."10시00분", s."10시30분"
FROM "서울시대학" u
JOIN "지하철혼잡도" s ON (s."출발역" LIKE "%" || SUBSTR(u."학교명", 1, 2) || "%"
    OR (u."학교명" LIKE "%덕성%" AND s."출발역" LIKE "%쌍문%")
    OR (u."학교명" LIKE "%숙명%" AND s."출발역" LIKE "%숙대입구%")
    OR (u."학교명" LIKE "%이화%" AND s."출발역" LIKE "%이대%")
    OR (u."학교명" LIKE "%연세%" AND s."출발역" LIKE "%신촌%")
    OR (u."학교명" LIKE "%중앙%" AND s."출발역" LIKE "%흑석%")
    OR (u."학교명" LIKE "%경희%" AND s."출발역" LIKE "%회기%")
    OR (u."학교명" LIKE "%한국외국어%" AND s."출발역" LIKE "%외대앞%")
    OR (u."학교명" LIKE "%건국%" AND s."출발역" LIKE "%건대입구%")
    OR (u."학교명" LIKE "%동국%" AND s."출발역" LIKE "%동대입구%")
    OR (u."학교명" LIKE "%홍익%" AND s."출발역" LIKE "%홍대입구%")
)
WHERE s."요일구분" = "평일"
GROUP BY u."학교명"
ORDER BY u."학교명" ASC
'''
df_time = run_query(query_time)

if not df_time.empty:
    df_melted = df_time.melt(id_vars=["학교명", "인근역"], value_vars=["8시00분", "8시30분", "9시00분", "9시30분", "10시00분", "10시30분"], var_name="시간대", value_name="혼잡도")
    c1, c2 = st.columns([2, 1])
    with c1:
        fig_line = px.line(df_melted, x="시간대", y="혼잡도", color="학교명", markers=True, title="대학별 등교 시간대 혼잡도 추이")
        st.plotly_chart(fig_line, use_container_width=True)
    with c2:
        with st.expander("🛠️ SQL문"):
            st.code(query_time, language="sql")
        st.write("① 8시 정점 이후 9시까지 완만해지나, 대학별로 등교 피크가 다르므로 실시간 확인이 필요합니다.")
        st.write("")
        st.write("② **동국대학교**는 오전 혼잡도가 특히 높으므로, 10시 이후 등교 시 가장 쾌적합니다.")

# --- 4. 버스 등교 골든타임 분석 ---
st.divider()
st.header("4. ⏰ 버스 등교 골든타임 분석")

query_golden = 'SELECT "버스" AS "교통수단", AVG("8시하차총승객수") AS "08시", AVG("10시하차총승객수") AS "10시", AVG("12시하차총승객수") AS "12시", AVG("14시하차총승객수") AS "14시", AVG("16시하차총승객수") AS "16시", AVG("18시하차총승객수") AS "18시" FROM "버스정류장" WHERE "버스정류장 위치(자치구)" IN (SELECT DISTINCT "행정구" FROM "서울시대학")'
df_golden = run_query(query_golden)

if not df_golden.empty:
    df_golden_melt = df_golden.melt(id_vars="교통수단", var_name="시간", value_name="하차인원")
    c3, c4 = st.columns([2, 1])
    with c3:
        fig_area = px.area(df_golden_melt, x="시간", y="하차인원", title="🚌 대학가 버스 시간대별 평균 하차 인원 추이", color_discrete_sequence=["#ff7f0e"], markers=True)
        st.plotly_chart(fig_area, use_container_width=True)
    with c4:
        with st.expander("🛠️ SQL문"):
            st.code(query_golden, language="sql")
        st.write("① **등/하교 피크 뚜렷**: 08시와 18시에 하차 인원이 집중됩니다. 대학가 특성상 저녁 유입 인원도 많으므로 하교 시간대 정류장 혼잡에 주의해야 합니다.")
        st.write("")
        st.write("② **오후의 여유**: 10시부터 14시 사이는 하차 인원이 적습니다. 이 시간대를 등교 시간으로 활용하면 훨씬 쾌적한 이동이 가능합니다.")

st.info("👣 매학기, 통학으로 고통받는 모든 대학생을 응원합니다!")
