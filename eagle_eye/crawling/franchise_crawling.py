import requests
from bs4 import BeautifulSoup

import pandas as pd
import os

# 공정거래위원회의 정보공개서에서 프랜차이즈 체인 정보 크롤링


def franchise_crawling():
    url = "https://franchise.ftc.go.kr/mnu/00013/program/userRqst/list.do?pageUnit=20000&pageIndex=1"

    response = requests.get(url)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "lxml")

    table = soup.find('table', class_="table")

    rows = table.find_all('tr')
    data = []

    for row in rows[1:]:
        cols = row.find_all('td')
        data.append({
            "상호": cols[1].text.strip(),
            "영업표지": cols[2].text.strip(),
            "대표자": cols[3].text.strip(),
            "등록번호": cols[4].text.strip(),
            "최초등록일": cols[5].text.strip(),
            "업종": cols[6].text.strip(),
        })
    df = pd.DataFrame(data)

    directory = os.path.dirname(os.path.abspath(__file__))
    csv_file_path = os.path.join(directory, 'data/', "franchise.csv")

    df.to_csv(csv_file_path, encoding='utf-8-sig', index=False, )
    print(df)


if __name__ == "__main__":
    franchise_crawling()
