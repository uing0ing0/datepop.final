def calculate_score(series):
    score = 0

    score += 15 if series['new_store'] else 0
    score += 8 if series['gender-balance'] else 0
    score += 8 if series['age-2030'] else 0
    score += 6 if series['hot_spot'] else 0
    score += 3 if series['parking_available'] else 0
    score += 3 if series['no_kids'] else 0

    # 인스타그램 계정 존재 여부
    if series['instagram_link'] != None and series['instagram_link'] != "":
        score += 4  # 점수 차이를 더 줄까? # 차라리 감점 형식으로 바꿀까?

    # 역으로부터 거리
    if series['distance_from_subway'] == None:
        pass
    elif int(series['distance_from_subway']) <= 400:
        score += 3
    elif int(series['distance_from_subway']) <= 700:
        score += 2

    if series["blog_review_count"] >= 500:
        if series["visitor_review_count"] >= 2 * series["blog_review_count"]:
            score -= 5

    return score
