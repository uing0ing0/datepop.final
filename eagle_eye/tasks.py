import threading
import os

from navermap_crawling import crawling_one_keyword
from scoring import scoring


def crawl_and_score(location, keywords):

    for keyword in keywords:
        crawled_data = crawling_one_keyword(location=location, keyword=keyword)
        crawled_data = scoring(crawled_data=crawled_data,
                               location=location, keyword=keyword)

        save_result(location=location, keyword=keyword,
                    result_data=crawled_data)


# DB 연결이 이루어지면, 아래 함수는 DB에 데이터를 전달하는 함수로 교체해야함
def save_result(location, keyword, result_data):

    directory = os.path.dirname(os.path.abspath(__file__))
    csv_file_path = os.path.join(
        directory, 'data/result/', f"{location}-{keyword}.csv")

    result_data.to_csv(csv_file_path, encoding='utf-8-sig', index=False, )
