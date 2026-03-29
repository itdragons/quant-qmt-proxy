"""
data_ex 扩展行情数据模型（对应 xtdata.get_market_data_ex）
"""
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator


class MarketDataExRequest(BaseModel):
    """获取历史行情与实时行情请求（get_market_data_ex）"""
    stock_list: Optional[List[str]] = Field(..., description="合约代码列表，格式 'code.market'，如 '000001.SZ'")
    field_list: Optional[List[str]] = Field(None, description="字段列表")
    period: str = Field(default="1d", description=(
        "数据周期，K线: tick/1m/5m/15m/30m/1h/1d/1w；"
        "特殊周期: stoppricedata/snapshotindex/limitupperformance/"
        "transactioncount1m/transactioncount1d/orderflow1m/orderflow5m/"
        "orderflow15m/orderflow30m/orderflow1h/orderflow1d/"
        "interactiveqa/northfinancechange1m/northfinancechange1d"
    ))
    start_time: str = Field(default="", description="开始时间，格式 YYYYMMDD 或 YYYYMMDDHHMMSS，空字符串表示最早可用")
    end_time: str = Field(default="", description="结束时间，格式 YYYYMMDD 或 YYYYMMDDHHMMSS，空字符串表示最新可用")
    count: int = Field(default=-1, description="数据条数，-1 表示全部数据")
    dividend_type: str = Field(default="front_ratio", description="复权类型: none/front/back/front_ratio/back_ratio")
    fill_data: bool = Field(default=True, description="是否填充缺失数据")
    disable_download: bool = Field(False, description="是否禁用下载功能")

    @field_validator('stock_list')
    def validate_stock_list(cls, v):
        if not v:
            raise ValueError('合约代码列表不能为空')
        return v

    @field_validator('start_time', 'end_time')
    def validate_time_format(cls, v):
        if v == '':
            return v
        if (len(v) != 8 and len(v) != 14) or not v.isdigit():
            raise ValueError('时间格式必须为 YYYYMMDD 或 YYYYMMDDHHMMSS')
        return v

    @field_validator('dividend_type')
    def validate_dividend_type(cls, v):
        allowed = {"none", "front", "back", "front_ratio", "back_ratio"}
        if v not in allowed:
            raise ValueError(f'复权类型必须是 {", ".join(sorted(allowed))} 之一')
        return v


class MarketDataExResponse(BaseModel):
    """获取历史行情与实时行情响应（列式结构）

    data 为列式格式：
      {
        "000001.SZ": {
          "time":   ["20240101", "20240102", ...],
          "open":   [10.1, 10.2, ...],
          "close":  [10.3, 10.4, ...],
          ...
        }
      }
    列式结构比行式（List[Dict]）JSON 体积减少约 60%，
    客户端可直接 pd.DataFrame(data["000001.SZ"]) 重建 DataFrame。
    """
    data: Dict[str, Dict[str, List[Any]]] = Field(..., description="各合约列式行情数据，key 为合约代码")
    period: str = Field(..., description="数据周期")
    field_list: List[str] = Field(..., description="实际返回的字段列表")