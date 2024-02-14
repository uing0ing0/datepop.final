from celery import Celery
from celery.schedules import crontab

app = Celery('eagle-eye',
             broker="amqp://guest:guest@localhost:5672",
             backend="rpc://",
             include=['eagle_eye.tasks'])

app.conf.update(
    result_expires=3600,
    timezone='Asia/Seoul',
)
app.conf.beat_schedule = {}

day_of_week = 'wednesday'  # 실행할 요일
hour = 13  # 실행할 시간
minute = 13  # 실행할 분

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
