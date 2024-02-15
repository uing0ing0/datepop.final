from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException, TimeoutException, StaleElementReferenceException, WebDriverException, InvalidSessionIdException

from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from selenium import webdriver
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from selenium.webdriver.firefox.service import Service

import pandas as pd
from urllib.parse import urlparse, parse_qs
from shapely.geometry import Point
import time
import re

from eagle_eye.utils.load_hotspots import load_hotspots
from eagle_eye.utils.load_bluer import load_bluer
from eagle_eye.utils.haversine import haversine
from eagle_eye.utils.convert_str_to_number import convert_str_to_number
from eagle_eye.utils.is_within_date import is_within_one_month, is_within_two_weeks
from eagle_eye.utils.get_instagram_link import get_instagram_link


class DatePopCrawler:
    columns = ['store_id', 'name', 'category', 'is_food', 'new_store', 'instagram_link', 'instagram_post', 'instagram_follower', 'hot_spot',
               'visitor_review_count', 'blog_review_count', 'distance_from_subway', 'on_tv', 'parking_available', 'no_kids',
               'seoul_michelin', 'age-2030', 'gender-balance', 'on_blue_ribbon', 'image_urls', 'running_well', 'address', 'phone', 'gps']

    def __init__(self, location, keyword, hotspots, is_food, crawl_new, blue_ribbon):
        self.location = location  # 크롤링 지역 ex) 강남역
        self.keyword = keyword  # 크롤링 키워드 ex) 맛집
        self.search_word = location + " " + keyword  # 크롤링 검색어 ex) 강남역 맛집

        # hotspots 정보, 나중에 location 값에 따라서 자동으로 해당 지역의 hotspot 정보를 불러오도록 수정 필요
        self.hotspots = hotspots
        self.crawl_new = crawl_new  # 신규매장 크롤링 여부
        self.blue_ribbon = blue_ribbon  # location에 대한 블루리본서베이 매장 정보 리스트

        self.is_food = is_food  # "맛집" 키워드 크롤링인지

        # 크롤링 결과 변수
        self.data = pd.DataFrame(columns=DatePopCrawler.columns)

        # Iframe 전환용 xpath
        self.search_iframe = """//*[@id="searchIframe"]"""
        self.entry_iframe = """//*[@id="entryIframe"]"""
        self.empty_searchIframe = """//*[@id="_pcmap_list_scroll_container"]"""
        self.empty_entryIframe = """//*[@id="app-root"]"""
        self.empty_root = """//*[@id="root"]"""

        # 한 매장에 대한 크롤링값 저장
        self.store_dict = None

        # Chrome driver 세팅
        self.driver = self.init_driver()
        self.wait = WebDriverWait(self.driver, 10)
        self.wait_short = WebDriverWait(self.driver, 2)
        self.wait_medium = WebDriverWait(self.driver, 5)

    # 크롬 드라이버 설정
    def init_driver(self):
        print("파이어폭스 설정")
        # 크롤링 봇 회피
        options = FirefoxOptions()

        options.add_argument("--headless")
        options.add_argument("lang=ko_KR")
        # 파이어폭스에는 '--no-sandbox'와 '--disable-setuid-sandbox' 옵션이 필요 없음
        # 이 옵션은 파이어폭스에는 적용되지 않을 수 있음
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')  # 이 옵션은 파이어폭스에서 필요 없을 수 있음
        # options.set_preference("dom.webdriver.enabled", False)  # 웹드라이버 속성 변경 회피
        # options.add_argument("--incognito")
        options.set_preference("network.http.use-cache", False)  # 캐시 비활성화
        # options.set_preference("permissions.default.image", 2)  # 이미지 로딩 비활성화

        options.add_argument(
            'user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:88.0) Gecko/20100101 Firefox/88.0')
        options.add_argument('window-size=1920,1080')

        # log_directory = os.path.join(os.getcwd(), 'log')
        # current_time = datetime.now()
        # log_file_path = os.path.join(log_directory, f"firefox_driver_{self.location}_{self.keyword}_{current_time}.log")

        # # 파이어폭스 로깅 설정, 파이어폭스에는 직접 로그 경로를 설정하는 방법이 다를 수 있음
        # options.log.level = "trace"

        print("파이어폭스 드라이버 시동")
        geckodriver_path = '/usr/local/bin/geckodriver'  # geckodriver 절대 경로
        service = Service(executable_path=geckodriver_path)
        driver = webdriver.Firefox(options=options, service=service)

        print("네이버지도 열기")
        driver.get("https://map.naver.com/")

        driver.execute_script("window.open('');")
        driver.switch_to.window(driver.window_handles[0])

        return driver

    # 검색어를 input field에 입력 후 클릭
    def search_keyword(self):
        self.move_to_default_content()

        css_selector = ".input_search"
        elem = self.wait.until(EC.presence_of_element_located(
            (By.CSS_SELECTOR, css_selector)))

        time.sleep(0.5)
        elem.send_keys(self.search_word)
        time.sleep(3)
        elem.send_keys(Keys.RETURN)

    def move_to_default_content(self):
        self.driver.switch_to.default_content()
        self.wait.until(EC.presence_of_element_located(
            (By.XPATH, self.empty_root)))

    # 한 매장의 크롤링 정보를 저장하는 변수 초기화
    def init_dictionary(self):
        self.store_dict = {
            "store_id": None,
            "name": "",
            "category": "",
            "is_food": self.is_food,
            "new_store": self.crawl_new,
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
            "seoul_michelin": False,
            "age-2030": None,
            "gender-balance": None,
            "on_blue_ribbon": None,
            "running_well": None,
            "address": None,
            "phone": None,
            "gps": {
                "latitude": None,
                "longitude": None,
            },
            "naver_url": None,
            "image_urls": [],
        }

    # "새로오픈" option 클릭

    def click_new_option(self):
        time.sleep(1)
        self.move_to_search_iframe()
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

    # 한 매장에 대한 페이지 열기
    def get_into_store(self, index):
        time.sleep(1)
        try:
            # 매장의 정보를 저장할 저장할 dictionay 변수 초기화
            self.init_dictionary()
            # 매장 목록이 있는 search Iframe으로 이동
            self.move_to_search_iframe()

            # 현재 페이지의 index번째 매장 클릭
            store_xpath = f"""//*[@id="_pcmap_list_scroll_container"]/ul/li[{
                index}]//a[.//div[contains(@class, 'place_bluelink')]]"""
            elem = self.wait.until(
                EC.element_to_be_clickable((By.XPATH, store_xpath)))
            self.driver.execute_script(
                "arguments[0].scrollIntoView(true);", elem)
            self.driver.execute_script("arguments[0].click()", elem)

            # entry Iframe에 접근하기위해 상위 frame으로 이동
            time.sleep(2)
            self.move_to_default_content()

            # 매장 정보가 있는 entry Iframe으로 이동
            iframe_element = self.wait.until(EC.presence_of_element_located(
                (By.XPATH, self.entry_iframe)))
            # iframe_element = self.driver.find_element(
            #     By.XPATH, self.entry_iframe)

            # entry Iframe으로 실제로 이동하기 전에 해당 매장에 대한 url 얻기
            iframe_src = iframe_element.get_attribute('src')
            self.store_dict["naver_url"] = iframe_src
            # 매장의 위도-경도 / 고유 ID 얻기
            parsed_url = urlparse(iframe_src)
            query_params = parse_qs(parsed_url.query)
            latitude = float(query_params.get('y')[0])
            longitude = float(query_params.get('x')[0])
            self.store_dict["gps"] = {
                "latitude": latitude,
                "longitude": longitude
            }
            path_segments = parsed_url.path.split('/')
            store_id = path_segments[2]
            self.store_dict["store_id"] = store_id

            # entryIframe으로 이동
            try:
                self.driver.switch_to.frame(iframe_element)
                self.wait.until(EC.presence_of_element_located(
                    (By.XPATH, self.empty_entryIframe)))
            except TimeoutException as e:
                print(e)
                print("매장 정보 로딩 실패")
                return False
            except Exception as e:
                print("entryIfram 이동 중 에러")

            # "요청하신 페이지를 찾을 수 없습니다" -> "새로고침" 버튼 클릭하여 매장 정보 다시 불러오기
            try:
                reset_elem = self.wait_short.until(
                    EC.presence_of_element_located((By.XPATH, """//a[contains(text(), '새로고침')]""")))

                self.driver.execute_script("arguments[0].click()", reset_elem)
                print("새로고침 발생")
                return True
            except (NoSuchElementException, TimeoutException):  # 매장 정보가 잘 불러와진 경우
                return True
        except StaleElementReferenceException:
            return False
        except Exception as e:
            print("get_into_store에서 에러 발생")
            print(e)
            return False

    # 대표사진 URL 추출 함수
    def get_image_urls(self, max_images=10, first_try=True):
        images_xpath = """/html/body/div[3]/div/div/div/div[6]/div[4]/div/div/div/div/a"""
        try:
            self.wait_medium.until(EC.element_to_be_clickable(
                (By.XPATH, images_xpath)))
            images_xpath = images_xpath + "/img"
            image_elements = self.driver.find_elements(By.XPATH, images_xpath)
            image_urls = [img.get_attribute('src')
                          for img in image_elements][:max_images]
            return image_urls
        except StaleElementReferenceException:
            # 요소가 stale 상태인 경우
            if first_try:
                return self.get_image_urls(first_try=False)
            else:
                return []
        except TimeoutException as e:
            try:
                if first_try:
                    self.move_to_tab("홈")
                    self.move_to_tab("사진")
                    return self.get_image_urls(first_try=False)
                else:
                    return []
            except (NoSuchElementException, TimeoutException):
                return []

    # 한 매장 내에서 특정 탭으로 전환
    # 홈, 리뷰, 사진, 예약 등, 탭 이름을 전달해서 사용

    def move_to_tab(self, tab_name):

        tab_xpath = f"""//a[@role='tab' and .//span[text()='{tab_name}']]"""

        tab_element = self.driver.find_element(By.XPATH, tab_xpath)
        self.driver.execute_script("arguments[0].click()", tab_element)
        time.sleep(2)

    # 한 매장에 대한 정보 얻기

    def get_store_details(self):
        time.sleep(1)

        # 매장이 핫스팟에 위치해있는지 확인
        # 핫스팟 여부를 먼저 확인하는 건, 최대한 매장 정보 로딩 시간을 확보하기 위해서임
        # 핫스팟 여부는 매장 정보 로딩과 별개이기 때문에 맨 처음에 넣어도 상관없음
        try:
            store_point = Point(float(self.store_dict["gps"]["longitude"]), float(
                self.store_dict["gps"]["latitude"]))
            for i in range(len(self.hotspots)):
                polygon = self.hotspots[i]["polygon_area"]
                if polygon.contains(store_point):
                    self.store_dict["hot_spot"] = True  # default = False
                    break
        except:
            self.store_dict['hot_spot'] = False

        # 매장 정보 로딩을 위한 명시적 대기
        time.sleep(3)

        # 매장 이름, 카테고리
        try:
            store_name_xpath = """//*[@id="_title"]/div/span"""
            elem = self.wait.until(EC.presence_of_all_elements_located(
                (By.XPATH, store_name_xpath)))

            self.store_dict['name'] = elem[0].text
            self.store_dict['category'] = elem[1].text
        # 드물게 매장 이름을 크롤링하지 못하는 에러 발생
        # 해당 매장 생략하고 다음 매장 크롤링 진행
        except TimeoutException as e:
            print("매장 이름, 카테고리 에러: ", e)
            return False
        except Exception as e:
            print("매장 이름, 카테고리 에러: ", e)
            return False

        # 신규 매장 여부
        # 일반 크롤링일 때만 실행
        if self.store_dict["new_store"] == False:
            try:
                new_open_xpath = """//*[@id='_title']/div/span[contains(text(), '새로오픈')]"""
                new_open_spans = self.driver.find_element(
                    By.XPATH, new_open_xpath)

                if new_open_spans:
                    self.store_dict["new_store"] = True
                else:
                    pass
            except NoSuchElementException:
                pass
            except Exception as e:
                print(e)

        # 방문자 리뷰, 블로그 리뷰 개수
        try:
            elem_visitor = self.driver.find_element(
                By.XPATH, value="//a[contains(text(), '방문자리뷰')]")
            visitor_review_count = int(re.findall(
                r'\d+', elem_visitor.text.replace(",", ""))[0])
            self.store_dict['visitor_review_count'] = visitor_review_count
        except NoSuchElementException:
            self.store_dict['visitor_review_count'] = None
        try:
            elem_blog = self.driver.find_element(
                By.XPATH, value="//a[contains(text(), '블로그리뷰')]")
            blog_review_count = int(re.findall(
                r'\d+', elem_blog.text.replace(",", ""))[0])
            self.store_dict['blog_review_count'] = blog_review_count
        except NoSuchElementException:
            self.store_dict['blog_review_count'] = None

        # 도로명주소
        try:
            address_xpath = "//strong[contains(.,'주소')]/following-sibling::div/a/span"
            address_elem = self.driver.find_element(By.XPATH, address_xpath)
            address_text = address_elem.text
            if address_text != "":
                self.store_dict["address"] = address_text
        except NoSuchElementException:
            self.store_dict["address"] = None
        except Exception as e:
            print("도로명주소 에러: ", e)
            self.store_dict["address"] = False

        # 매장 전화번호
        try:
            phone_xpath = "//strong[contains(.,'전화번호')]/following-sibling::div/span"
            phone_elem = self.driver.find_element(By.XPATH, phone_xpath)
            phone_text = phone_elem.text
            if phone_text != "":
                self.store_dict["phone"] = phone_text
        except NoSuchElementException:
            self.store_dict["phone"] = None
        except Exception as e:
            print("전화번호 에러: ", e)
            self.store_dict["phone"] = False

        # 인스타그램 계정 존재 확인
        try:
            elem = self.driver.find_element(
                By.XPATH, value="//a[contains(@href, 'instagram.com')]")
            instagram_url = elem.get_attribute('href')

            result = get_instagram_link(instagram_url)

            if result == False:
                self.store_dict['instagram_link'] = None
                self.store_dict['instagram_post'] = None
                self.store_dict['instagram_follower'] = None
            elif result != None:
                self.store_dict['instagram_link'] = result

        except (NoSuchElementException, TimeoutException) as e:
            self.store_dict['instagram_link'] = None
            self.store_dict['instagram_post'] = None
            self.store_dict['instagram_follower'] = None
        except Exception as e:
            print("인스타그램 에러:", e)
            self.store_dict['instagram_link'] = None
            self.store_dict['instagram_post'] = None
            self.store_dict['instagram_follower'] = None

        # 서울 미쉐린 가이드 등재 여부
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
                self.store_dict["distance_from_subway"] = convert_str_to_number(
                    numbers[-1])
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

        # 주차 가능,노키즈존
        try:
            convenient_xpath = "//strong[descendant::span[text()='편의']]/ancestor::div[1]/div/div"
            elem = self.driver.find_element(By.XPATH, convenient_xpath)
            convenients = elem.text

            for parking in ["주차", "발렛파킹"]:
                if parking in convenients:
                    self.store_dict["parking_available"] = True
                    break

            if "노키즈존" in convenients:
                self.store_dict["no_kids"] = True
        except NoSuchElementException:
            self.store_dict["parking_available"] = False
            self.store_dict["no_kids"] = False
        except Exception as e:
            print("주차, 반려동물, 노키즈 에러: ", e)
            self.store_dict["parking_available"] = False
            self.store_dict["no_kids"] = False

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
            age_elements = self.wait_medium.until(
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
            gender_elements = self.wait_medium.until(
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

        # 블루 리본 등재 여부
        if self.is_food == True:
            if self.store_dict["name"].replace(" ", "") in [name.replace(" ", "") for name in self.blue_ribbon["name"].values]:
                indices = self.blue_ribbon.index[self.blue_ribbon["name"]
                                                 == self.store_dict["name"].replace(" ", "")].tolist()

                for i, index in enumerate(indices):
                    # 1. 도로명 주소 비교
                    # - 띄어쓰기 모두 제거한 상태로 비교
                    address1 = self.store_dict["address"].replace(" ", "")
                    address2 = self.blue_ribbon["address"][index].replace(
                        " ", "")

                    if address1 == address2:
                        self.store_dict["on_blue_ribbon"] = True
                        break
                    # 2. 위도-경도 비교
                    lat1 = float(self.store_dict["gps"]["latitude"])
                    lon1 = float(self.store_dict["gps"]["longitude"])

                    lat2 = float(self.blue_ribbon["latitude"][index])
                    lon2 = float(self.blue_ribbon["longitude"][index])
                    distance = haversine(lat1, lon1, lat2, lon2)
                    if distance <= 50:
                        self.store_dict["on_blue_ribbon"] = True
                        break
                    if i + 1 == len(indices):
                        self.store_dict["on_blue_ribbon"] = False
                        break
            elif self.store_dict["phone"] in [phone for phone in self.blue_ribbon["phone"].values]:
                self.store_dict["on_blue_ribbon"] = True
            else:
                self.store_dict["on_blue_ribbon"] = False
        else:
            self.store_dict['on_blue_ribbin'] = False

        # 방문자 리뷰 작성 일자 크롤링
        try:
            self.store_dict["running_well"] = 1
            self.move_to_tab('리뷰')

            # time.sleep(2)

            latest_xpath = """//a[@role='option' and text()='최신순']"""
            elem = self.wait_medium.until(
                EC.element_to_be_clickable((By.XPATH, latest_xpath)))
            self.driver.execute_script("arguments[0].click()", elem)

            date_xpath = """//div[@class='place_section_content']/ul/li//span[contains(text(), '방문일')]/following-sibling::span"""
            elements = self.wait_medium.until(
                EC.presence_of_all_elements_located((By.XPATH, date_xpath)))
            date_texts = [elem.text for elem in elements]

            for date_text in date_texts:
                if not is_within_one_month(date_text):
                    self.store_dict["running_well"] = 0
                    break

            if self.store_dict['running_well'] == 1:
                self.store_dict['running_well'] = 2
                for date_text in date_texts:
                    if not is_within_two_weeks(date_text):
                        self.store_dict["running_well"] = 1
                        break
        except NoSuchElementException:
            # 리뷰탭이 없거나, 리뷰가 없는 경우
            self.store_dict["running_well"] = 1
        except Exception as e:  # 방문자 리뷰 자체가 적어서 표기가 안 된 매장도 많음
            print("최근 영업 상태에서 예상치 못한 에러 발생")
            print("이슈 내용: ", e)
            self.store_dict["running_well"] = 1

        # 대표사진 크롤링
        self.store_dict["image_urls"] = []
        try:
            self.move_to_tab("사진")
            self.store_dict["image_urls"] = self.get_image_urls()
        except NoSuchElementException as e:
            print("사진 탭 없음")
            self.store_dict["image_urls"] = []

        # 인스타그램 크롤링(게시글 수, 팔로워 수)
        if self.store_dict['instagram_link'] != None:  # 인스타그램 계정이 있는 경우에만 실행
            try:
                instagram_embed_url = self.store_dict['instagram_link'] + "/embed"

                # 인스타그랩 탭으로 이동
                self.driver.switch_to.window(self.driver.window_handles[1])
                self.driver.get(instagram_embed_url)
                # time.sleep(1)

                name_xpath = """/html/body/div/div/div/div/div/div/div/div/div[1]/div[2]/div[1]/a/div"""
                self.wait_medium.until(EC.presence_of_element_located(
                    (By.XPATH, name_xpath)))

                # xpath = """//div[contains(@class, 'EmbedProfile')]//span[contains(text(), '팔로워 ') and contains(text(), '게시물 ')]/span/span"""
                # elements = self.driver.find_elements(By.XPATH, xpath)

                # follower_xpath = """//span[contains(., '팔로워 ')]/span/span"""
                follower_xpath = """/html/body/div/div/div/div/div/div/div/div/div[1]/div[2]/div[3]/span/span[1]/span"""
                # post_xpath = """//span[contains(., '게시물 ')]/span/span"""
                post_xpath = """/html/body/div/div/div/div/div/div/div/div/div[1]/div[2]/div[3]/span/span[2]/span"""

                follower_elem = self.driver.find_element(
                    By.XPATH, follower_xpath)
                post_elem = self.driver.find_element(By.XPATH, post_xpath)

                follower = convert_str_to_number(follower_elem.text)
                post = convert_str_to_number(post_elem.text)
                self.store_dict["instagram_follower"] = follower
                self.store_dict["instagram_post"] = post
            except (NoSuchElementException, TimeoutException, WebDriverException):
                self.store_dict['instagram_link'] = None
                self.store_dict["instagram_follower"] = None
                self.store_dict["instagram_post"] = None

            # 네이버지도 탭으로 복귀
            self.driver.switch_to.window(self.driver.window_handles[0])

        # 한 매장에 대한 크롤링 결과
        print(f"{self.location} + {self.keyword}")
        print(f"매장 이름: {self.store_dict["name"]}, 매장 카테고리: {
              self.store_dict["category"]}")
        self.insert_into_dataframe()

    # 한 매장에 대한 크롤링 정볼르 DataFrame에 Insertion
    def insert_into_dataframe(self):
        new_data = pd.DataFrame([self.store_dict])
        self.data = pd.concat([self.data, new_data], ignore_index=True)

    # 한 페이지 크롤링
    def crawling_one_page(self):
        self.move_to_search_iframe()
        store_count = self.scroll_to_end()

        for i in range(1, store_count + 1):

            print(f"==== {i} 번째 매장 ====")
            if self.get_into_store(index=i) == False:
                continue
            self.get_store_details()

    # 한 페이지에 대한 매장 개수 반환
    def scroll_to_end(self):
        try:
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
            return store_count
        except (NoSuchElementException, TimeoutException):
            print("매장 정보를 찾을 수 없습니다.")
            return 0

    # searchIframe으로 이동
    def move_to_search_iframe(self):
        self.move_to_default_content()
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

    def crawl_popular_menu(self):

        self.click_filter_button()

        # 메뉴 종류 긁어오기
        menu_list_xpath = """//div[@id='modal-root']//div[@id='_popup_menu']/following-sibling::div//span/a"""
        self.wait.until(
            EC.element_to_be_clickable((By.XPATH, menu_list_xpath)))
        elements = self.driver.find_elements(By.XPATH, menu_list_xpath)
        menu_list = [element.text for element in elements].copy()

        # 각 메뉴에 대해 크롤링 진행
        for index, menu in enumerate(menu_list):
            if index != 0:
                self.click_filter_button()

            if self.click_menu_button(menu) == False:
                continue
            time.sleep(2)

            for page in range(1, 7):
                print("="*10+f"page {page}" + "="*10)
                self.crawling_one_page()
                print(self.data)
                # 마지막 페이지인 경우
                if self.move_to_next_page() == False:
                    break
                time.sleep(1)

    # searchIframe의 필터 버튼 클릭
    def click_filter_button(self):
        time.sleep(1)
        self.move_to_search_iframe()
        # "더보기" 버튼 클릭
        filter_xpath = """//a[span[contains(text(),'전체필터')]]"""
        filtter_button = self.wait.until(
            EC.element_to_be_clickable((By.XPATH, filter_xpath)))
        self.driver.execute_script("arguments[0].click()", filtter_button)

    # 메뉴 클릭하고 "결과보기" 버튼 클릭
    def click_menu_button(self, menu_text):
        print("="*15 + f"{menu_text} 크롤링" + "="*15)
        menu_xpath = f"""//div[@id='modal-root']//div[@id='_popup_menu']/following-sibling::div//span/a[text()='{
            menu_text}']"""

        menu_item = self.wait.until(
            EC.element_to_be_clickable((By.XPATH, menu_xpath)))

        self.driver.execute_script("arguments[0].click()", menu_item)

        time.sleep(0.5)

        submit_xpath = f"""//div[@id='modal-root']//a[contains(text(), '결과보기 ')]"""
        submit_button = self.driver.find_element(By.XPATH, submit_xpath)

        # 검색 결과 0건일 경우, aria-disabled = 'true'임
        # 0건이 아닌 경우 True 반환
        if submit_button.get_attribute('aria-disabled') == 'false':
            self.driver.execute_script("arguments[0].click()", submit_button)
            return True
        else:
            return False

    def crawling(self):
        self.search_keyword()
        if self.crawl_new:
            self.click_new_option()
        for page in range(1, 7):
            print("="*10+f"page {page}" + "="*10)
            self.crawling_one_page()
            # 마지막 페이지인 경우
            if self.move_to_next_page() == False:
                break
            time.sleep(1)

        # if self.keyword == "맛집" and not self.crawl_new:
        #     self.crawl_popular_menu()
        self.driver.quit()


def crawling_one_keyword(location, keyword):
    seoul_hotspots = load_hotspots('seoul_hotspots.csv')
    try:
        search_word = location + " " + keyword
        print(f"{search_word} 크롤링 시작")

        # 음식 크롤링 여부
        is_food = False
        bluer_data = None
        if keyword == "맛집":
            is_food = True
            bluer_data1 = load_bluer("서울 강남_bluer.csv")
            bluer_data2 = load_bluer("서울 강북_bluer.csv")

            bluer_data = pd.concat(
                [bluer_data1, bluer_data2], ignore_index=True)

            del bluer_data1
            del bluer_data2

        try:
            crawler = DatePopCrawler(location=location, keyword=keyword, hotspots=seoul_hotspots,
                                     is_food=is_food, crawl_new=False, blue_ribbon=bluer_data)
            crawler.crawling()
        except InvalidSessionIdException as e:
            print(e)
            crawler = DatePopCrawler(location=location, keyword=keyword, hotspots=seoul_hotspots,
                                     is_food=is_food, crawl_new=False, blue_ribbon=bluer_data)
            crawler.crawling()

        crawler_data_unique = crawler.data.drop_duplicates(
            subset='store_id', keep='first')

        if keyword == "맛집1123":

            print("Start to crawl new stores")
            # 동일 검색어로 신규오픈 매장 크롤링
            crawler_new = DatePopCrawler(location=location, keyword=keyword, hotspots=seoul_hotspots,
                                         is_food=is_food, crawl_new=True, blue_ribbon=bluer_data)
            crawler_new.crawling()
            crawler_new_data_unique = crawler_new.data.drop_duplicates(
                subset='store_id', keep='first')
            print(f"Crawling for {location} {keyword} is done.")
            merged_data = pd.concat(
                [crawler_data_unique, crawler_new_data_unique])
            merged_data = merged_data.drop_duplicates(
                subset='store_id', keep='first')
        else:
            merged_data = crawler_data_unique

        merged_data.reset_index(inplace=True)
        merged_data.drop(columns="index", inplace=True)

        print(f"merge하고 중복 제거 후 개수: {len(merged_data)}")

        return merged_data

    except Exception as e:
        print(e)
