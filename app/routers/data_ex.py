"""
扩展行情数据路由（get_market_data_ex）
"""
from fastapi import APIRouter, Depends, HTTPException, status

from app.dependencies import get_data_ex_service, verify_api_key
from app.models.data_ex_models import FullTickExRequest, FullTickExResponse, MarketDataExRequest, MarketDataExResponse
from app.services.data_ex_service import DataExService
from app.utils.exceptions import DataServiceException, handle_xtquant_exception
from app.utils.logger import logger

router = APIRouter(prefix="/api/v1/data-ex", tags=["扩展行情数据"])


@router.post("/full-tick", response_model=FullTickExResponse)
async def get_full_tick_ex(
    request: FullTickExRequest,
    api_key: str = Depends(verify_api_key),
    data_ex_service: DataExService = Depends(get_data_ex_service),
) -> FullTickExResponse:
    """获取全推 tick 数据（get_full_tick）

    返回各合约最新快照，列式格式，key 为合约代码。
    多档字段（askPrice/bidPrice/askVol/bidVol）原样透传。
    """
    try:
        data = data_ex_service.get_full_tick(request.stock_list)
        return FullTickExResponse(data=data)
    except DataServiceException as e:
        raise handle_xtquant_exception(e)
    except Exception as e:
        logger.error(f"get_full_tick 接口异常: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"message": f"获取全推数据失败: {str(e)}"},
        )


@router.post("/market", response_model=MarketDataExResponse)
async def get_market_data_ex(
    request: MarketDataExRequest,
    api_key: str = Depends(verify_api_key),
    data_ex_service: DataExService = Depends(get_data_ex_service),
) -> MarketDataExResponse:
    """获取历史行情与实时行情（get_market_data_ex）

    支持标准 K 线周期（tick/1m/5m/15m/30m/1h/1d/1w）及专属周期
    （stoppricedata/snapshotindex/limitupperformance/transactioncount1m 等）。

    - 历史数据需要提前在本地下载。
    - 实时数据直接从服务端返回。
    - 同时请求时自动拼接历史与实时数据。

    返回 `data` 字段为各合约行情字典，key 为合约代码，value 为行情记录列表。
    """
    try:
        request.field_list = request.field_list or []
        data = data_ex_service.get_market_data_ex(request)
        return MarketDataExResponse(
            data=data,
            period=request.period,
            field_list=request.field_list,
        )
    except DataServiceException as e:
        raise handle_xtquant_exception(e)
    except Exception as e:
        logger.error(f"get_market_data_ex 接口异常: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"message": f"获取行情数据失败: {str(e)}"},
        )
