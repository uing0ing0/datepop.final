import pandas as pd
import numpy as np
import math

from sklearn.metrics.pairwise import cosine_similarity
from sklearn.preprocessing import MinMaxScaler, RobustScaler

from utils.calculate_score import calculate_score
from utils.load_datepop import load_datepop


class CrawlingDataScorer:

    def __init__(self, crawled_data, location, keyword, is_food):
        self.location = location
        self.keyword = keyword
        self.is_food = is_food

        self.datepop_data = pd.DataFrame()
        self.crawled_data = crawled_data
        self.scaled_crawled_data = pd.DataFrame()

    # missing value 채워서 반환
    def fill_missing_value(self, data):

        missing_to_zero = ['instagram_post', 'instagram_follower',
                           'visitor_review_count', 'blog_review_count', ]
        missing_to_inf = ['distance_from_subway']

        missing_to_false = ['on_tv', 'seoul_michelin', 'on_blue_ribbon', "no_kids",
                            "parking_available", "hot_spot", "age-2030", "gender-balance", "new_store"]

        for column in missing_to_zero:
            data[column] = data[column].fillna(1)
        for column in missing_to_false:
            data[column] = data[column].fillna(False).astype('bool')
        for column in missing_to_inf:
            data[column] = data[column].fillna(1000)

        data = data.reset_index(drop=True)

        return data

    # str형으로 표기된 numerfic features를 int형으로 전환 후 반환
    def str_to_int(self, data):
        # Type Conversion
        str_to_int_features = ['instagram_post', 'instagram_follower',
                               'visitor_review_count', 'blog_review_count', 'distance_from_subway']

        for feature in str_to_int_features:
            data[feature] = data[feature].astype(int)

        return data

    # 데이트팝 매장 load
    def load_and_preprocess_datepop_data(self):

        datepop_data = load_datepop()

        # 인스타그램 링크 없는 경우(null 또는 빈 문자열) 제외
        datepop_data = datepop_data[datepop_data['instagram_link'].notna() & (
            datepop_data['instagram_link'] != '')]
        # 데이트팝 매장 중, 아래 features 값이 하나라도 없는 경우(null 또는 0) 제외
        drop_numeric_features = ['instagram_post', 'instagram_follower',
                                 'visitor_review_count', 'blog_review_count']

        datepop_data = datepop_data[datepop_data[drop_numeric_features].notna().all(
            axis=1) & (datepop_data[drop_numeric_features] != 0).all(axis=1)]

        datepop_data = self.fill_missing_value(datepop_data)
        self.datepop_data = self.str_to_int(datepop_data)

    # 크롤링 매장 전처리
    def preprocess_crawled_data(self):
        self.crawled_data = self.fill_missing_value(self.crawled_data)
        self.crawled_data = self.str_to_int(self.crawled_data)

    # 유사도 계산을 위한 numeric features 전처리
    def scaling_numeric_features(self):
        # Feature Scaling
        numeric_features = ['instagram_post', 'instagram_follower',
                            'visitor_review_count', 'blog_review_count']

        robust_scaler = RobustScaler()
        self.scaled_crawled_data[numeric_features] = robust_scaler.fit_transform(
            self.crawled_data[numeric_features])
        self.datepop_data[numeric_features] = robust_scaler.transform(
            self.datepop_data[numeric_features])

        min_max_scaler = MinMaxScaler()
        self.scaled_crawled_data[numeric_features] = min_max_scaler.fit_transform(
            self.scaled_crawled_data[numeric_features])
        self.datepop_data[numeric_features] = min_max_scaler.transform(
            self.datepop_data[numeric_features])

    # 크롤링 매장에 대한 기준표 점수 계산
    def calculate_condition_score(self):
        scores = []
        for index, item in self.crawled_data.iterrows():
            score = calculate_score(item)
            scores.append(score)

        self.crawled_data.insert(2, 'score', scores)

    # 크롤링 매장에 대한 데이트팝 매장과의 유사도 점수 계산
    def calculate_similarity_score(self):
        similarity_features = [
            'instagram_post', 'instagram_follower', 'visitor_review_count', 'blog_review_count']
        average_similarity = []
        for i, row in self.scaled_crawled_data.iterrows():
            row_df = pd.DataFrame([row[similarity_features]])
            similarities = cosine_similarity(
                row_df, self.datepop_data[similarity_features])[0]

            high_percent = np.percentile(similarities, 70)

            top_similarities = [
                sim for sim in similarities if sim >= high_percent]

            average_similarity.append(np.mean(top_similarities))

        similarity_scores = [5 * math.pow(10, sim)
                             for sim in average_similarity]
        self.crawled_data.insert(2, 'similarity', similarity_scores)

    def calculate_total_score(self):
        # Total Score
        total_scores = []
        for index, item in self.crawled_data.iterrows():
            score1 = item["similarity"]
            score2 = item["score"]

            total_scores.append(score1 + score2)

        self.crawled_data.insert(2, 'total_score', total_scores)
        self.crawled_data.sort_values(by="total_score", ascending=False,
                                      ignore_index=True, inplace=True)

    def scoring(self):
        self.load_and_preprocess_datepop_data()
        self.preprocess_crawled_data()
        self.scaling_numeric_features()
        self.calculate_condition_score()
        self.calculate_similarity_score()
        self.calculate_total_score()

    # def save_result(self):
    #     self.crawled_data.head(20).to_csv(f'data/crawl_score/hybrid/{self.location}{self.keyword}_top20.csv', encoding='utf-8-sig')


def scoring(crawled_data, location, keyword):

    is_food = False
    if keyword == "맛집":
        is_food = True

    scorer = CrawlingDataScorer(
        crawled_data=crawled_data, location=location, keyword=keyword, is_food=is_food)
    scorer.scoring()

    return scorer.crawled_data
