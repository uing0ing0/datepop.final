import csv
import os
from shapely.geometry import Polygon


def load_seoul_hotspots():
    seoul_hotspots = []

    # 스크립트 파일이 위치한 디렉토리를 기준으로 상대 경로 구하기
    directory = os.path.dirname(os.path.abspath(__file__))
    csv_file_path = os.path.join(directory, 'data', 'seoul_hotspots.csv')

    # CSV 파일 읽기
    with open(csv_file_path, 'r', encoding='utf-8') as file:
        reader = csv.reader(file)
        next(reader)  # 첫 번째 헤더 라인 건너뛰기

        for row in reader:
            location = row[0]
            polygon_coords = [(float(x), float(y)) for x, y in (
                point.split(',') for point in row[1].split(';'))]
            seoul_hotspots.append(
                {"location": location, "polygon_area": Polygon(polygon_coords)})

    return seoul_hotspots
