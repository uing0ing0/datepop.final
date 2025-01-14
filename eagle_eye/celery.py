from celery import Celery
from celery.schedules import crontab

app = Celery('eagle-eye',
             broker="amqp://guest:guest@rabbitmq:5672",
             backend="rpc://",
             include=['eagle_eye.tasks'])

app.conf.update(
    result_expires=3600,
    timezone='Asia/Seoul',
    task_time_limit=43200,  # 태스트가 12시간 내로 완료되지 않으면, 해당 태스크 강제 종료 + 예외 발생
)
app.conf.beat_schedule = {}


crawling_dict_list = [
    {
        "location": "강남역",
        "keywords": ["맛집", "공방", "만화카페", "커플 스튜디오", "동물카페"]
    },
    {
        "location": "가로수길",
        "keywords": ["맛집", "공방", "만화카페", "커플 스튜디오", "동물카페"]
    },
    {
        "location": "대학로",
        "keywords": ["맛집", "공방", "만화카페", "커플 스튜디오", "동물카페", "연극"]
    },
    {
        "location": "홍대",
        "keywords": ["맛집", "공방", "만화카페", "커플 스튜디오", "동물카페", "연극"]
    },
    {
        "location": "연남동",
        "keywords": ["맛집", "공방", "만화카페", "커플 스튜디오", "동물카페"]
    },
]

# 월요일 오전 9시
day_of_week = '1'  # 실행할 요일(1부터 7까지 월요일~일요일)
hour = 9  # 실행할 시간
minute = 0  # 실행할 분

for idx, item in enumerate(crawling_dict_list, start=1):
    task_name = f'crawl_and_score_{item["location"]}_every_week'
    app.conf.beat_schedule[task_name] = {
        'task': 'eagle_eye.tasks.crawl_and_score',  # 태스트 함수 경로 지정
        'schedule': crontab(day_of_week=day_of_week, hour=hour, minute=minute),
        'args': (item['location'], item['keywords']),  # 태스크 함수에 전달할 인자 설정
    }

if __name__ == "__main__":
    app.start()

# 터미널 1에서
# brew services start rabbitmq
# celery -A eagle_eye worker --loglevel=info --concurrency=4
# 터미널 2에서
# celery -A eagle_eye beat --loglevel=info
