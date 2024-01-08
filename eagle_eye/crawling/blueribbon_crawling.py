import pandas as pd
import requests
from requests.exceptions import HTTPError, ConnectionError

class BlueRibbonCrawler:
    def __init__(self, location):
        self.location = location
        self.current_page = 0
        self.max_page = 0
        self.data = pd.DataFrame(columns=["name", "ribbonType"])

    def crawling(self):
        print("Blue Ribbon Survey crawling start!")
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
            response = requests.get(f"https://www.bluer.co.kr/api/v1/restaurants?page={self.current_page}&query={self.location}")
            if self.max_page == 0:
                self.max_page = response.json()["page"]["totalPages"]
            items = response.json()['_embedded']['restaurants']
            data = [{"name": item["headerInfo"]["nameKR"], "ribbonType": item["headerInfo"]["ribbonType"]} for item in items]
            new_data = pd.DataFrame(data)
            self.data = pd.concat([self.data, new_data], ignore_index=True)
            self.current_page += 1
        except (HTTPError, ConnectionError) as e:
            print(f"Network error: {e}")
            return
        except Exception as e:
            print(f"An error occurred: {e}")


# if __name__ == "__main__":
#     location_input = input()
#     ribbon_crawler = BlueRibbonCrawler(location_input)
#     ribbon_crawler.crawling()
#     if "목로" in ribbon_crawler.data['name'].values:
#         print("목로 리본 등급: ", ribbon_crawler.data.loc[ribbon_crawler.data["name"] == "목로", "ribbonType"].iloc[0])
#     if "가나다" in ribbon_crawler.data['name'].values:
#         print("가나다 리본 등급: ", ribbon_crawler.data.loc[ribbon_crawler.data["name"] == "가나다", "ribbonType"].iloc[0])
#     if "어썸로즈" in ribbon_crawler.data['name'].values:
#         print("어썸로즈 리본 등급: ", ribbon_crawler.data.loc[ribbon_crawler.data["name"] == "어썸로즈", "ribbonType"].iloc[0])
