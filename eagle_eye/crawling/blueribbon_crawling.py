import pandas as pd
import requests
from requests.exceptions import HTTPError, ConnectionError


class BlueRibbonCrawler:
    def __init__(self, location):
        self.location = location
        self.current_page = 0
        self.max_page = 0
        self.data = pd.DataFrame(
            columns=["name", "ribbonType", "latitude", "longitude", "address"])

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
        except (HTTPError, ConnectionError) as e:
            print(f"Network error: {e}")
            return
        except Exception as e:
            print(f"An error occurred: {e}")

    def crawling_onepage(self):
        try:
            response = requests.get(
                f"https://www.bluer.co.kr/api/v1/restaurants?page={self.current_page}&query={self.location}")

            if self.max_page == 0:
                self.max_page = response.json()["page"]["totalPages"]
            items = response.json()['_embedded']['restaurants']
            data = []
            for item in items:
                name = item["headerInfo"]["nameKR"]
                ribbonType = item["headerInfo"]["ribbonType"]
                latitude = item["gps"]["latitude"]
                longitude = item["gps"]["longitude"]

                print(latitude)

                roadAddrPart1 = item["juso"]["roadAddrPart1"]
                detailAddress = item["juso"]["detailAddress"]

                # None 확인 및 대체
                roadAddrPart1 = "" if roadAddrPart1 is None else roadAddrPart1
                detailAddress = "" if detailAddress is None else detailAddress

                address = roadAddrPart1 + " " + detailAddress

                data.append({"name": name, "ribbonType": ribbonType, "latitude": latitude,
                             "longitude": longitude, "address": address})

            new_data = pd.DataFrame(data)

            self.data = pd.concat([self.data, new_data], ignore_index=True)
            self.current_page += 1
        except (HTTPError, ConnectionError) as e:
            print(f"Network error: {e}")
            return
        except Exception as e:
            print(f"An error occurred: {e}")


if __name__ == "__main__":
    # location_input = input()
    location_input = "가로수길"
    ribbon_crawler = BlueRibbonCrawler(location_input)
    ribbon_crawler.crawling()
