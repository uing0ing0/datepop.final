import threading
import os

from navermap_crawling import crawling_one_keyword
from scoring import scoring


def crawl_and_score_semaphore(location, keywords, semaphore):
    with semaphore:
        crawl_and_score(location, keywords)


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


def main():
    crawling_dict_list = [
        {
            "location": "강남역",
            "keywords": ["맛집", "공방", "만화카페", "커플 스튜디오", "동물카페"]
        },
        {
            "location": "가로수길",
            "keywords": ["맛집", "공방", "만화카페", "커플 스튜디오", "동물카페"]
        },
        {
            "location": "대학로",
            "keywords": ["맛집", "공방", "만화카페", "커플 스튜디오", "동물카페", "연극"]
        },
        {
            "location": "홍대",
            "keywords": ["맛집", "공방", "만화카페", "커플 스튜디오", "동물카페", "연극"]
        },
        {
            "location": "연남동",
            "keywords": ["맛집", "공방", "만화카페", "커플 스튜디오", "동물카페"]
        },
    ]

    semaphore = threading.Semaphore(1)

    threads = []
    for search_dict in crawling_dict_list:
        thread = threading.Thread(target=crawl_and_score_semaphore, args=(
            search_dict["location"], search_dict["keywords"], semaphore))
        threads.append(thread)

    # 모든 쓰레드 시작
    for thread in threads:
        thread.start()

    # 모든 쓰레드의 종료를 기다림
    for thread in threads:
        thread.join()


if __name__ == "__main__":
    main()
