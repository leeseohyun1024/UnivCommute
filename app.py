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
    db_path = "통학러 db"
    if not os.path.exists(db_path):
        st.error(f"데이터베이스 파일('{db_path}')을 찾을 수 없습니다.")
        return pd.DataFrame()
    try:
        with sqlite3.connect(db_path) as conn:
            return pd.read_sql(query, conn)
    except Exception as e:
        st.error(f"SQL 실행 오류: {e}")
        return pd.DataFrame()

# --- [섹션 A] 1번 & 2번 차트 데이터 준비 ---
st.divider()

# 1. 자치구별 대학교 수
query_univ_count = 'SELECT "행정구" AS 자치구, COUNT(DISTINCT "학교명") AS 대학교수 FROM "서울시대학" GROUP BY "행정구"'
df_univ_base = run_query(query_univ_count)

# 2. 버스 하차량
query_bus = 'SELECT "버스정류장 위치(자치구)" AS 자치구, SUM("8시하차총승객수" + "9시하차총승객수") AS 버스하차총합 FROM "버스정류장" GROUP BY "버스정류장 위치
