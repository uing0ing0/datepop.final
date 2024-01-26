def calculate_score(series):
    score = 0

    # 인스타그램 계정 존재 여부
    if series['instagram_link'] != None:
        score += 5

        # 인스타그램 게시글 수
        if series['instagram_post'] == None:
            pass
        elif int(series['instagram_post']) >= 100:
            score += 4
        elif int(series['instagram_post']) >= 50:
            score += 3

        # 인스타그램 팔로워 수
        if series['instagram_follower'] == None:
            pass
        elif int(series['instagram_follower']) >= 3000:
            score += 4
        elif int(series['instagram_follower']) >= 1000:
            score += 3

    # 네이버 방문자 리뷰 수
    if series['visitor_review_count'] == None:
        pass
    elif int(series['visitor_review_count']) >= 900:
        score += 3
    elif int(series['visitor_review_count']) >= 500:
        score += 2

    # 네이버 블로그 리뷰 수
    if series['blog_review_count'] == None:
        pass
    elif int(series['blog_review_count']) >= 600:
        score += 4
    elif int(series['blog_review_count']) >= 300:
        score += 3

    # 역으로부터 거리
    if series['distance_from_subway'] == None:
        pass
    elif int(series['distance_from_subway']) <= 500:
        score += 2
    elif int(series['distance_from_subway']) <= 900:
        score += 1

    # 기타 조건들
    score += 5 if series['hot_spot'] else 0
    score += 3 if series['on_tv'] else 0
    score += 2 if series['parking_available'] else 0
    score += 1 if series['no_kids'] else 0
    score += 4 if series['seoul_michelin'] else 0
    score += 6 if series['gender-balance'] else 0
    score += 6 if series['age-2030'] else 0
    score += 3 if series['on_blue_ribbon'] else 0
    score += 10 if series['new_store'] else 0

    return score
