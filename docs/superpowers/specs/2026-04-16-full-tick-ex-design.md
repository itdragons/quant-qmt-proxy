# Full Tick Ex 接口设计文档

**日期**：2026-04-16  
**状态**：已确认  

---

## 背景

项目已有 `POST /api/v1/data/full-tick`（由 `DataService` 提供），返回行式 Pydantic `TickData` 模型列表。  
本需求在 `data_ex` 模块（`/api/v1/data-ex/`）新增同等功能的端点，采用列式格式，与 `get_market_data_ex` 保持一致，减少 JSON 体积，客户端可直接用 `pd.DataFrame` 重建。

---

## 目标

在以下三个文件中各增加内容，实现 `POST /api/v1/data-ex/full-tick` 端点：

| 文件 | 新增内容 |
|------|---------|
| `app/models/data_ex_models.py` | `FullTickExRequest`、`FullTickExResponse` |
| `app/services/data_ex_service.py` | `DataExService.get_full_tick()`、`DataExService._format_full_tick()` |
| `app/routers/data_ex.py` | `POST /full-tick` 路由 |

---

## 返回格式（列式，B 方案）

每个字段值用列表包装（长度为 1），与 `MarketDataExResponse` 类型一致：

```json
{
  "data": {
    "000001.SZ": {
      "time":      [1713234567000],
      "lastPrice": [10.5],
      "open":      [10.2],
      "high":      [10.8],
      "low":       [10.1],
      "lastClose": [10.3],
      "amount":    [123456789.0],
      "volume":    [1000000],
      "pvolume":   [900000],
      "stockStatus": [0],
      "openInt":   [0],
      "lastSettlementPrice": [0.0],
      "askPrice":  [[10.51, 10.52, 10.53, 10.54, 10.55]],
      "bidPrice":  [[10.49, 10.48, 10.47, 10.46, 10.45]],
      "askVol":    [[100, 200, 300, 400, 500]],
      "bidVol":    [[150, 250, 350, 450, 550]],
      "transactionNum": [5000]
    }
  }
}
```

**多档字段处理（B3）**：`askPrice`、`bidPrice`、`askVol`、`bidVol` 本身是列表，包装后变为 `[[...]]`，原样透传，不拆散为独立字段。

---

## 模型设计

### `FullTickExRequest`

```python
class FullTickExRequest(BaseModel):
    stock_list: List[str] = Field(..., description="合约代码列表，格式 'code.market'")

    @field_validator('stock_list')
    def validate_stock_list(cls, v):
        if not v:
            raise ValueError('合约代码列表不能为空')
        return v
```

### `FullTickExResponse`

```python
class FullTickExResponse(BaseModel):
    data: Dict[str, Dict[str, List[Any]]] = Field(
        ..., description="各合约列式 tick 数据，key 为合约代码"
    )
```

`data` 类型与 `MarketDataExResponse.data` 一致，客户端可统一处理。

---

## 服务层设计

### `DataExService.get_full_tick(stock_list)`

- 调用 `xtdata.get_full_tick(stock_list)`
- 调用 `_format_full_tick(raw)` 格式化
- Mock 模式：返回 `{code: {} for code in stock_list}`

### `DataExService._format_full_tick(raw)`

```
输入：{stock_code: {field: scalar_or_list, ...}}
输出：{stock_code: {field: [scalar_or_list], ...}}
```

核心逻辑：`{field: [val] for field, val in tick.items()}`，一行完成所有字段包装。

---

## 路由设计

```
POST /api/v1/data-ex/full-tick
Tag: 扩展行情数据
Auth: Bearer token / ?api_key=
Request body: FullTickExRequest
Response: FullTickExResponse
```

异常处理与现有 `/api/v1/data-ex/market` 完全一致。

---

## 不涉及范围

- 不修改现有 `DataService.get_full_tick`（`/api/v1/data/full-tick` 保持不变）
- 不修改 `dependencies.py`（复用现有 `get_data_ex_service` 单例）
- 不新增测试文件（超出本次需求范围）
