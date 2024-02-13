import pandas as pd
import os
from shapely.geometry import Polygon


def load_datepop():

    directory = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    csv_directory = os.path.join(directory, 'data/datepop')
    csv_file_path = os.path.join(csv_directory, "shop_playing.csv")

    df = pd.read_csv(
        csv_file_path, encoding="utf-8-sig").drop('Unnamed: 0', axis=1).reset_index(drop=True)

    return df
