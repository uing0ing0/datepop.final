import pandas as pd
import requests
from requests.exceptions import HTTPError, ConnectionError
import csv
import os

# 블루리본서베이 크롤링 신버전


class BlueRibbonCrawler:
    def __init__(self, zone1):
        self.zone1 = zone1
        self.current_page = 0
        self.max_page = 0
        self.columns = ["name", "ribbonType",
                        "latitude", "longitude", "address", "phone"]
        self.data = pd.DataFrame(columns=self.columns)

    def crawling(self):
        print("Blue Ribbon Survey crawling start......")
        # initialization
        try:
            print("Crawling page 0......")
            self.crawling_onepage()
            for i in range(1, self.max_page):
                print(f"Crawling page {i}......")
                self.crawling_onepage()
            print("Blue Ribbon Survey crawling done!")
            print(self.data)
        except (HTTPError, ConnectionError) as e:
            print(f"Network error: {e}")
            return
        except Exception as e:
            print(f"An error occurred: {e}")

    def crawling_onepage(self):
        try:
            blue_ribbon_survey_url = f"https://www.bluer.co.kr/api/v1/restaurants?page={self.current_page}&size=100&zone1={
                self.zone1}"
            response = requests.get(blue_ribbon_survey_url).json()

            if self.max_page == 0:
                self.max_page = response["page"]["totalPages"]
            items = response['_embedded']['restaurants']
            data = []
            for item in items:
                name = item["headerInfo"]["nameKR"]
                ribbonType = item["headerInfo"]["ribbonType"]
                phone = item["defaultInfo"]["phone"]
                latitude = item["gps"]["latitude"]
                longitude = item["gps"]["longitude"]

                roadAddrPart1 = item["juso"]["roadAddrPart1"]
                detailAddress = item["juso"]["detailAddress"]

                # None 확인 및 대체
                roadAddrPart1 = "" if roadAddrPart1 is None else roadAddrPart1
                detailAddress = "" if detailAddress is None else detailAddress

                address = roadAddrPart1 + " " + detailAddress

                data.append({"name": name, "ribbonType": ribbonType, "phone": phone,
                             "latitude": latitude, "longitude": longitude, "address": address})

            new_data = pd.DataFrame(data)

            self.data = pd.concat([self.data, new_data], ignore_index=True)
            self.current_page += 1
        except (HTTPError, ConnectionError) as e:
            print(f"Network error: {e}")
            return
        except Exception as e:
            print(f"An error occurred: {e}")


if __name__ == "__main__":

    zone1_list = ["강원", "경기", "경남%2F울산", "경북", "광주", "대구", "대전",
                  "부산", "서울 강남", "서울 강북", "인천", "전남", "전북", "제주", "충남", "충북%2F세종"]

    for zone1 in zone1_list:

        try:
            print(f"====================== {zone1} ======================")

            ribbon_crawler = BlueRibbonCrawler(zone1=zone1)
            ribbon_crawler.crawling()

            directory = os.path.dirname(os.path.abspath(__file__))
            data_directory = os.path.join(directory, 'data/blueribbon')
            if not os.path.exists(data_directory):
                os.makedirs(data_directory)

            if zone1 == "경남%2F울산":
                zone1 = "경남, 울산"
            elif zone1 == "충북%2F세종":
                zone1 = "충북, 세종"

            with open(os.path.join(data_directory, f'{zone1}_bluer.csv'), 'w', newline='', encoding='utf-8') as file:
                writer = csv.writer(file)
                writer.writerow(ribbon_crawler.columns)

                for index, row in ribbon_crawler.data.iterrows():
                    writer.writerow(row)

        except Exception as e:
            print(e)
            print(f"Failed to crawl {zone1}...")
