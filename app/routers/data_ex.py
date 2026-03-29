"""
扩展行情数据路由（get_market_data_ex）
"""
from fastapi import APIRouter, Depends, HTTPException, status

from app.dependencies import get_data_ex_service, verify_api_key
from app.models.data_ex_models import MarketDataExRequest, MarketDataExResponse
from app.services.data_ex_service import DataExService
from app.utils.exceptions import DataServiceException, handle_xtquant_exception
from app.utils.logger import logger

router = APIRouter(prefix="/api/v1/data-ex", tags=["扩展行情数据"])


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
        data = data_ex_service.get_market_data_ex(request)
        actual_fields = request.field_list if request.field_list else [
            "time", "open", "high", "low", "close", "volume", "amount"
        ]
        return MarketDataExResponse(
            data=data,
            period=request.period,
            field_list=actual_fields,
        )
    except DataServiceException as e:
        raise handle_xtquant_exception(e)
    except Exception as e:
        logger.error(f"get_market_data_ex 接口异常: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"message": f"获取行情数据失败: {str(e)}"},
        )
