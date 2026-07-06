# 毕昇微光 RESTful API 接口文档

**Base URL**: `http://<服务器IP>:8001`

## 复制以下命令部署到宝塔服务器

```bash
# 1. SSH 连接服务器后,创建数据库
mysql -u root -p -e "
CREATE DATABASE IF NOT EXISTS bisheng_glimmer CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
"

# 2. 克隆后端代码 (或通过宝塔面板 Git 拉取)
cd /www/wwwroot
git clone https://github.com/penglinghuo-alt/Bi_Sheng_Glimmer.git backend
cd backend

# 3. 修改 .env 中的数据库密码
cp .env .env.example  # 如果需要的话
# 编辑 .env,填写正确的 DB_PASSWORD

# 4. 安装依赖
pip3 install --break-system-packages -r requirements.txt

# 5. 宝塔面板 -> 网站 -> Python 项目管理器 -> 添加项目
#   项目路径: /www/wwwroot/backend
#   启动文件: main.py
#   启动方式: uvicorn
#   端口: 8001
```

---

## 认证接口 (Auth)

### POST /api/auth/login — 用户登录

```bash
curl -X POST http://localhost:8001/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"test_admin","password":"123456"}'
```

Response `200`:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer",
  "user": {
    "id": "a1b2c3d4e5f6",
    "username": "test_admin",
    "email": "test@bisheng.com",
    "avatar": null,
    "bio": "毕昇微光管理员",
    "created_at": "2026-06-18T00:00:00"
  }
}
```

| 字段 | 说明 |
|------|------|
| `username` | 登录用户名 |
| `password` | 密码 |

---

### POST /api/auth/register — 用户注册

```bash
curl -X POST http://localhost:8001/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username":"zhangsan","email":"zs@test.com","password":"123456"}'
```

---

### GET /api/auth/profile — 获取当前用户信息

```bash
curl http://localhost:8001/api/auth/profile \
  -H "Authorization: Bearer <access_token>"
```

### PUT /api/auth/profile — 更新用户信息

```bash
curl -X PUT http://localhost:8001/api/auth/profile \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{"bio":"新个人简介","avatar":"https://example.com/avatar.png"}'
```

---

## 盲文记录接口 (Records) `🔒`

### GET /api/records — 获取记录列表

```bash
curl "http://localhost:8001/api/records?search=语文&page=1&page_size=20" \
  -H "Authorization: Bearer <access_token>"
```

Response:
```json
{
  "total": 3,
  "records": [
    {
      "id": "r1",
      "title": "语文课本 第三单元",
      "source_type": "现场扫描",
      "dot_matrix_width": 32,
      "dot_matrix_height": 48,
      "dot_matrix_data": [[1,0,1,0,...],[0,1,0,1,...]],
      "page_count": 12,
      "created_at": "2026-06-18T10:00:00"
    }
  ]
}
```

| 参数 | 类型 | 说明 |
|------|------|------|
| `search` | string | 按标题模糊搜索,可选 |
| `page` | int | 页码,默认 1 |
| `page_size` | int | 每页条数,默认 20 |

---

### GET /api/records/{record_id} — 获取单条记录详情

```bash
curl http://localhost:8001/api/records/r1 \
  -H "Authorization: Bearer <access_token>"
```

### POST /api/records — 创建新记录

```bash
curl -X POST http://localhost:8001/api/records \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "title":"语文课本 第三单元",
    "source_type":"现场扫描",
    "dot_matrix_width":32,
    "dot_matrix_height":48,
    "dot_matrix_data":[[1,0,1,0],[0,1,0,1]],
    "page_count":12
  }'
```

### PUT /api/records/{record_id} — 重命名记录

```bash
curl -X PUT http://localhost:8001/api/records/r1 \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{"title":"新标题"}'
```

### DELETE /api/records/{record_id} — 删除记录

```bash
curl -X DELETE http://localhost:8001/api/records/r1 \
  -H "Authorization: Bearer <access_token>"
```

---

## 设备管理接口 (Device) `🔒`

### GET /api/device/status — 获取设备状态

```bash
curl http://localhost:8001/api/device/status \
  -H "Authorization: Bearer <access_token>"
```

Response:
```json
{
  "status": "disconnected",
  "status_message": "未连接",
  "device_id": null,
  "use_wifi": false
}
```

状态值: `disconnected` | `connected` | `initializing` | `initialized` | `working` | `printing`

### POST /api/device/connect — 连接/断开设备

```bash
# 连接
curl -X POST http://localhost:8001/api/device/connect \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{"device_id":"ELF2-BLE-001","use_wifi":false}'

# 断开
curl -X POST http://localhost:8001/api/device/connect \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{"device_id":"","use_wifi":false}'
```

### POST /api/device/initialize — 设备初始化

```bash
curl -X POST http://localhost:8001/api/device/initialize \
  -H "Authorization: Bearer <access_token>"
```

### POST /api/device/start — 开始扫描打印

```bash
curl -X POST http://localhost:8001/api/device/start \
  -H "Authorization: Bearer <access_token>"
```

### POST /api/device/stop — 紧急终止

```bash
curl -X POST http://localhost:8001/api/device/stop \
  -H "Authorization: Bearer <access_token>"
```

### POST /api/device/paper-ready — 换纸确认

```bash
curl -X POST http://localhost:8001/api/device/paper-ready \
  -H "Authorization: Bearer <access_token>"
```

---

## 日志接口 (Logs) `🔒`

### GET /api/logs — 获取设备日志

```bash
curl "http://localhost:8001/api/logs?device_id=ELF2&limit=50" \
  -H "Authorization: Bearer <access_token>"
```

### POST /api/logs/upload — 上传设备日志

```bash
curl -X POST http://localhost:8001/api/logs/upload \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{"logs":["[2026-06-18 10:00] BLE connected","[2026-06-18 10:01] Init OK"]}'
```

---

## 项目文件结构

```
backend/
├── main.py              # FastAPI 入口,种子数据,中间件
├── database.py          # MySQL 连接池 (SQLAlchemy + PyMySQL)
├── models.py            # ORM 模型 (User / BrailleRecord / DeviceLog)
├── schemas.py           # Pydantic 请求/响应模型
├── auth_utils.py        # JWT 签发校验,密码哈希
├── .env                 # 环境变量 (数据库密码, JWT密钥)
├── requirements.txt     # Python 依赖
└── api/
    └── routers/
        ├── auth.py      # 登录/注册/个人资料
        ├── records.py   # 盲文记录 CRUD
        ├── device.py    # 设备连接/初始化/打印控制
        └── logs.py      # 设备日志上报查询
```

## MySQL 表结构

```sql
-- users
CREATE TABLE users (
    id VARCHAR(64) PRIMARY KEY,
    username VARCHAR(64) NOT NULL UNIQUE,
    email VARCHAR(128) NOT NULL UNIQUE,
    password_hash VARCHAR(256) NOT NULL,
    avatar VARCHAR(512),
    bio VARCHAR(256) DEFAULT '毕昇微光用户',
    created_at DATETIME,
    updated_at DATETIME
);

-- braille_records
CREATE TABLE braille_records (
    id VARCHAR(64) PRIMARY KEY,
    user_id VARCHAR(64) NOT NULL,
    title VARCHAR(256) NOT NULL,
    source_type VARCHAR(32) NOT NULL,
    dot_matrix_width INT DEFAULT 0,
    dot_matrix_height INT DEFAULT 0,
    dot_matrix_data JSON,
    page_count INT DEFAULT 1,
    created_at DATETIME,
    updated_at DATETIME,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

-- device_logs
CREATE TABLE device_logs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id VARCHAR(64) NOT NULL,
    device_id VARCHAR(64),
    log_content TEXT NOT NULL,
    created_at DATETIME,
    FOREIGN KEY (user_id) REFERENCES users(id)
);
```

## 前端对接配置

在前端 Flutter 项目中将 API 基地址配置为你的服务器 IP:

```dart
// lib/data/services/api_client.dart
static const String baseUrl = 'http://<你的服务器IP>:8001/api';
```

宝塔面板 Python 项目管理器配置:
- 启动文件: `main.py`
- 启动命令: `uvicorn main:app --host 0.0.0.0 --port 8001`
- 端口: `8001` (记得安全组放行此端口)
