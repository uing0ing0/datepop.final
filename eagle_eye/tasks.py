import os
from celery import current_task
# import logging

from eagle_eye.navermap_crawling import crawling_one_keyword
from eagle_eye.scoring import scoring

from eagle_eye.celery import app


@app.task
def crawl_and_score(location, keywords):

    for keyword in keywords:
        crawled_data = crawling_one_keyword(location=location, keyword=keyword)
        crawled_data = scoring(crawled_data=crawled_data,
                               location=location, keyword=keyword)

        save_result(location=location, keyword=keyword,
                    result_data=crawled_data)


# DB 연결이 이루어지면, 아래 함수는 DB에 데이터를 저장하는 함수로 교체 필요
def save_result(location, keyword, result_data):

    directory = os.path.dirname(os.path.abspath(__file__))
    result_directory = os.path.join(directory, 'data/result')
    csv_file_path = os.path.join(result_directory, f"{location}-{keyword}.csv")

    # 결과를 저장하기 전에 디렉토리가 존재하는지 확인하고, 없으면 생성
    os.makedirs(result_directory, exist_ok=True)

    result_data.to_csv(csv_file_path, encoding='utf-8-sig', index=False)
