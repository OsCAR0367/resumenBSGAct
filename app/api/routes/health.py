from fastapi import APIRouter
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder

router = APIRouter()


@router.get("")
async def health():
    try:
        respuesta = {
            "success": True,
            "data": None,
            "message": "OK"
        }
        json_compatible = jsonable_encoder(
            respuesta
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
