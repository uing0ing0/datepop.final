from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException, TimeoutException, StaleElementReferenceException

from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

import pandas as pd
from urllib.parse import urlparse, parse_qs
from shapely.geometry import Point
import time
import re
import os

from blueribbon_crawling import BlueRibbonCrawler
from eagle_eye.crawling.utils.load_hotspots import load_seoul_hotspots


class DatePopCrawler:
    def __init__(self, location, keyword, hotspots, is_food, crawl_new, blue_ribbon):
        self.location = location
        self.keyword = keyword
        self.search_word = location + " " + keyword
        self.hotspots = hotspots
        self.crawl_new = crawl_new
        self.blue_ribbon = blue_ribbon

        self.is_food = is_food

        self.data = pd.DataFrame(columns=['store_id', 'name', 'category', 'is_food', 'instagram_link', 'instagram_post', 'instagram_follower', 'visitor_review_count',
                                          'blog_review_count', 'distance_from_subway', 'on_tv', 'parking_available', 'no_kids', 'pet_available', 'seoul_michelin',
                                          'age-2030', 'gender-balance', 'on_blue_ribbon', 'image_urls'])
        self.empty_searchIframe = """//*[@id="_pcmap_list_scroll_container"]"""
        self.empty_entryIframe = """//*[@id="app-root"]"""
        self.empty_root = """//*[@id="root"]"""

        self.search_iframe = """//*[@id="searchIframe"]"""
        self.entry_iframe = """//*[@id="entryIframe"]"""

        self.store_dict = None

        self.driver = self.initialize_driver()
        self.wait = WebDriverWait(self.driver, 10)

    def initialize_driver(self):
        options = webdriver.ChromeOptions()
        options.add_argument("--enable-logging")
        options.add_argument("--v=1")  # 로그 레벨 설정

        driver = webdriver.Chrome(options=options)
        driver.get("https://map.naver.com/")

        driver.execute_script("window.open('');")
        driver.switch_to.window(driver.window_handles[0])

        return driver

    def initialize_dictionary(self):
        self.store_dict = {
            "store_id": None,
            "name": "",
            "category": "",
            "is_food": self.is_food,
            "instagram_link": None,
            "instagram_post": None,
            "instagram_follower": None,
            "hot_spot": False,
            "visitor_review_count": 0,
            "blog_review_count": 0,
            "distance_from_subway": None,
            "on_tv": False,
            "parking_available": False,
            "no_kids": False,
            "pet_available": False,
            "seoul_michelin": False,
            "age-2030": None,
            "gender-balance": None,
            "on_blue_ribbon": None,
            "image_urls": [],
        }

    def search_keyword(self):
        self.wait.until(EC.presence_of_element_located(
            (By.XPATH, self.empty_root)))

        css_selector = ".input_search"
        elem = self.wait.until(EC.presence_of_element_located(
            (By.CSS_SELECTOR, css_selector)))

        elem.send_keys(self.search_word)
        time.sleep(1)
        elem.send_keys(Keys.RETURN)

    def click_option_new_store(self):
        time.sleep(1)
        self.move_to_search_iframe()
        # # 옵션버튼 클릭
        # option_xpath = """//*[@id="app-root"]/div/div[1]/div/div/div/div/div/span[1]/a"""
        # option_button = self.wait.until(EC.element_to_be_clickable((By.XPATH, option_xpath)))
        # self.driver.execute_script("arguments[0].click()", option_button)
        # "더보기" 버튼 클릭
        more_xpath = """//a[span[contains(text(),'더보기')]]"""
        more_button = self.wait.until(
            EC.element_to_be_clickable((By.XPATH, more_xpath)))
        self.driver.execute_script("arguments[0].click()", more_button)
        # "새로오픈" 버튼 클릭
        new_xpath = """//a[contains(text(),'새로오픈')]"""
        new_button = self.wait.until(
            EC.element_to_be_clickable((By.XPATH, new_xpath)))
        self.driver.execute_script("arguments[0].click()", new_button)

    def get_into_store(self, i):
        # 크롤링 값을 저장할 dictionay 변수 초기화
        self.initialize_dictionary()
        self.move_to_search_iframe()

        store_xpath = f"""//*[@id="_pcmap_list_scroll_container"]/ul/li[{
            i}]/div[1]/a[1]"""
        elem = self.wait.until(
            EC.element_to_be_clickable((By.XPATH, store_xpath)))
        time.sleep(2)

        self.driver.execute_script("arguments[0].scrollIntoView(true);", elem)
        self.driver.execute_script("arguments[0].click()", elem)

        time.sleep(1)

        self.driver.switch_to.default_content()
        self.wait.until(EC.presence_of_element_located(
            (By.XPATH, self.empty_root)))
        self.driver.find_element(By.XPATH, self.empty_root)

        self.wait.until(EC.presence_of_element_located(
            (By.XPATH, self.entry_iframe)))
        iframe_element = self.driver.find_element(By.XPATH, self.entry_iframe)
        iframe_src = iframe_element.get_attribute('src')
        self.driver.switch_to.frame(iframe_element)
        self.driver.find_element(By.XPATH, self.empty_entryIframe)

        parsed_url = urlparse(iframe_src)
        query_params = parse_qs(parsed_url.query)
        lat = query_params.get('x')[0]
        lon = query_params.get('y')[0]
        store_point = Point(lat, lon)

        path_segments = parsed_url.path.split('/')
        store_id = path_segments[2]

        self.store_dict["store_id"] = store_id

        print("Check the store to be in hotspot area")
        for i in range(len(self.hotspots)):
            polygon = self.hotspots[i]["polygon_area"]
            if polygon.contains(store_point):
                self.store_dict["hot_spot"] = True  # default = False
                break

        # 매장 클릭 시 "요청하신 페이지를 찾을 수 없습니다"라는 메시지를 갖는 에러 가끔 발생
        # "새로고침" 버튼 클릭하여 매장 정보 다시 불러오기
        try:
            # WebDriverWait(self.driver, 1).until(EC.presence_of_element_located((By.XPATH, "//div[contains(text(), '요청하신 페이지를 찾을 수 없습니다.')]")))
            reset_elem = WebDriverWait(self.driver, 1).until(
                EC.presence_of_element_located((By.XPATH, """//a[contains(text(), "새로고침)]""")))

            # reset_xpath = """//a[contains(text(), "새로고침)]"""

            # reset_elem = self.wait.until(EC.presence_of_element_located((By.XPATH, reset_xpath)))
            self.driver.execute_script("arguments[0].click()", reset_elem)
        except:
            pass

    # 대표사진 URL 추출 함수
    def get_image_urls(self, images_xpath, max_images=10):
        try:
            self.wait.until(EC.presence_of_all_elements_located(
                (By.XPATH, images_xpath)))
            image_elements = self.driver.find_elements(By.XPATH, images_xpath)
            image_urls = [img.get_attribute('src')
                          for img in image_elements][:max_images]
            return image_urls
        except StaleElementReferenceException:
            # 요소가 stale 상태인 경우 재시도
            print("재시도")
            return self.get_image_urls(images_xpath, max_images)
        # except Exception as e:
        #     print("이미지 URL 추출 중 에러 발생: ", e)
        #     return None

    def get_store_details(self):

        time.sleep(3)

        # 매장 이름, 카테고리
        try:
            store_name_xpath = """//*[@id="_title"]/div/span"""
            elem = self.wait.until(EC.presence_of_all_elements_located(
                (By.XPATH, store_name_xpath)))

            self.store_dict['name'] = elem[0].text
            self.store_dict['category'] = elem[1].text
        except Exception as e:
            print("매장 이름, 카테고리 에러: ", e)
            # 희귀하게 매장 이름을 크롤링하지 못하는 에러 발생
            # 해당 매장 생략하고 다음 매장 크롤링 진행
            return False

        # 방문자 리뷰, 블로그 리뷰 개수
        try:
            elem_visitor = self.driver.find_element(
                By.XPATH, value="//a[contains(text(), '방문자리뷰')]")
            elem_blog = self.driver.find_element(
                By.XPATH, value="//a[contains(text(), '블로그리뷰')]")

            visitor_review_count = int(re.findall(
                r'\d+', elem_visitor.text.replace(",", ""))[0])
            blog_review_count = int(re.findall(
                r'\d+', elem_blog.text.replace(",", ""))[0])

            self.store_dict['visitor_review_count'] = visitor_review_count
            self.store_dict['blog_review_count'] = blog_review_count
        except NoSuchElementException:
            self.store_dict['visitor_review_count'] = None
            self.store_dict['blog_review_count'] = None

        # 인스타그램 계정 존재 확인
        try:
            elem = self.driver.find_element(
                By.XPATH, value="//a[contains(@href, 'instagram.com')]")
            instagram_url = elem.get_attribute('href')

            # 인스타그램 계정 url 뒤에 queryParameter가 붙은 경우 or "/"가 하나 더 붙은 경우
            # 두 경우 모두, 해당 url에 "/embed"를 concatenation하면 응답으로 "알 수 없는 페이지"
            # 때문에 url에서 해당 인스타그램 계정의 이름에 해당하는 부분 이후는 제거
            if instagram_url == "https://instagram.com" or instagram_url == "https://instagram.com/" or instagram_url == "http://instagram.com" or instagram_url == "http://instagram.com/":
                self.store_dict['instagram_link'] = None
            else:
                if "?" in instagram_url:
                    instagram_url = instagram_url.split("?")[0]

                if instagram_url.count("/") >= 4:
                    instagram_url = "/".join(instagram_url.split("/", 4)[:4])

                self.store_dict['instagram_link'] = instagram_url
        except NoSuchElementException:
            self.store_dict['instagram_link'] = None
            self.store_dict['instagram_post'] = None
            self.store_dict['instagram_follower'] = None
        except Exception as e:
            print("인스타그램 에러:", e)
            self.store_dict['instagram_link'] = None
            self.store_dict['instagram_post'] = None
            self.store_dict['instagram_follower'] = None

        # 서울 미쉐린 가이드
        try:
            michelin_xpath = """//div[a[contains(text(), '미쉐린 가이드 서울')]]"""
            self.driver.find_element(By.XPATH, michelin_xpath)
            self.store_dict['seoul_michelin'] = True
        except NoSuchElementException:
            self.store_dict['seoul_michelin'] = False
        except Exception as e:
            print("서울 미쉐린 가이드 에러:", e)
            self.store_dict['seoul_michelin'] = None

        # 지하철역 출구로부터 거리
        try:
            subway_xpath = "/html/body/div[3]/div/div/div/div[5]/div/div[2]/div[1]/div/div[1]/div/div"
            elem = self.driver.find_element(By.XPATH, subway_xpath)
            text = elem.text

            numbers = re.findall(r'\d+', text)
            if numbers:
                self.store_dict["distance_from_subway"] = numbers[-1]
        except NoSuchElementException:
            self.store_dict["distance_from_subway"] = None
        except Exception as e:
            print("지하철역 에러: ", e)
            self.store_dict["distance_from_subway"] = None

        # 방송 출연 여부
        try:
            tv_xpath = """//strong[descendant::span[text()='TV방송정보']]"""
            self.driver.find_element(By.XPATH, tv_xpath)
            self.store_dict['on_tv'] = True
        except NoSuchElementException:
            self.store_dict['on_tv'] = False
        except Exception as e:
            print("방송 출연 에러: ", e)
            self.store_dict['on_tv'] = None

        # 주차 가능, 반려동물 동반, 노키즈존
        try:
            convenient_xpath = "//strong[descendant::span[text()='편의']]/ancestor::div[1]/div/div"
            elem = self.driver.find_element(By.XPATH, convenient_xpath)
            convenients = elem.text

            for parking in ["주차", "발렛파킹"]:
                if parking in convenients:
                    self.store_dict["parking_available"] = True
                    break

            if "반려동물 동반" in convenients:
                self.store_dict["pet_available"] = True

            if "노키즈존" in convenients:
                self.store_dict["no_kids"] = True
        except NoSuchElementException:
            self.store_dict["parking_available"] = False
            self.store_dict["no_kids"] = False
            self.store_dict["pet_available"] = False
        except Exception as e:
            print("주차, 반려동물, 노키즈 에러: ", e)
            self.store_dict["parking_available"] = False
            self.store_dict["no_kids"] = False
            self.store_dict["pet_available"] = False

        # DataLab: 연령별 / 성별 검색 인기도
        try:
            # entryIframe 스크롤 끝까지 내려서 모든 컨텐츠 로딩
            last_height = self.driver.execute_script(
                "return document.body.scrollHeight")
            while True:
                self.driver.execute_script(
                    "window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(0.5)
                new_height = self.driver.execute_script(
                    "return document.body.scrollHeight")
                if new_height == last_height:
                    break
                last_height = new_height

            # DataLab 항목 찾고 해당 element로 스크롤 이동
            datalab_xpath = """//div[h2/span[contains(text(), '데이터랩')]]"""
            datalab_elem = self.driver.find_element(By.XPATH, datalab_xpath)
            self.driver.execute_script(
                "arguments[0].scrollIntoView(true);", datalab_elem)

            # "테마키워드"라는 text가 있는 경우, "더보기 버튼을 눌러줘야 연령별/성별 검색어 비율 확인 가능
            try:
                theme_keyword_xpath = """.//div/div/div/h3[contains(text(), '테마키워드')]"""
                datalab_elem.find_element(By.XPATH, theme_keyword_xpath)
                button_elem = datalab_elem.find_element(
                    By.XPATH, ".//div[2]/div/a")
                self.driver.execute_script("arguments[0].click()", button_elem)
            except NoSuchElementException:
                pass
            except Exception as e:
                print("데이터랩 더보기 버튼 에러: ", e)

            # 20대와 30대가 top 1, 2를 차지하는지 확인
            age_xpath = """//*[@id="bar_chart_container"]/ul/li/div[1]/span/span[1]"""
            age_elements = self.wait.until(
                EC.presence_of_all_elements_located((By.XPATH, age_xpath)))
            percentage_by_age = [
                round(float(item.text.replace('%', '')), 2) for item in age_elements]
            top_two = sorted(percentage_by_age, reverse=True)[:2]
            is_2030_in_top_two = percentage_by_age[1] in top_two and percentage_by_age[2] in top_two
            if is_2030_in_top_two:
                self.store_dict["age-2030"] = True
            else:
                self.store_dict["age-2030"] = False

            # 남성의 비율이 50%를 넘는지 확인
            gender_xpath = """//*[@id="pie_chart_container"]/div/*[local-name()='svg']/*[local-name()='g'][1]/*[local-name()='g'][3]/*[local-name()='g'][4]/*[local-name()='g']/*[local-name()='text'][2]"""
            gender_elements = self.wait.until(
                EC.presence_of_all_elements_located((By.XPATH, gender_xpath)))
            female, male = [round(float(item.text.replace("%", "")), 0)
                            for item in gender_elements]
            if male > 50:
                self.store_dict["gender-balance"] = False
            else:
                self.store_dict["gender-balance"] = True
        except NoSuchElementException:
            self.store_dict["age-2030"] = None
            self.store_dict["gender-balance"] = None
        except Exception as e:
            print("데이터랩 에러: ", e)
            self.store_dict["age-2030"] = None
            self.store_dict["gender-balance"] = None

        # 블루 리본 등재 여부 -> "맛집" 키워드일 경우에만 확인
        if self.is_food == True:
            if self.store_dict["name"] in self.blue_ribbon["name"].values:
                self.store_dict["on_blue_ribbon"] = True
            else:
                self.store_dict["on_blue_ribbon"] = False

        # 대표사진 크롤링
        try:
            imgtab_xpath = "//a[.//span[contains(text(),'사진')]]"
            elem = self.driver.find_element(By.XPATH, imgtab_xpath)
            self.driver.execute_script("arguments[0].click()", elem)
            time.sleep(2)  # 사진 로딩 대기

            images_xpath = """/html/body/div[3]/div/div/div/div[6]/div[4]/div/div/div/div/a/img"""
            self.store_dict["image_urls"] = self.get_image_urls(
                images_xpath=images_xpath)
            # self.wait.until(EC.presence_of_all_elements_located((By.XPATH, images_xpath)))

            # image_elements = self.wait.until(
            #     EC.presence_of_all_elements_located((By.XPATH, images_xpath))
            # )
            # image_urls = [img.get_attribute('src') for img in image_elements][:10] # 최대 10개의 이미지 url
            # self.store_dict["image_urls"] = image_urls
        except NoSuchElementException as e:
            print("대표사진 NoSuchElementException")
            print(e)
            self.store_dict["image_urls"] = []
        # except TimeoutException:
        #     self.store_dict["image_urls"] = None
        # except Exception as e:
        #     print("대표사진 에러: ", e)
        #     self.store_dict["image_urls"] = None

        # 인스타그램 크롤링
        if self.store_dict['instagram_link'] != None:  # 인스타그램 계정이 있는 경우에만 실행
            try:
                instagram_embed_url = self.store_dict['instagram_link'] + "/embed"

                # 인스타그랩 탭으로 이동
                self.driver.switch_to.window(self.driver.window_handles[1])
                self.driver.get(instagram_embed_url)

                xpath = """//span[contains(., '팔로워') and contains(., '게시물')]/span/span"""
                elements = self.wait.until(
                    EC.presence_of_all_elements_located((By.XPATH, xpath)))

                follower = elements[0].text
                post = elements[1].text
                self.store_dict["instagram_follower"] = follower
                self.store_dict["instagram_post"] = post
            except NoSuchElementException:
                self.store_dict['instagram_link'] = None
                self.store_dict["instagram_follower"] = None
                self.store_dict["instagram_post"] = None
            except Exception as e:
                print("인스타그램 에러: ", e)
                self.store_dict['instagram_link'] = None
                self.store_dict["instagram_follower"] = None
                self.store_dict["instagram_post"] = None

            # 네이버지도 탭으로 복귀
            self.driver.switch_to.window(self.driver.window_handles[0])

        print(self.store_dict)

        return True

    # 한 매장에 대한 크롤링 진행 후, 해당 정보를 DataFrame에 Insertion
    def insert_into_dataframe(self):
        new_data = pd.DataFrame([self.store_dict])
        self.data = pd.concat([self.data, new_data], ignore_index=True)

    # 한 페이지 크롤링
    def crawling_one_page(self):
        self.move_to_search_iframe()

        li_xpath = """//*[@id="_pcmap_list_scroll_container"]/ul/li"""
        store_elements = self.wait.until(
            EC.presence_of_all_elements_located((By.XPATH, li_xpath)))
        store_count = len(store_elements)
        self.driver.execute_script(
            "arguments[0].scrollIntoView(true);", store_elements[-1])
        while True:
            time.sleep(0.5)
            store_elements = self.wait.until(
                EC.presence_of_all_elements_located((By.XPATH, li_xpath)))
            new_store_count = len(store_elements)

            if store_count == new_store_count:
                break
            store_count = new_store_count
            self.driver.execute_script(
                "arguments[0].scrollIntoView(true);", store_elements[-1])

        for i in range(1, store_count + 1):
            print("="*3+f"{i} 번째 매장" + "="*3)
            self.get_into_store(i=i)
            if self.get_store_details():
                self.insert_into_dataframe()

    # searchIframe으로 이동

    def move_to_search_iframe(self):
        self.driver.switch_to.default_content()
        self.wait.until(EC.presence_of_element_located(
            (By.XPATH, self.empty_root)))
        self.wait.until(EC.frame_to_be_available_and_switch_to_it(
            (By.XPATH, self.search_iframe)))
        self.wait.until(EC.presence_of_element_located(
            (By.XPATH, self.empty_searchIframe)))

    # 다음 페이지로 이동
    def move_to_next_page(self):
        self.driver.switch_to.default_content()
        self.wait.until(EC.presence_of_element_located(
            (By.XPATH, self.empty_root)))
        self.wait.until(EC.frame_to_be_available_and_switch_to_it(
            (By.XPATH, self.search_iframe)))

        nextpage_xpath = """//a[span[contains(text(),'다음페이지')]]"""
        next_page_button = self.wait.until(
            EC.presence_of_element_located((By.XPATH, nextpage_xpath)))

        # 다음페이지 존재 여부 확인
        aria_disabled = next_page_button.get_attribute("aria-disabled")
        if aria_disabled == "true":
            return False
        else:
            next_page_button.click()
            time.sleep(2)
            return True


if __name__ == "__main__":

    location = "가로수길"
    keyword = "맛집"
    search_word = location + " " + keyword

    # 서울 지역의 핫스팟 area 정보 불러오기
    seoul_hotspots = load_seoul_hotspots()

    # 음식 키워드 여부
    is_food = False
    blue_ribbon_data = None
    if keyword == "맛집":
        is_food = True
        blue_ribbon_crawler = BlueRibbonCrawler(location=location)
        blue_ribbon_crawler.crawling()
        blue_ribbon_data = blue_ribbon_crawler.data

    # crawler = DatePopCrawler(location=location, keyword= keyword, hotspots=seoul_hotspots, is_food=is_food, crawl_new=False, blue_ribbon=blue_ribbon_data)
    # crawler.search_keyword()

    # for page in range(1, 7):
    #     print("="*10+f"page {page}"+ "="*10)
    #     crawler.crawling_one_page()
    #     time.sleep(1)

    #     print(crawler.data)

    #     # 마지막 페이지인 경우
    #     if crawler.move_to_next_page() == False:
    #         break

    # crawler.driver.quit()

    print("새로오픈 매장 크롤링 시작")

    # 동일 검색어로 신규오픈 매장 크롤링
    crawler_new = DatePopCrawler(location=location, keyword=keyword, hotspots=seoul_hotspots,
                                 is_food=is_food, crawl_new=True, blue_ribbon=blue_ribbon_data)
    crawler_new.search_keyword()
    crawler_new.click_option_new_store()

    for page in range(1, 7):
        print("="*10+f"page {page}" + "="*10)
        crawler_new.crawling_one_page()
        time.sleep(1)

        # 마지막 페이지인 경우
        if crawler_new.move_to_next_page() == False:
            print(crawler_new.data)
            break
        print(crawler_new.data)
    print(f"Crawling for {location} {keyword} is done.")
