import httpx
from ninja import Router

__all__ = ["router"]

router = Router()


@router.get("/")
def image(request):
    # httpx를 이용하여 외부 API 호출하기
    return {"status": "OK"}
