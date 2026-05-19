import os
import json
from flask import Flask, request, jsonify, render_template, redirect, url_for
import gspread
from google.oauth2.service_account import Credentials
from dotenv import load_dotenv

load_dotenv()

app = Flask(
    __name__,
    template_folder="../templates",
    static_folder="../static"
)

# ─── Google Sheets 연결 ───────────────────────────────────────────────────────

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

def get_sheet():
    """Google Sheets 클라이언트를 반환합니다."""
    # Vercel 환경변수에서 서비스 계정 JSON을 문자열로 읽음
    creds_json = os.environ.get("GOOGLE_CREDENTIALS_JSON")
    if not creds_json:
        raise ValueError("GOOGLE_CREDENTIALS_JSON 환경변수가 설정되지 않았습니다.")

    creds_dict = json.loads(creds_json)
    creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
    client = gspread.authorize(creds)

    spreadsheet_id = os.environ.get("SPREADSHEET_ID")
    sheet = client.open_by_key(spreadsheet_id).sheet1
    return sheet


# ─── 라우트 ──────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    """설문조사 페이지"""
    return render_template("index.html")


@app.route("/submit", methods=["POST"])
def submit():
    """설문조사 제출 → Google Sheets에 저장"""
    data = request.form

    name       = data.get("name", "").strip()
    age_group  = data.get("age_group", "")
    satisfaction = data.get("satisfaction", "")
    recommend  = data.get("recommend", "")
    comment    = data.get("comment", "").strip()

    if not all([name, age_group, satisfaction, recommend]):
        return "필수 항목을 모두 입력해주세요.", 400

    from datetime import datetime
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    sheet = get_sheet()

    # 헤더가 없으면 첫 행에 추가
    existing = sheet.get_all_values()
    if not existing:
        sheet.append_row(["타임스탬프", "이름", "연령대", "만족도", "추천여부", "의견"])

    sheet.append_row([timestamp, name, age_group, satisfaction, recommend, comment])

    return redirect(url_for("thank_you"))


@app.route("/thank-you")
def thank_you():
    return """
    <!DOCTYPE html>
    <html lang="ko">
    <head>
      <meta charset="UTF-8">
      <meta name="viewport" content="width=device-width, initial-scale=1.0">
      <title>제출 완료</title>
      <link rel="preconnect" href="https://fonts.googleapis.com">
      <link href="https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;700&display=swap" rel="stylesheet">
      <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
          font-family: 'Noto Sans KR', sans-serif;
          background: #0f172a;
          color: #f1f5f9;
          min-height: 100vh;
          display: flex;
          align-items: center;
          justify-content: center;
        }
        .card {
          text-align: center;
          padding: 60px 40px;
          background: #1e293b;
          border-radius: 20px;
          border: 1px solid #334155;
          max-width: 420px;
        }
        .icon { font-size: 64px; margin-bottom: 24px; }
        h1 { font-size: 28px; margin-bottom: 12px; color: #38bdf8; }
        p { color: #94a3b8; line-height: 1.7; margin-bottom: 32px; }
        a {
          display: inline-block;
          padding: 12px 28px;
          background: #38bdf8;
          color: #0f172a;
          border-radius: 10px;
          text-decoration: none;
          font-weight: 700;
          margin: 0 8px;
          transition: opacity .2s;
        }
        a:hover { opacity: .8; }
        a.outline {
          background: transparent;
          border: 1px solid #38bdf8;
          color: #38bdf8;
        }
      </style>
    </head>
    <body>
      <div class="card">
        <div class="icon">✅</div>
        <h1>제출 완료!</h1>
        <p>소중한 의견을 보내주셔서 감사합니다.<br>응답이 성공적으로 저장되었습니다.</p>
        <a href="/">다시 참여하기</a>
        <a href="/results" class="outline">결과 보기</a>
      </div>
    </body>
    </html>
    """


@app.route("/results")
def results():
    """차트 결과 페이지"""
    return render_template("result.html")


@app.route("/api/data")
def api_data():
    """차트용 JSON 데이터 API"""
    sheet = get_sheet()
    rows = sheet.get_all_records()  # 헤더 제외한 딕셔너리 리스트

    # 만족도 집계
    satisfaction_count = {}
    recommend_count    = {}
    age_count          = {}

    for row in rows:
        s = row.get("만족도", "")
        r = row.get("추천여부", "")
        a = row.get("연령대", "")

        satisfaction_count[s] = satisfaction_count.get(s, 0) + 1
        recommend_count[r]    = recommend_count.get(r, 0) + 1
        age_count[a]          = age_count.get(a, 0) + 1

    return jsonify({
        "total": len(rows),
        "satisfaction": satisfaction_count,
        "recommend":    recommend_count,
        "age_group":    age_count,
    })


# ─── Vercel용 핸들러 ─────────────────────────────────────────────────────────

# Vercel은 'app' 변수를 WSGI 앱으로 인식합니다.
# 로컬 테스트 시:
if __name__ == "__main__":
    app.run(debug=True, port=5000)
