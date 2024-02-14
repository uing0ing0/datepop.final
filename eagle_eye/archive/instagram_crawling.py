import pandas as pd
import requests
from requests.exceptions import HTTPError, ConnectionError

import time


class InstagramCrawler:
    def crawling(self, url):
        json_link = url + "/?__a=1&__d=dis"

        # 인스타그램측 블락 방지용
        time.sleep(5)
        try:
            response = requests.get(json_link)

            data = response.json()
            followers_count = data['graphql']['user']['edge_followed_by']['count']
            posts_count = data['graphql']['user']['edge_owner_to_timeline_media']['count']

            return {
                "status": 'complete',
                "followers": followers_count,
                "posts_count": posts_count
            }
        except (HTTPError, ConnectionError) as e:
            return {
                "status": 'network error',
                "followers": followers_count,
                "posts_count": posts_count
            }
        except:
            return {
                "status": 'incomplete',
                "followers": None,
                "posts_count": None
            }

# if __name__ == "__main__":

#     instagram_crawaler = InstagramCrawler()
#     response = instagram_crawaler.crawling("https://instagram.com/letsgo._.kim")
#     print(response)
#     if response["status"] == "complete":
#         print("followers: ", response["followers"])
#         print("posts_count: ", response["posts_count"])
#     else:
#         print("Failed to crawl")
