# 📈 股票持仓管理系统

一个简洁的个人股票持仓管理工具，支持港股 & 美股，所有金额统一换算为港币 (HKD)。

## 功能特点

- **多市场支持**：港股 (HK) + 美股 (US)
- **实时价格**：通过 yfinance 获取实时股票价格
- **自动汇率**：自动获取 USD/HKD 实时汇率
- **统一货币**：所有盈亏、市值、占比均以港币计算
- **数值隐私**：持仓页眼睛开关可隐藏金额、价格、股数、持仓数量和汇率，保留比例；浏览器会记住选择
- **前台展示**：查看持仓汇总、盈亏情况、持仓占比
- **多标签管理**：新增、重命名、删除标签，每只股票可绑定多个标签；前台与后台均展示全部标签按钮，支持单选切换或查看全部，也可筛选未标记持仓
- **后台管理**：添加、编辑、删除股票，刷新实时价格
- **响应式设计**：支持桌面端和移动端
- **无需登录**：个人使用，后台直接编辑

## 技术栈

- **后端**：Python + Flask + yfinance
- **前端**：原生 HTML/CSS/JS（无框架依赖）
- **数据**：JSON 文件存储

## 快速启动

### 1. 安装依赖

```bash
cd backend
pip install -r requirements.txt
```

### 2. 启动服务

```bash
python app.py
```

### 3. 访问

- 前台查看：http://localhost:5000
- 后台管理：http://localhost:5000/admin

## 项目结构

```
stockown/
├── backend/
│   ├── app.py              # Flask 后端服务
│   ├── requirements.txt    # Python 依赖
│   └── data/
│       ├── stocks.json     # 股票数据存储
│       └── price_cache.json # 价格缓存
├── frontend/
│   ├── index.html          # 前台展示页面
│   └── admin.html          # 后台管理页面
└── README.md
```

## API 接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /api/stocks | 获取所有持仓（含盈亏计算） |
| POST | /api/stocks | 添加股票 |
| PUT | /api/stocks/:id | 更新股票 |
| DELETE | /api/stocks/:id | 删除股票 |
| POST | /api/refresh-prices | 刷新所有股票实时价格 |
| POST | /api/refresh-exchange-rate | 刷新 USD/HKD 汇率 |
| POST | /api/stocks/batch-update-price | 批量手动更新价格 |

## 股票代码格式

| 市场 | 格式 | 示例 |
|------|------|------|
| 港股 | 4位数字 | 0700（腾讯）、9988（阿里） |
| 美股 | 英文代码 | AAPL（苹果）、TSLA（特斯拉） |

## 标签系统

首次读取持仓时，旧 `type` 字段会自动迁移为 `tag_ids`，标签保存在 `backend/data/tags.json`。
删除标签会解除所有持仓关联，保留持仓本身；标签名称不可重复，最多 40 个字符。
筛选标签为单选，点击其他标签直接切换，点击「全部」恢复全部持仓；每只股票仍可绑定多个标签。
筛选后的汇总和持仓占比按当前结果计算。标签分布允许重叠，占比合计可能超过 100%。

- `GET /api/tags`：获取标签及关联持仓数量。
- `POST /api/tags`：创建标签，JSON 为 `{"name": "半导体"}`。
- `PUT /api/tags/:id`：重命名标签。
- `DELETE /api/tags/:id`：删除标签并移除关联。
- 新增、编辑股票时通过 `tag_ids` 数组分配标签，空数组表示未标记。

运行回归测试：`venv/bin/python -m unittest discover -s tests -v`。
