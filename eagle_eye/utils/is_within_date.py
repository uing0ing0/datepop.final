from datetime import datetime, timedelta


def is_within_one_month(date_text):
    # 요일 정보를 제외하고 날짜만 추출
    date_text_formatted = ' '.join(date_text.split(' ')[:3])
    date = datetime.strptime(date_text_formatted, "%Y년 %m월 %d일")

    # 현재 날짜
    current_date = datetime.now()

    # 날짜가 한 달 이내인지 확인
    return current_date - timedelta(days=30) <= date <= current_date


def is_within_two_weeks(date_text):
    # 요일 정보를 제외하고 날짜만 추출
    date_text_formatted = ' '.join(date_text.split(' ')[:3])
    date = datetime.strptime(date_text_formatted, "%Y년 %m월 %d일")

    # 현재 날짜
    current_date = datetime.now()

    # 날짜가 두 주 이내인지 확인
    return current_date - timedelta(days=14) <= date <= current_date
