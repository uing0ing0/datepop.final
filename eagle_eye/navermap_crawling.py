# 셀레니움 및 드라이버 모듈

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
import os
from datetime import datetime
from urllib.parse import urlparse, parse_qs
from shapely.geometry import Point
import time
import re
import logging

# 각종 util 함수
from eagle_eye.utils.get_instagram_link import get_instagram_link
from eagle_eye.utils.is_within_date import is_within_one_month, is_within_two_weeks
from eagle_eye.utils.convert_str_to_number import convert_str_to_number
from eagle_eye.utils.haversine import haversine
from eagle_eye.utils.load_bluer import load_bluer
from eagle_eye.utils.load_hotspots import load_hotspots


def crawling_one_keyword(location, keyword):

    # 로그 디렉토리 설정
    log_directory = os.path.join(os.getcwd(), 'log')
    if not os.path.exists(log_directory):
        os.makedirs(log_directory)

    current_time = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    log_file_path = os.path.join(log_directory, f"firefox_driver_{location}_{
        keyword}_crawling_{current_time}.log")
    logging.basicConfig(filename=log_file_path, level=logging.INFO)

    # 핫스팟 정보를 load
    # 현재는 서울에 대한 핫스팟 정보만 있음
    seoul_hotspots = load_hotspots('seoul_hotspots.csv')
    try:
        search_word = location + " " + keyword
        logging.info(f"{search_word} 크롤링 시작")

        # 음식 크롤링 여부
        is_food = False
        bluer_data = None
        if keyword == "맛집":
            is_food = True

            # 기본적으로 서울을 기준으로 블루리본서베이 등재 여부를 확인
            # 만약 서울 외의 지역을 크롤링할 예정이라면, 그 지역에 맞는 csv 파일을 load해야함
            bluer_data1 = load_bluer("서울 강남_bluer.csv")
            bluer_data2 = load_bluer("서울 강북_bluer.csv")
            bluer_data = pd.concat(
                [bluer_data1, bluer_data2], ignore_index=True)
            del bluer_data1
            del bluer_data2

        # 검색어에 대한 크롤링 진행
        try:
            crawler = DatePopCrawler(location=location, keyword=keyword, hotspots=seoul_hotspots,
                                     is_food=is_food, crawl_new=False, blue_ribbon=bluer_data)
            crawler.crawling()
        # session이 죽어서 크롤링이 종료된 경우, 크롤링이 진행된 부분까지만 데이터 저장
        except InvalidSessionIdException as e:
            logging.warning("Invalid Session Id로 인해 크롤링 에러 발생")
            logging.warning(e)
        except Exception as e:
            logging.warning(f"크롤링 중 예상하지 못한 에러 발생. 원인 파악 요먕: {e}")

        # 중복 크롤링 매장 삭제
        crawler_data_unique = crawler.data.drop_duplicates(
            subset='store_id', keep='first')

        # "맛집" keyword일 경우에만 신규매장을 겨냥한 크롤링 추가 진행
        if keyword == "맛집":

            logging.info("신규매장 크롤링 시작")
            # 동일 검색어로 신규오픈 매장 크롤링
            try:
                crawler_new = DatePopCrawler(location=location, keyword=keyword, hotspots=seoul_hotspots,
                                             is_food=is_food, crawl_new=True, blue_ribbon=bluer_data)
                crawler_new.crawling()
            except InvalidSessionIdException as e:
                logging.warning("Invalid Session Id로 인해 크롤링 에러 발생")
                logging.warning(e)
            except Exception as e:
                logging.warning(f"신규매장 크롤링 중 예상하지 못한 에러 발생. 원인 파악 요먕: {e}")
            # 중복 크롤링 매장 제거
            crawler_new_data_unique = crawler_new.data.drop_duplicates(
                subset='store_id', keep='first')
            merged_data = pd.concat(
                [crawler_data_unique, crawler_new_data_unique])
            merged_data = merged_data.drop_duplicates(
                subset='store_id', keep='first')
        else:
            merged_data = crawler_data_unique

        # index 초기화 후, 중복 크롤링 매장 제거
        merged_data.reset_index(inplace=True)
        merged_data.drop(columns="index", inplace=True)

        logging.info(f"{location}{keyword}에 대한 크롤링 종료")
        logging.info(f"{location}{keyword} 크롤링 매장 개수: {len(merged_data)}")

        return merged_data

    except Exception as e:
        logging.warning(f"crawling_one_keyword에서 에러 발생: {e}")
        return False


# 한 검색어에 대한 크롤링 모델
class DatePopCrawler:
    # 크롤링되는 features 리스트
    columns = ['store_id', 'name', 'category', 'is_food', 'new_store', 'instagram_link', 'instagram_post', 'instagram_follower', 'hot_spot',
               'visitor_review_count', 'blog_review_count', 'distance_from_subway', 'on_tv', 'parking_available', 'no_kids',
               'seoul_michelin', 'age-2030', 'gender-balance', 'on_blue_ribbon', 'image_urls', 'running_well', 'address', 'phone', 'gps']

    def __init__(self, location: str, keyword: str, hotspots, is_food: bool, crawl_new: bool, blue_ribbon):
        self.location = location  # 크롤링 지역 ex) 강남역
        self.keyword = keyword  # 크롤링 키워드 ex) 맛집
        self.search_word = location + " " + keyword
        self.is_food = is_food  # "맛집" 키워드 여부
        self.hotspots = hotspots  # 서울 지역의 hospot 지역들의 polygon data
        self.crawl_new = crawl_new  # 신규매장을 겨냥한 크롤링 여부
        self.blue_ribbon = blue_ribbon  # 블루리본 데이터

        # 현재 모델을 사용한 크롤링의 모든 결과들을 임시로 저장하는 변수
        self.data = pd.DataFrame(columns=DatePopCrawler.columns)

        # Iframe 전환용 xpath 변수
        # 네이버지도에서는 Iframe 태그가 정말 많다
        # Iframe 바깥에서는 Iframe 내부에 접근할 수 없기 때문에, frame 전환이 자주 일어난다
        # search Iframe은 검색어 입력 시 나타나는 매장 리스트를 표시하는 Iframe이며
        # entry Iframe은 매장 리스트에서 매장 클릭 시 나타나는 상세 매장 Iframe이다
        self.search_iframe = """//*[@id="searchIframe"]"""
        self.entry_iframe = """//*[@id="entryIframe"]"""
        self.empty_searchIframe = """//*[@id="_pcmap_list_scroll_container"]"""
        self.empty_entryIframe = """//*[@id="app-root"]"""
        self.empty_root = """//*[@id="root"]"""

        # 한 매장에 대한 크롤링 결과를 저장하는 변수
        self.store_dict = None

        # 크롤링 드라이버 설정
        self.driver = self.init_driver()
        # 명시적 대기를 위함
        # 수행하는 작업에 따라 명시적 대기 시간을 달리 함
        self.wait_short = WebDriverWait(self.driver, 2)
        self.wait_medium = WebDriverWait(self.driver, 5)
        self.wait = WebDriverWait(self.driver, 10)

    # 크롬 드라이버 설정

    def init_driver(self):
        logging.info("FireFox Driver Options 설정 중...")

        options = FirefoxOptions()
        # 브라우저 GUI 없이 백그라운드에서 실행하기 위한 headless 모드 설정
        options.add_argument("--headless")
        options.add_argument("lang=ko_KR")
        # /dev/shm 파티션 사용 비활성화, Docker 같은 컨테이너 환경에서 메모리 이슈 해결을 위함
        options.add_argument('--disable-dev-shm-usage')
        # GPU 하드웨어 가속 비활성화, 헤드리스 모드에서 성능 향상을 위함
        options.add_argument('--disable-gpu')
        # 브라우저 캐시 비활성화로 최신 데이터 로드
        options.set_preference("network.http.use-cache", False)
        # 페이지 로딩 속도 향상을 위한 이미지 로딩 비활성화
        # 추후 크롤링 과정에서 매장 이미지 url을 제거할 예정인 경우, 주석처리 제거
        # options.set_preference("permissions.default.image", 2)

        # 크롤링 봇 탐지 회피를 위한 user agent 설정
        options.add_argument(
            'user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:88.0) Gecko/20100101 Firefox/88.0')
        options.add_argument('window-size=1920,1080')

        # 파이어폭스 로깅 설정, 파이어폭스에는 직접 로그 경로를 설정하는 방법이 다를 수 있음
        options.log.level = "trace"

        logging.info("FireFox Driver 초기화 중...")
        # 도커 환경에서 파이어폭스의 드라이버인 geckodriver가 설치되는 절대 경로
        geckodriver_path = '/usr/local/bin/geckodriver'
        service = Service(executable_path=geckodriver_path)
        driver = webdriver.Firefox(options=options, service=service)

        logging.info("네이버지도로 이동 중...")
        driver.get("https://map.naver.com/")  # 네이버지도
        driver.execute_script("window.open('');")  # 인스타그램 검색을 위해 여분의 탭을 열어둠
        driver.switch_to.window(driver.window_handles[0])  # 첫 번째 탭으로 전환

        return driver

    # 검색어를 네이버지도의 검색 field에 입력하고 버튼 클릭
    def search_keyword(self):

        logging.info(f"{self.search_word} 검색어 입력 중...")
        self.move_to_default_content()
        css_selector = ".input_search"
        elem = self.wait.until(EC.presence_of_element_located(
            (By.CSS_SELECTOR, css_selector)))
        # 위 조건에서 input_search element가 presence_of_element_located 조건을 충족하자마자 search_word를 입력하면
        # 가끔씩 검색어가 입력이 되지 않는 이슈 드물게 발생
        # 때문에 직접 sleep을 걸어줌
        time.sleep(0.5)
        elem.send_keys(self.search_word)
        # 검색어 입력 후 곧바로 버튼을 클릭하면, 아무런 결과를 return하지 않는 이슈 드물게 발생
        # 검색엔진이 충분히 실행될 수 있도록 직접 sleep을 걸어줌
        time.sleep(3)
        elem.send_keys(Keys.RETURN)

    # Iframe 내부에 있을 때, 가장 상위의 frame으로 이동
    def move_to_default_content(self):
        self.driver.switch_to.default_content()
        # 이동 후 해당 frame의 빈 element를 클릭하여, 현재 frame이 제대로 이동했음을 확인
        self.wait.until(EC.presence_of_element_located(
            (By.XPATH, self.empty_root)))

    # 한 매장의 크롤링 결과를 저장하는 변수 초기화
    # 한 매장에 대한 크롤링을 마치고, 그 다음 매장을 크롤링 하기 위해 실행
    def init_dictionary(self):
        self.store_dict = {
            "store_id": None,
            "name": None,
            "category": None,
            "is_food": self.is_food,
            "new_store": self.crawl_new,
            "instagram_link": None,
            "instagram_post": None,
            "instagram_follower": None,
            "hot_spot": False,
            "visitor_review_count": None,
            "blog_review_count": None,
            "distance_from_subway": None,
            "on_tv": None,
            "parking_available": None,
            "no_kids": None,
            "seoul_michelin": None,
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
    # "새로오픈" 태그를 가진 매장만을 겨냥한 크롤링 진행 시, 본격적인 매장 크롤링 직전에 실행
    def click_new_option(self):
        time.sleep(1)
        logging.info("새로오픈 태그 클릭")
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
    # 해당 매장에 대한 접근이 정상적으로 이뤄질 경우 True, 그 반대는 False를 return
    # False의 경우, 현 매장은 생략하고 다음 매장에 대한 크롤링을 이어간다
    def get_into_store(self, index) -> bool:
        time.sleep(1)
        try:
            logging.info("매장 접근 시도 중...")

            # 매장의 정보를 저장할 저장할 변수 초기화
            self.init_dictionary()
            # 매장 목록이 있는 search Iframe으로 이동
            self.move_to_search_iframe()

            # 현재 페이지의 index번째 매장 클릭
            store_xpath = f"""//*[@id="_pcmap_list_scroll_container"]/ul/li[{
                index}]//a[.//div[contains(@class, 'place_bluelink')]]"""
            store_element = self.wait.until(
                EC.element_to_be_clickable((By.XPATH, store_xpath)))

            # 매장 목록에서 index 번째의 매장 위치로 스크롤
            self.driver.execute_script(
                "arguments[0].scrollIntoView(true);", store_element)
            # index 번째 매장 클릭
            # 드라이버로 직접 클릭 시, 화면에 보이지 않는 element는 클릭되지 않는 이슈가 있음
            # 때문에 js script를 실행하여 매장 클릭(앞으로 모든 클릭은 해당 방법을 사용함)
            self.driver.execute_script("arguments[0].click()", store_element)

            # entry Iframe에 접근하기위해 상위 frame으로 이동
            time.sleep(2)
            self.move_to_default_content()
            # 매장 정보가 있는 entry Iframe element 선택
            iframe_element = self.wait.until(EC.presence_of_element_located(
                (By.XPATH, self.entry_iframe)))
            # entry Iframe으로 이동하기 전에 선택한 entry Iframe element에서 해당 매장에 대한 네이버플레이스 url 추출 및 저장
            iframe_src = iframe_element.get_attribute('src')
            self.store_dict["naver_url"] = iframe_src
            # 매장의 gps(위도, 경도) 정보, 네이버플레이스 고유 ID 추출 및 저장
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
                logging.warning("Entry Iframe을 찾을 수 없음")
                logging.warning("e")
                return False
            except Exception as e:
                logging.warning("Entry Iframe으로 이동 중 에러 발생")
                logging.warning(e)
                return False

            # 정말 드물게 "요청하신 페이지를 찾을 수 없습니다"라는 메시지와 함께 매장 정보가 표시되지 않는 이슈 발생
            # 이 경우 entry Iframe이 존재하기는 하나, 아무런 정보를 얻을 수 없음
            # 이 때 entry Iframe 내에 존재하는 "새로고침" 버튼 클릭하여 매장 정보 다시 불러올 수 있음
            # 다만, 매번 명시적을 대기를 하며 "새로고침" 버튼이 있는지 확인해야한다는 단점이 있음
            # 이 때문에 한 검색어 당 매장 개수(약 300개) x 3초 = 약 900초(15분)의 딜레이가 발생하게 됨
            # 이를 한 지역으로 확장할 경우, 여러 키워드를 사용해 크롤링을 여러 번 진행허가 때문에 대략 1시간이 넘는 딜레이가 발생
            # 득보다 실이 크기 때문에 주석처리해둔 상태
            # try:
            #     reset_elem = self.wait_short.until(
            #         EC.presence_of_element_located((By.XPATH, """//a[contains(text(), '새로고침')]""")))

            #     self.driver.execute_script("arguments[0].click()", reset_elem)
            #     print("새로고침 발생")
            #     return True
            # except (NoSuchElementException, TimeoutException):  # 매장 정보가 잘 불러와진 경우
            #     return True
        except Exception as e:
            logging.warning("get_into_store 내부에서 예러 발생")
            logging.warning(e)
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
            self.store_dict["image_urls"] = image_urls
        except StaleElementReferenceException:
            # 요소가 stale 상태이면서 첫 번째 시도였을 경우 -> 재시도
            if first_try:
                self.store_dict["image_urls"] = self.get_image_urls(
                    first_try=False)
            else:
                logging.warning("매장 대표사진 url 추출 실패")
                self.store_dict["image_urls"] = []
        except TimeoutException as e:
            try:
                if first_try:
                    self.move_to_tab("홈")
                    self.move_to_tab("사진")
                    self.store_dict["image_urls"] = self.get_image_urls(
                        first_try=False)
                else:
                    logging.warning("매장 대표사진 url 추출 실패")
                    self.store_dict["image_urls"] = []
            except (NoSuchElementException, TimeoutException):
                logging.warning("매장 대표사진 url 추출 실패")
                self.store_dict["image_urls"] = []

    # 한 매장 내에서 특정 탭으로 전환
    # 홈, 리뷰, 사진, 예약 등, 탭 이름을 전달해서 사용
    # 탭 이동 후 직접 time sleep을 사용해 대시한다
    def move_to_tab(self, tab_name):
        tab_xpath = f"""//a[@role='tab' and .//span[text()='{tab_name}']]"""
        tab_element = self.driver.find_element(By.XPATH, tab_xpath)
        self.driver.execute_script("arguments[0].click()", tab_element)
        time.sleep(2)

    # 한 매장에 대한 정보 얻기
    def get_store_details(self):
        time.sleep(1)
        logging.info("매장 정보 크롤링 중...")

        # 매장이 핫스팟에 위치해있는지 확인 및 저장
        # 핫스팟 여부를 먼저 확인하는 건, 최대한 매장 정보 로딩 시간을 확보하기 위함
        # 핫스팟 여부는 매장 정보 로딩과 별개이기 때문에 맨 처음에 넣어도 무관
        try:
            store_point = Point(float(self.store_dict["gps"]["longitude"]), float(
                self.store_dict["gps"]["latitude"]))
            self.store_dict["hot_spot"] = False
            for i in range(len(self.hotspots)):
                polygon = self.hotspots[i]["polygon_area"]
                if polygon.contains(store_point):
                    self.store_dict["hot_spot"] = True
                    break
        except:
            self.store_dict['hot_spot'] = False

        # 매장 이름, 카테고리 추출 및 저장
        try:
            store_name_xpath = """//*[@id="_title"]/div/span"""
            title_element = self.wait_medium.until(EC.presence_of_all_elements_located(
                (By.XPATH, store_name_xpath)))

            self.store_dict['name'] = title_element[0].text
            self.store_dict['category'] = title_element[1].text
        # 드물게 매장 이름을 크롤링하지 못하는 에러 발생
        # 해당 매장 생략하고 다음 매장 크롤링 진행
        except TimeoutException as e:
            logging.warning("매장 이름, 카테고리 에러 발생")
            logging.warning(e)
            return False
        except Exception as e:
            logging.warning("매장 이름, 카테고리 에러 발생")
            logging.warning(e)
            return False

        # 신규매장 여부 확인 및 저장
        # 신규매장을 겨냥한 크롤링이 아닌 경우에만 실행
        if self.crawl_new == False:
            try:
                new_open_xpath = """//*[@id='_title']/div/span[contains(text(), '새로오픈')]"""
                new_open_spans = self.driver.find_element(
                    By.XPATH, new_open_xpath)

                if new_open_spans:
                    self.store_dict["new_store"] = True
                else:
                    pass
            # "새로오픈" 태그가 없는 경우(신규매장이 아닌 경우)
            except NoSuchElementException:
                pass
            except Exception as e:
                logging.warning("새로오픈 태그 클릭 실패")
                logging.warning(e)

        # 방문자 리뷰, 블로그 리뷰 개수 추출 및 저장
        try:
            # 방문자 리뷰
            elem_visitor = self.driver.find_element(
                By.XPATH, value="//a[contains(text(), '방문자리뷰')]")
            visitor_review_count = int(re.findall(
                r'\d+', elem_visitor.text.replace(",", ""))[0])
            self.store_dict['visitor_review_count'] = visitor_review_count
        except NoSuchElementException:
            self.store_dict['visitor_review_count'] = 0
        except Exception as e:
            logging.warning("방문자 리뷰 크롤링 실패")
            logging.warning(e)

        try:
            # 블로그 리뷰
            elem_blog = self.driver.find_element(
                By.XPATH, value="//a[contains(text(), '블로그리뷰')]")
            blog_review_count = int(re.findall(
                r'\d+', elem_blog.text.replace(",", ""))[0])
            self.store_dict['blog_review_count'] = blog_review_count
        except NoSuchElementException:
            self.store_dict['blog_review_count'] = 0
        except Exception as e:
            logging.warning("블로그 리뷰 크롤링 실패")
            logging.warning(e)

        # 도로명주소 추출 및 저장
        try:
            address_xpath = "//strong[contains(.,'주소')]/following-sibling::div/a/span"
            address_elem = self.driver.find_element(By.XPATH, address_xpath)
            address_text = address_elem.text
            if address_text != "":
                self.store_dict["address"] = address_text
        except NoSuchElementException as e:
            self.store_dict["address"] = None
        except Exception as e:
            logging.warning("도로명 주소 크롤링 실패")
            logging.warning(e)
            self.store_dict["address"] = None

        # 매장 전화번호 추출 및 저장
        try:
            phone_xpath = "//strong[contains(.,'전화번호')]/following-sibling::div/span"
            phone_elem = self.driver.find_element(By.XPATH, phone_xpath)
            phone_text = phone_elem.text
            if phone_text != "":
                self.store_dict["phone"] = phone_text
        except NoSuchElementException:
            self.store_dict["phone"] = None
        except Exception as e:
            logging.warning("매장 전화번호 크롤링 실패")
            logging.warning(e)
            self.store_dict["phone"] = None

        # 인스타그램 계정 추출 및 저장
        try:
            # 인스타그램 링크 추출
            elem = self.driver.find_element(
                By.XPATH, value="//a[contains(@href, 'instagram.com')]")
            instagram_url = elem.get_attribute('href')

            result = get_instagram_link(instagram_url)

            # 인스타그램 계정 url이 올바르지 않은 경우
            if result == None:
                self.store_dict['instagram_link'] = None
                self.store_dict['instagram_post'] = None
                self.store_dict['instagram_follower'] = None
            # 올바른 경우
            elif result != None and result != "":
                self.store_dict['instagram_link'] = result
            else:
                self.store_dict['instagram_link'] = None
                self.store_dict['instagram_post'] = None
                self.store_dict['instagram_follower'] = None
        # 매장이 네이버지도에 인스타그램 계정을 등록해두지 않은 경우
        except (NoSuchElementException, TimeoutException) as e:
            self.store_dict['instagram_link'] = None
            self.store_dict['instagram_post'] = None
            self.store_dict['instagram_follower'] = None
        except Exception as e:
            logging.warning("인스타그램 크롤링 실패")
            logging.warning(e)
            self.store_dict['instagram_link'] = None
            self.store_dict['instagram_post'] = None
            self.store_dict['instagram_follower'] = None

        # 서울 미쉐린 가이드 등재 여부 확인 및 저장
        try:
            # "미쉐린 가이드 서울" 텍스트를 포함하는지 여부로 확인
            michelin_xpath = """//div[a[contains(text(), '미쉐린 가이드 서울')]]"""
            self.driver.find_element(By.XPATH, michelin_xpath)
            self.store_dict['seoul_michelin'] = True
        except NoSuchElementException:
            self.store_dict['seoul_michelin'] = False
        except Exception as e:
            logging.warning("서울 미쉐린 가이드 크롤링 실패")
            logging.warning(e)
            self.store_dict['seoul_michelin'] = False

        # 지하철역 출구로부터 거리 추출 및 저장
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
            logging.warning("지하철역으로부터 매장까지 거리 크롤링 실패")
            logging.warning(e)
            self.store_dict["distance_from_subway"] = None

        # 방송 출연 여부 확인 및 저장
        try:
            tv_xpath = """//strong[descendant::span[text()='TV방송정보']]"""
            self.driver.find_element(By.XPATH, tv_xpath)
            self.store_dict['on_tv'] = True
        except NoSuchElementException:
            self.store_dict['on_tv'] = False
        except Exception as e:
            logging.warning("방송 출연 여부 크롤링 실패")
            logging.warning(e)
            self.store_dict['on_tv'] = False

        # 주차 가능, 노키즈존 확인 및 저장
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
            logging.warning("주차, 노키즈존 여부 크롤링 실패")
            logging.warning(e)
            print("주차, 반려동물, 노키즈 에러: ", e)
            self.store_dict["parking_available"] = False
            self.store_dict["no_kids"] = False

        # DataLab: 연령별 / 성별 검색 인기도 확인 및 저장
        try:
            # entryIframe의 "홈" 탭에서 스크롤 끝까지 내려서 모든 컨텐츠 로딩
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
                # "더보기" 버튼이 없는 경우
                pass
            except Exception as e:
                logging.warning("Datalab 더보기 버튼 클릭 에러")
                logging.warning(e)
                print("데이터랩 더보기 버튼 에러: ", e)

            # 20대와 30대가 top 1, 2를 차지하는지 확인 및 저장
            # 20, 30대가 데이트하기에 적합한 매장인지 여부를 확인한다
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

            # 남성의 비율이 55% 이상인지
            # 55% 이상일 경우, 데이트 적합 매장이 아닌 경향성 반영(국밥, 제육, 돈까스 등)
            gender_xpath = """//*[@id="pie_chart_container"]/div/*[local-name()='svg']/*[local-name()='g'][1]/*[local-name()='g'][3]/*[local-name()='g'][4]/*[local-name()='g']/*[local-name()='text'][2]"""
            gender_elements = self.wait_medium.until(
                EC.presence_of_all_elements_located((By.XPATH, gender_xpath)))
            female, male = [round(float(item.text.replace("%", "")), 0)
                            for item in gender_elements]
            if male >= 55:
                self.store_dict["gender-balance"] = False
            else:
                self.store_dict["gender-balance"] = True
        except NoSuchElementException:
            self.store_dict["age-2030"] = False
            self.store_dict["gender-balance"] = False
        except Exception as e:
            logging.warning("DataLab 크롤링 실패")
            logging.warning(e)
            print("데이터랩 에러: ", e)
            self.store_dict["age-2030"] = False
            self.store_dict["gender-balance"] = False

        # 블루리본서베이 등재 여부 확인 및 저장
        # "맛집" 키워드일 때만 실행
        if self.is_food == True:
            # 1. 매장 이름 부분일치 여부 확인
            if self.store_dict["name"].replace(" ", "") in [name.replace(" ", "") for name in self.blue_ribbon["name"].values]:
                # 매장 이름이 부분일치하는 매장 리스트업
                indices = self.blue_ribbon.index[self.blue_ribbon["name"]
                                                 == self.store_dict["name"].replace(" ", "")].tolist()

                # 이름이 부분일치하는 매장에 대해서
                for i, index in enumerate(indices):
                    # (1) 도로명 주소 비교
                    # 띄어쓰기 모두 제거한 상태로 비교
                    # 도로명 주소가 같을 경우, 블루리본서베이 등재 True로 저장
                    address1 = self.store_dict["address"].replace(" ", "")
                    address2 = self.blue_ribbon["address"][index].replace(
                        " ", "")
                    if address1 == address2:
                        self.store_dict["on_blue_ribbon"] = True
                        break

                    # (2) 위도-경도 비교
                    # 매장 이름이 일부 일치하는데, 위도-경도 정보가 50m 이하로 근사할 경우, 블루리본서베이 등재 True로 저장
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
            # 2. 전화번호 일치하는 매장이 있을 경우, 블루리본서베이 등재 True로 저장
            elif self.store_dict["phone"] in [phone for phone in self.blue_ribbon["phone"].values]:
                self.store_dict["on_blue_ribbon"] = True
            else:
                self.store_dict["on_blue_ribbon"] = False
        else:
            self.store_dict['on_blue_ribbin'] = False

        # 현 매장의 운영 상태를 확인 및 저장
        # 방문자 리뷰 작성 일자를 사용한다
        # 최근 10개의 리뷰 중 하나라도 한딜 이전 -> bad(0)
        # 최근 10개의 리뷰가 모두 2주 이내 -> good(2)
        # 나머지 -> soso(1)
        try:
            self.store_dict["running_well"] = 1
            self.move_to_tab('리뷰')

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
        except (TimeoutException, NoSuchElementException) as e:
            # 리뷰탭이 없거나, 리뷰가 없는 경우
            self.store_dict["running_well"] = 1
        except Exception as e:
            logging.warning("최근 방문자 리뷰 크롤링 실패")
            logging.warning(e)
            self.store_dict["running_well"] = 1

        # 대표사진 크롤링
        # entry Iframe 내부에서 "사진" 탭으로 이동하여 해당 매장의 대표 사진 Url 추출 및 저장
        # 간혹, "사진" 탭이 없거나 이미지 로딩이 늦어지는 경우 발생할 수 있음
        # 전자의 경우, image_url을 빈 리스트로 설정
        # 후자의 경우,
        self.store_dict["image_urls"] = []
        try:
            self.move_to_tab("사진")
            self.get_image_urls()
        # 사진 탭이 없는 경우
        except NoSuchElementException as e:
            self.store_dict["image_urls"] = []
        except Exception as e:
            logging.warning("매장 사진 url 크롤링 실패")
            logging.warning(e)

        # 인스타그램 게시글 수, 팔로워 수 추출 및 저장
        if self.store_dict['instagram_link'] != None:  # 인스타그램 계정이 있는 경우에만 실행
            try:
                instagram_embed_url = self.store_dict['instagram_link'] + "/embed"

                # 인스타그랩 탭으로 이동
                self.driver.switch_to.window(self.driver.window_handles[1])
                self.driver.get(instagram_embed_url)

                name_xpath = """/html/body/div/div/div/div/div/div/div/div/div[1]/div[2]/div[1]/a/div"""
                self.wait_medium.until(EC.presence_of_element_located(
                    (By.XPATH, name_xpath)))

                follower_xpath = """/html/body/div/div/div/div/div/div/div/div/div[1]/div[2]/div[3]/span/span[1]/span"""
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
            except Exception as e:
                logging.warning("인스타그램 크롤링 실패")
                logging.warning(e)
                self.store_dict['instagram_link'] = None
                self.store_dict["instagram_follower"] = None
                self.store_dict["instagram_post"] = None

            # 네이버지도 탭으로 복귀
            self.driver.switch_to.window(self.driver.window_handles[0])

        # 한 매장에 대한 크롤링 결과
        logging.info(f"""{self.location} + {self.keyword} | 매장 이름: {self.store_dict["name"]}, 매장 카테고리: {
            self.store_dict["category"]}""")
        self.insert_into_dataframe()

    # 한 매장에 대한 크롤링 결과를 한 키워드에 대한 모든 크롤링 결과를 저장하는 변수에 추가
    def insert_into_dataframe(self):
        new_data = pd.DataFrame([self.store_dict])
        self.data = pd.concat([self.data, new_data], ignore_index=True)

    # 한 페이지 크롤링
    def crawling_single_page(self, page):
        # serach Iframe으로 이동 후, 가장 하단까지 스크롤 다운
        # 이는, 한 페이지의 매장 개수를 얻기 위함
        self.move_to_search_iframe()
        # 한 페이지에 대한 매장 개수 반환 및 현재 페이지 매장 개수 반환
        store_count = self.scroll_to_end()

        logging.info(f"{page} 번째 페이지 크롤링 중...")
        # 반복문을 돌면서, 현재 페이지의 모든 매장의 정보를 크롤링
        for i in range(1, store_count + 1):
            logging.info(f"{page}페이지 {i} 번째 매장 크롤링 중...")
            # 매장 정보 페이지 진입에 실패할 경우, 다음 매장으로 이어서 진행
            if self.get_into_store(index=i) == False:
                continue
            self.get_store_details()

    # 한 페이지에 대한 매장 개수 반환 및 현재 페이지 매장 개수 반환
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
        except (NoSuchElementException, TimeoutException) as e:
            print("매장 정보를 찾을 수 없습니다.")
            logging.warning("매장 목록을 확인할 수 없는 에러 발생")
            logging.warning(e)
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

        # search Iframe으로 이동
        self.move_to_search_iframe()

        nextpage_xpath = """//a[span[contains(text(),'다음페이지')]]"""
        next_page_button = self.wait.until(
            EC.presence_of_element_located((By.XPATH, nextpage_xpath)))

        # 다음페이지 존재 여부 확인
        # 존재하지 않으면 별도의 작업없이 False 반환
        # 존재하면 다음페이지 클릭 후 True 반환
        aria_disabled = next_page_button.get_attribute("aria-disabled")
        if aria_disabled == "true":
            logging.info("마지막 페이지")
            return False
        else:
            logging.info("다음 페이지로 이동")
            next_page_button.click()
            time.sleep(2)
            return True

    # 인기메뉴 탭 크롤링
    def crawl_popular_menu(self):

        logging.info("인기메뉴 탭 크롤링 중...")
        self.click_filter_button()

        # 메뉴 종류 긁어오기
        menu_list_xpath = """//div[@id='modal-root']//div[@id='_popup_menu']/following-sibling::div//span/a"""
        self.wait.until(
            EC.element_to_be_clickable((By.XPATH, menu_list_xpath)))
        elements = self.driver.find_elements(By.XPATH, menu_list_xpath)
        menu_list = [element.text for element in elements].copy()

        logging.info(f"총 {len(menu_list)}개의 메뉴 카테고리 확인")

        # 각 메뉴에 대해 크롤링 진행
        for index, menu in enumerate(menu_list):
            if index != 0:
                self.click_filter_button()

            # 해당 메뉴를 클릭했는데, 결과가 0건인 경우, 다음 메뉴로 이어서 진행
            if self.click_menu_button(menu) == False:
                logging.info(f"{menu} 메뉴 검색 결과 0건임으로 해당 메뉴 생략")
                continue
            time.sleep(2)

            logging.info(f"[{index}/{len(menu_list)}] {menu} 메뉴 크롤링 중...")
            self.crawling_all_pages()

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

        # "결과보기" 버튼 클릭
        submit_xpath = f"""//div[@id='modal-root']//a[contains(text(), '결과보기 ')]"""
        submit_button = self.driver.find_element(By.XPATH, submit_xpath)
        # 검색 결과 0건일 경우, aria-disabled = 'true'임
        # 0건이 아닌 경우 True 반환
        if submit_button.get_attribute('aria-disabled') == 'false':
            self.driver.execute_script("arguments[0].click()", submit_button)
            return True
        else:
            return False

    # 모든 페이지 크롤링
    def crawling_all_pages(self):
        for page in range(1, 7):
            self.crawling_single_page(page)
            # 마지막 페이지인 경우
            if self.move_to_next_page() == False:
                break
            time.sleep(1)

    # 한 키워드에 대한 크롤링 진행
    def crawling(self):
        self.search_keyword()
        if self.crawl_new:
            self.click_new_option()
        self.crawling_all_pages()

        # "맛집" 키워드이면서, 신규매장을 겨냥한 크롤링이 아닌 경우
        # 인기메뉴 탭을 클릭해서, 모든 인기메뉴에 대한 매장들을 전부 크롤링
        if self.keyword == "맛집" and not self.crawl_new:
            self.crawl_popular_menu()

        # 드라이버 종료
        self.driver.quit()

# 크롤링 설정, 필요한 사전 데이터 load, 크롤링 진행 함수
