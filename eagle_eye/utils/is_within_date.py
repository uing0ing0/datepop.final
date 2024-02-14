from datetime import datetime, timedelta


def is_within_one_month(date_text):
    # 현재 날짜
    current_date = datetime.now()

    # 날짜 텍스트를 datetime 객체로 변환
    date = datetime.strptime(date_text, "%Y년 %m월 %d일 %A")

    # 날짜가 한 달 이내인지 확인
    return current_date - timedelta(days=30) <= date <= current_date


def is_within_two_weeks(date_text):
    # 현재 날짜
    current_date = datetime.now()

    # 날짜 텍스트를 datetime 객체로 변환
    date = datetime.strptime(date_text, "%Y년 %m월 %d일 %A")

    # 날짜가 한 달 이내인지 확인
    return current_date - timedelta(days=14) <= date <= current_date
