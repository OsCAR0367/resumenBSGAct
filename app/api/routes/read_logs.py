from fastapi import APIRouter

from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder

from app.core.utils.read_jsonl_files import read_jsonl_files

router = APIRouter()


@router.get("filter")
async def filter_logs(key: str, value: str):
    try:
        datos = read_jsonl_files(key, value)

        json_compatible = jsonable_encoder(
            datos
        )
        return JSONResponse(content=json_compatible, media_type="application/json; charset=utf-8")

    except Exception as e:
        respuesta = {
            "message": "Ha ocurrido un error. Intenta nuevamente más tarde.",
            "success": False,
            "data": None
        }

        json_compatible = jsonable_encoder(respuesta)
        return JSONResponse(
            content=json_compatible,
            status_code=500,
            media_type="application/json; charset=utf-8"
        )
