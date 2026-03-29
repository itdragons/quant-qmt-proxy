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

    def get_market_data_ex(self, request: MarketDataExRequest) -> Dict[str, Dict[str, List]]:
        """获取历史行情与实时行情（xtdata.get_market_data_ex）

        返回列式格式: {stock_code: {"time": [...], "open": [...], ...}}
        """
        try:
            if self._should_use_real_data():
                try:
                    raw = xtdata.get_market_data_ex(
                        field_list=request.field_list,
                        stock_list=request.stock_list,
                        period=request.period,
                        start_time=request.start_time,
                        end_time=request.end_time,
                        count=request.count or -1,
                        dividend_type=request.dividend_type or 'front',
                        fill_data=request.fill_data or True,
                    )
                    logger.debug(f"get_market_data_ex 返回类型: {type(raw)}")
                    return self._format_result(raw)
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

    def _format_result(self, raw: Any) -> Dict[str, Dict[str, List]]:
        """格式化 get_market_data_ex 返回的数据（列式向量化实现）

        xtdata 返回格式: {stock_code: DataFrame(index=time, columns=fields)}

        输出列式格式: {stock_code: {"time": [...], "open": [...], ...}}

        """
        import numpy as np

        result: Dict[str, Dict[str, List]] = {}

        if not isinstance(raw, dict):
            logger.warning(f"get_market_data_ex 返回数据格式异常: {type(raw)}")
            return result

        for stock_code, df in raw.items():
            if df is None or (hasattr(df, 'empty') and df.empty):
                result[stock_code] = {}
                continue

            try:
                col_data: Dict[str, List] = {}

                # time：索引直接向量化转字符串，无 Python 循环
                col_data['time'] = df.index.astype(str).tolist()

                # 各数据列：按 dtype 选最优路径
                for col in df.columns:
                    arr = df[col].to_numpy()
                    if arr.dtype.kind == 'f':
                        # 浮点列：向量化检测 NaN
                        nan_mask = np.isnan(arr)
                        if nan_mask.any():
                            # arr.tolist() C 层批量转 Python float，再用 bool mask 替换 NaN 位置
                            col_data[col] = [None if m else v for m, v in zip(nan_mask.tolist(), arr.tolist())]
                        else:
                            # 快路径：无 NaN，zero-copy → C 层直接转 Python list
                            col_data[col] = arr.tolist()
                    else:
                        # 整型 / 对象列：直接 tolist()，无需 NaN 处理
                        col_data[col] = arr.tolist()

                result[stock_code] = col_data
            except Exception as e:
                logger.error(f"格式化 {stock_code} 数据失败: {e}")
                result[stock_code] = {}

        return result
