import logging
import httpx
from fastapi import HTTPException

logger = logging.getLogger(__name__)


async def forward(http_client: httpx.AsyncClient, method: str, url: str, **kwargs):
    try:
        if method.upper() == "GET":
            resp = await http_client.get(url, **kwargs)
        elif method.upper() == "POST":
            resp = await http_client.post(url, **kwargs)
        elif method.upper() == "PATCH":
            resp = await http_client.patch(url, **kwargs)
        else:
            raise ValueError(f"unsupported method: {method}")
        
        if resp.status_code >= 400:
            raise HTTPException(status_code=resp.status_code, detail=resp.text)
        
        try:
            return resp.json()
        except Exception:
            return resp.text
    except httpx.RequestError:
        logger.exception("request error")
        raise HTTPException(status_code=502, detail="Upstream service unavailable")
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("forward error")
        raise HTTPException(status_code=502, detail=str(e))
