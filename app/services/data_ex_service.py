"""
扩展行情数据服务（对应 xtdata.get_market_data_ex）
"""
import os
import sys
from typing import Any, Dict, List

from app.utils.logger import logger

# 添加xtquant包到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

try:
    import xtquant.xtdata as xtdata
    XTQUANT_AVAILABLE = True
except ImportError:
    logger.warning("xtquant模块未正确安装")
    XTQUANT_AVAILABLE = False

    class MockModule:
        def __getattr__(self, name):
            def mock_function(*args, **kwargs):
                raise NotImplementedError(f"xtquant模块未正确安装，无法调用 {name}")
            return mock_function

    xtdata = MockModule()

from app.config import Settings, XTQuantMode
from app.models.data_ex_models import MarketDataExRequest
from app.utils.exceptions import DataServiceException


class DataExService:
    """扩展行情数据服务"""

    def __init__(self, settings: Settings):
        self.settings = settings

    def _should_use_real_data(self) -> bool:
        return self.settings.xtquant.mode in [XTQuantMode.DEV, XTQuantMode.PROD]

    def download_history_data(self, request):
        # 先下载历史数据（确保本地有数据）                        
        if not request.disable_download:
            logger.debug("下载历史数据...")
            n = 1
            num = len(request.stock_list)
            for stock_code in request.stock_list:
                print(f"当前正在下载 {stock_code}({request.period}) {n}/{num}")
                xtdata.download_history_data(
                    stock_code=stock_code,
                    period=request.period,
                    start_time=request.start_time,
                    end_time=request.end_time
                )
                n += 1

    def get_market_data_ex(self, request: MarketDataExRequest) -> Dict[str, Dict[str, List]]:
        """获取历史行情与实时行情（xtdata.get_market_data_ex）

        返回列式格式: {stock_code: {"time": [...], "open": [...], ...}}
        """
        try:
            if self._should_use_real_data():
                try:
                    self.download_history_data(request)
                    raw = xtdata.get_market_data_ex(
                        field_list=request.field_list or [],
                        stock_list=request.stock_list,
                        period=request.period,
                        start_time=request.start_time,
                        end_time=request.end_time,
                        count=request.count or -1,
                        dividend_type=request.dividend_type or 'front',
                        fill_data=request.fill_data or True,
                    )
                    logger.debug(f"get_market_data_ex 返回类型: {type(raw)}")
                    return self._format_ex_market_data(raw)
                except Exception as e:
                    logger.error(f"get_market_data_ex 失败: {e}")
                    raise DataServiceException(f"获取行情数据失败: {str(e)}")
            else:
                # Mock 模式：返回空数据
                return {code: [] for code in request.stock_list}
        except DataServiceException:
            raise
        except Exception as e:
            raise DataServiceException(f"获取行情数据失败: {str(e)}")

    def _format_ex_market_data(self, raw: Any) -> Dict[str, Dict[str, List]]:
        """格式化 返回的数据（列式向量化实现）

        xtdata 返回格式: {stock_code: DataFrame(index=time, columns=fields)}

        输出列式格式: {stock_code: {"time": [...], "open": [...], ...}}

        """
        import numpy as np

        result: Dict[str, Dict[str, List]] = {}

        if not isinstance(raw, dict):
            logger.warning(f"返回数据格式异常: {type(raw)}")
            return result

        for stock_code, df in raw.items():
            if df is None or (hasattr(df, 'empty') and df.empty):
                result[stock_code] = {}
                continue

            try:
                col_data: Dict[str, List] = {}
                # 各数据列：按 dtype 选最优路径
                for col in df.columns:
                    arr = df[col].to_numpy()
                    if arr.dtype.kind == 'f':
                        # 浮点列：向量化检测 NaN，并 round 消除浮点精度误差
                        arr = np.round(arr, 4)
                        nan_mask = np.isnan(arr)
                        if nan_mask.any():
                            col_data[col] = [None if m else v for m, v in zip(nan_mask.tolist(), arr.tolist())]
                        else:
                            col_data[col] = arr.tolist()
                    elif arr.dtype.kind == 'O':
                        # 对象列：元素可能是 float 列表，逐元素 round
                        def _round_item(v):
                            if isinstance(v, (list, tuple)):
                                return [round(x, 4) if isinstance(x, float) else x for x in v]
                            return v
                        col_data[col] = [_round_item(v) for v in arr.tolist()]
                    else:
                        # 整型列：直接 tolist()
                        col_data[col] = arr.tolist()
                col_data['time'] = df.index.astype(str).tolist()
                result[stock_code] = col_data
            except Exception as e:
                logger.error(f"格式化 {stock_code} 数据失败: {e}")
                result[stock_code] = {}

        return result
