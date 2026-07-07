# 毕昇微光 (BiSheng Glimmer)

面向视障阅读辅助的盲文扫描打印系统。前端 Flutter 跨平台（Android / Web），后端 FastAPI REST API，硬件层支持 MQTT / BLE / WiFi 三模通信。

## 技术栈

| 层 | 技术 | 版本 |
|---|------|------|
| 前端框架 | Flutter + Dart | >=3.0.0 <4.0.0 |
| 状态管理 | Riverpod | ^2.6.1 |
| 路由 | GoRouter | ^14.8.1 |
| HTTP 客户端 | Dio | ^5.4.1 |
| 后端框架 | FastAPI | 0.115.6 |
| 服务器 | Uvicorn | 0.34.0 |
| ORM | SQLAlchemy | 2.0.36 |
| 数据库 | MySQL / SQLite (自动回退) | — |
| 认证 | JWT (python-jose) + passlib | HS256 |
| 硬件通信 | MQTT / BLE (flutter_blue_plus) / WiFi TCP | — |

## 整体链路架构

```
┌─────────────────────────────────────────────────────┐
│                   Flutter App                       │
│                                                     │
│  ┌──────────┐  ┌──────────┐  ┌──────────────────┐  │
│  │ Auth     │  │ Records  │  │ Device/Print     │  │
│  │ Provider │  │ Provider │  │ Manager          │  │
│  └────┬─────┘  └────┬─────┘  └────────┬─────────┘  │
│       │              │                 │             │
│  ┌────┴──────────────┴─────────────────┴──────────┐ │
│  │              API Client (Dio)                   │ │
│  │         baseUrl: http://119.91.119.89:9000      │ │
│  └──────────────────────┬─────────────────────────┘ │
│                         │                           │
│  ┌──────────────────────┴─────────────────────────┐ │
│  │           HardwareManager (单例)               │ │
│  │  ┌─────────┐  ┌─────────┐  ┌──────────────┐   │ │
│  │  │  MQTT   │  │   BLE   │  │  WiFi (TCP)  │   │ │
│  │  └────┬────┘  └────┬────┘  └──────┬───────┘   │ │
│  └───────┼────────────┼──────────────┼────────────┘ │
└──────────┼────────────┼──────────────┼──────────────┘
           │            │              │
     ┌─────┴────────────┴──────────────┴─────┐
     │          硬件板子 (ELF2)              │
     │     JSON 协议: CMD / STATUS           │
     └───────────────────────────────────────┘
           HTTP (REST API)
           │
┌──────────┴──────────────────────────────────────────┐
│                  FastAPI 后端                        │
│                                                     │
│  ┌──────────────┐  ┌──────────────┐                 │
│  │ CORSMiddleware│  │ JWT Auth     │                 │
│  │ (allow all)  │  │ (Bearer)     │                 │
│  └──────────────┘  └──────────────┘                 │
│                                                     │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌───────┐  │
│  │ /api/auth│ │/api/records│ │/api/device│ │/api/  │  │
│  │          │ │          │ │          │ │  logs  │  │
│  └────┬─────┘ └────┬─────┘ └────┬─────┘ └───┬───┘  │
│       └────────────┴────────────┴────────────┘      │
│                         │                           │
│                    SQLAlchemy                        │
│                         │                           │
│              ┌──────────┴──────────┐                │
│              │   MySQL / SQLite    │                │
│              └─────────────────────┘                │
└─────────────────────────────────────────────────────┘
```

## 前后端连接逻辑

### API 通信

前端 `ApiClient` 基于 Dio，`baseUrl` 硬编码为 `http://119.91.119.89:9000`。所有请求自动携带 JWT Bearer Token（从 SharedPreferences 读取 `access_token`）。

| 模块 | 端点 | 鉴权 |
|------|------|------|
| 登录 | POST `/api/auth/login` | 否 |
| 注册 | POST `/api/auth/register` | 否 |
| 用户信息 | GET/PUT `/api/auth/profile` | 是 |
| 头像上传 | POST `/api/auth/avatar` | 是 |
| 头像服务 | GET `/uploads/avatars/{filename}` | 否 |
| 盲文记录 CRUD | GET/POST/PUT/DELETE `/api/records/*` | 是 |
| 设备控制 | GET/POST `/api/device/*` | 是 |
| 日志上传 | GET/POST `/api/logs/*` | 是 |

### 认证流程

```
1. 用户输入用户名密码
2. POST /api/auth/login → 后端验证 sha256_crypt/bcrypt 哈希
3. 返回 { access_token, user } → 前端存入 SharedPreferences
4. 后续请求 Dio 拦截器自动注入 Header: Authorization: Bearer <token>
5. 后端 get_current_user() 解析 JWT → 返回 User 对象
6. Token 过期 → 401 → 前端自动跳转登录页
```

### 密码哈希兼容

后端同时支持 `sha256_crypt` 和 `bcrypt` 两种哈希算法，旧用户无感迁移。

## 硬件板子通信逻辑

### 硬件管理器 (`HardwareManager`)

单例模式，管理三种通信模式：

| 模式 | 实现 | 状态 | 协议 |
|------|------|------|------|
| MQTT (默认) | `MqttCommService` | 骨架 | Broker pub/sub, topic `bisheng/cmd` / `bisheng/status` |
| BLE | `BleCommService` | 骨架 | GATT, Service UUID `0000ffe0`, Char UUID `0000ffe1` |
| WiFi | `WifiCommService` | 骨架 | TCP Socket 直连 |

### JSON 通信协议

**APP → 硬件命令**：

```json
{"type": "CMD_START_PRINT", "payload": {}}
{"type": "CMD_PAUSE_PRINT", "payload": {}}
{"type": "CMD_STOP_PRINT", "payload": {}}
{"type": "CMD_EMERGENCY_STOP", "payload": {}}
```

**硬件 → APP 状态回传**：

```json
{"type": "STATUS_PROGRESS", "payload": {"current": 5, "total": 10, "percentage": 50}}
{"type": "STATUS_ERROR", "payload": {"code": 101, "msg": "缺纸"}}
{"type": "STATUS_CONNECTED", "payload": {}}
{"type": "STATUS_IDLE", "payload": {"message": "设备就绪"}}
```

### 设备状态机

```
disconnected → connecting → connected → initializing → initialized
                                                    ↓
                                              working → printing
                                                 ↓         ↓
                                              stopped   paused
```

### 打印步骤流程

```
idle → turningPage → capturing → recognizing → converting → printing → completed
                                                              ↓
                                                       paused / stopped / error
```

## 数据库

### 表结构

**users** — 用户表

| 字段 | 类型 | 说明 |
|------|------|------|
| id | VARCHAR(64) PK | UUID 前16位 |
| username | VARCHAR(64) UNIQUE | 用户名 |
| email | VARCHAR(128) UNIQUE | 邮箱 |
| password_hash | VARCHAR(256) | sha256_crypt / bcrypt |
| avatar | VARCHAR(512) | 头像路径 `/uploads/avatars/xxx.png` |
| bio | VARCHAR(256) | 个性签名 |
| created_at / updated_at | DATETIME | 自动时间戳 |

**braille_records** — 盲文记录

| 字段 | 类型 | 说明 |
|------|------|------|
| id | VARCHAR(64) PK | UUID |
| user_id | VARCHAR(64) FK | 归属用户 |
| title | VARCHAR(256) | 记录标题 |
| source_type | VARCHAR(32) | "现场扫描" / "本地文件" |
| dot_matrix_data | JSON | 点阵数据 |
| page_count | INT | 页数 |

**device_logs** — 设备日志

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INT PK | 自增 |
| user_id | VARCHAR(64) FK | 归属用户 |
| device_id | VARCHAR(64) | 设备标识 |
| log_content | TEXT | 日志内容 |

### 数据库切换

默认使用 SQLite（零配置）。配置 `.env` 中 `DB_HOST` 和 `DB_USER` 后自动切换 MySQL：

```env
DB_HOST=119.91.119.89
DB_PORT=3306
DB_USER=bisheng_glimmer
DB_PASSWORD=your_password
DB_NAME=bisheng_glimmer
```

## 项目结构

```
├── backend/
│   ├── main.py                  # FastAPI 入口 + 生命周期 + 路由注册
│   ├── database.py              # SQLAlchemy 引擎 + Session
│   ├── models.py                # ORM 模型 (User, BrailleRecord, DeviceLog)
│   ├── schemas.py               # Pydantic 请求/响应模型
│   ├── auth_utils.py            # JWT + 密码哈希 (sha256_crypt/bcrypt)
│   ├── requirements.txt         # Python 依赖
│   ├── .env                     # 环境变量 (不提交)
│   ├── uploads/avatars/         # 头像存储目录
│   └── api/routers/
│       ├── auth.py              # 登录/注册/用户信息/头像
│       ├── records.py           # 盲文记录 CRUD
│       ├── device.py            # 设备状态机控制
│       └── logs.py              # 设备日志
│
├── book_scanner/                # Flutter 前端
│   ├── pubspec.yaml
│   └── lib/
│       ├── main.dart            # 应用入口
│       ├── core/
│       │   ├── constants/       # 枚举 + 硬件配置 + 路由常量
│       │   ├── providers/       # device_provider (全局设备状态)
│       │   ├── routes/          # GoRouter 配置
│       │   ├── theme/           # 亮/暗主题 + 无障碍
│       │   └── utils/           # 日志 + 权限
│       ├── data/
│       │   ├── hardware/        # 硬件通信层 (MQTT/BLE/WiFi)
│       │   ├── models/          # UserModel, BrailleRecord
│       │   └── services/        # ApiClient (Dio)
│       └── features/
│           ├── auth/            # 登录/注册
│           ├── home/            # 首页 + 打印进度
│           ├── profile/         # 个人中心 + 头像
│           └── repository/      # 记录列表 + 预览
│
├── server.py                    # 代理服务器 (反代 + SPA fallback)
├── serve.py                     # 纯静态文件服务器
└── README.md
```

## 启动方式

### 后端

```bash
# 安装依赖
cd backend
pip install -r requirements.txt

# 启动 (默认 SQLite)
uvicorn main:app --host 0.0.0.0 --port 8001

# 使用 MySQL (确保 .env 配置正确)
uvicorn main:app --host 0.0.0.0 --port 8001
```

### 前端

```bash
cd book_scanner
flutter pub get
flutter run -d chrome    # Web
flutter run -d android   # Android
```

### 宝塔面板 (生产)

后端以 Python 项目管理器部署，启动命令：

```
uvicorn main:app --host 0.0.0.0 --port 8001
```

数据库需预先创建：

```sql
CREATE DATABASE bisheng_glimmer CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

## 路由表

### 前端路由

| 路径 | 页面 | 认证 |
|------|------|------|
| `/login` | 登录 | 否 |
| `/register` | 注册 | 否 |
| `/home` | 首页 (扫描打印) | 是 |
| `/repository` | 存储库 | 是 |
| `/profile` | 个人中心 | 是 |
| `/preview?id=xxx` | 记录预览 | 是 |
| `/device-manage` | 设备管理 | 是 |

### 后端 API

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/auth/login` | 登录 |
| POST | `/api/auth/register` | 注册 |
| GET | `/api/auth/profile` | 获取用户信息 |
| PUT | `/api/auth/profile` | 更新用户信息 |
| POST | `/api/auth/avatar` | 上传头像 |
| GET | `/uploads/avatars/{filename}` | 头像文件 |
| GET | `/api/records` | 记录列表 |
| POST | `/api/records` | 创建记录 |
| GET | `/api/records/{id}` | 记录详情 |
| PUT | `/api/records/{id}` | 重命名记录 |
| DELETE | `/api/records/{id}` | 删除记录 |
| GET | `/api/device/status` | 设备状态 |
| POST | `/api/device/connect` | 连接/断开设备 |
| POST | `/api/device/initialize` | 初始化设备 |
| POST | `/api/device/start` | 开始打印 |
| POST | `/api/device/stop` | 紧急停止 |
| POST | `/api/device/paper-ready` | 换纸确认 |
| GET | `/api/logs` | 日志列表 |
| POST | `/api/logs/upload` | 上传日志 |
