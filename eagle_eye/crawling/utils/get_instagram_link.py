import re


def get_instagram_link(input_url):

    wrong_url = ["https://instagram.com", "https://instagram.com/", "http://instagram.com",
                 "http://instagram.com/", "instagram.com", "instagram.com/",
                 "https://www.instagram.com/", "http://www.instagram.com/", "https://www.instagram.com",
                 "http://www.instagram.com"]

    if input_url in wrong_url:
        return False

    # query parameter 제거
    if "?" in input_url:
        input_url = input_url.split("?")[0]

    pattern = r'(instagram\.com/[^/?]+)'

    match = re.search(pattern, input_url)

    if match:
        instagram_url = match.group(1)

        instagram_url = "https://" + instagram_url

        if instagram_url.endswith('/'):
            instagram_url = instagram_url[:-1]
            return instagram_url
        return instagram_url
    else:
        return False
