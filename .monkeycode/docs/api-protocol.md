# 前后端通信协议文档

## 1. 架构概览

```
┌──────────────────────────────────────────────────────────┐
│  浏览器 / Flutter Web                                     │
│  book_scanner/lib/data/services/api_client.dart           │
│  Base URL: http://119.91.119.89:9000                     │
│  Auth: JWT Bearer Token (HS256)                          │
│  HTTP Client: Dio                                         │
└─────────────────────────┬────────────────────────────────┘
                          │ HTTP / HTTPS
                          │
┌─────────────────────────▼────────────────────────────────┐
│  Windows Server (宝塔面板)                                 │
│  C:\wwwroot\backend                                       │
│  FastAPI + Uvicorn  (端口 8001)                            │
│  宝塔反向代理 9000 → 8001                                  │
│  MySQL (SQLAlchemy ORM)                                   │
└──────────────────────────────────────────────────────────┘
```

| 层 | 说明 |
|----|------|
| 前端 base URL | `http://119.91.119.89:9000` |
| 后端监听端口 | `8001` |
| 端口映射 | 宝塔面板反向代理 `:9000 → :8001` |
| 认证 | JWT HS256, 1440 分钟过期, `Authorization: Bearer <token>` |
| 前端 HTTP 库 | Dio (单例) + SharedPreferences 存储 token |

---

## 2. 认证流程

```
注册/登录
  └─ POST /api/auth/login  {username, password}
  └─ 后端验证 sha256_crypt / bcrypt 密码哈希
  └─ 返回 {access_token, token_type, user}
  └─ 前端存入 SharedPreferences ("access_token")
  └─ Dio 拦截器自动注入 Authorization: Bearer <token>

自动登录 (应用启动)
  └─ SharedPreferences 读取 token
  └─ GET /api/auth/profile 验证 token 有效性
  └─ 成功: 状态设为 authenticated
  └─ 失败 (401): 清除 token, 状态 unauthenticated

登出
  └─ 清除 SharedPreferences 中 token
  └─ 状态设为 unauthenticated
```

---

## 3. 全部 API 端点

### 3.1 认证 `/api/auth`

| 方法 | 路径 | 认证 | 说明 |
|------|------|------|------|
| POST | `/api/auth/login` | 否 | 用户登录 |
| POST | `/api/auth/register` | 否 | 用户注册 |
| GET | `/api/auth/profile` | 是 | 获取当前用户信息 |
| PUT | `/api/auth/profile` | 是 | 更新用户资料 |
| POST | `/api/auth/avatar` | 是 | 上传头像 (multipart) |
| GET | `/uploads/avatars/{filename}` | 否 | 获取头像文件 |

#### POST /api/auth/login
```
Request:  { username: "test_admin", password: "123456" }
Response: {
  access_token: "eyJhbG...",
  token_type: "bearer",
  user: { id, username, email, avatar, bio, created_at }
}
```

#### POST /api/auth/register
```
Request:  { username: "zhangsan", email: "zs@test.com", password: "123456" }
Response: { access_token, token_type, user }
```

#### GET /api/auth/profile
```
Headers:  Authorization: Bearer <token>
Response: { id, username, email, avatar, bio, created_at }
```

#### PUT /api/auth/profile
```
Headers:  Authorization: Bearer <token>
Request:  { username?, avatar?, bio? }
Response: { id, username, email, avatar, bio, created_at }
```

#### POST /api/auth/avatar
```
Headers:  Authorization: Bearer <token>
Request:  FormData { file: MultipartFile }
Response: { id, username, email, avatar, bio, created_at }
```

---

### 3.2 盲文记录 `/api/records`

> 所有接口需认证 `Authorization: Bearer <token>`

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/records` | 获取记录列表 (分页, 搜索) |
| GET | `/api/records/{id}` | 获取单条详情 |
| POST | `/api/records` | 创建新记录 |
| PUT | `/api/records/{id}` | 重命名 |
| DELETE | `/api/records/{id}` | 删除 |

#### GET /api/records
```
Query:    ?search=语文&page=1&page_size=20
Response: {
  total: 3,
  records: [{
    id, title, source_type, dot_matrix_width, dot_matrix_height,
    dot_matrix_data: [[int]], page_count, created_at
  }]
}
```

#### GET /api/records/{id}
```
Response: { id, title, source_type, dot_matrix_width, dot_matrix_height, dot_matrix_data, page_count, created_at }
```

#### POST /api/records
```
Request: {
  title: "语文课本",
  source_type: "现场扫描",
  dot_matrix_width: 32,
  dot_matrix_height: 48,
  dot_matrix_data: [[1,0,1],[0,1,0]],
  page_count: 12
}
Response: { id, title, source_type, ... }
```

#### PUT /api/records/{id}
```
Request:  { title: "新标题" }
Response: { id, title, source_type, ... }
```

#### DELETE /api/records/{id}
```
Response: { success: true, message: "记录已删除" }
```

---

### 3.3 设备控制 `/api/device`

> 所有接口需认证

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/device/status` | 获取设备状态 |
| POST | `/api/device/connect` | 连接 / 断开设备 |
| POST | `/api/device/initialize` | 设备初始化 (回零) |
| POST | `/api/device/start` | 开始扫描打印 |
| POST | `/api/device/stop` | 紧急终止 |
| POST | `/api/device/paper-ready` | 换纸确认 |

#### GET /api/device/status
```
Response: {
  status: "disconnected",
  status_message: "未连接",
  device_id: null,
  use_wifi: false
}
```
状态值: `disconnected` | `connected` | `initializing` | `initialized` | `working` | `printing`

#### POST /api/device/connect
```
连接:      { device_id: "ELF2-BLE-001", use_wifi: false }
断开:      { device_id: "", use_wifi: false }
Response:  { success: true, message: "..." }
```

---

### 3.4 日志 `/api/logs`

> 所有接口需认证

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/logs` | 获取设备日志 |
| POST | `/api/logs/upload` | 上传设备日志 |

#### GET /api/logs
```
Query:    ?device_id=ELF2&limit=50
Response: { total: 100, logs: [...] }
```

#### POST /api/logs/upload
```
Request:  { logs: ["[2026-07-01 10:00] BLE connected", ...] }
Response: { success: true, uploaded_count: 2, message: "日志上传成功" }
```

---

### 3.5 健康检查

| 方法 | 路径 | 认证 | 说明 |
|------|------|------|------|
| GET | `/` | 否 | 服务信息 |
| GET | `/api/health` | 否 | `{ status: "healthy" }` |

---

## 4. 数据模型字段对照

### BrailleRecord

| 前端 (Dart) | 后端 (Python/Pydantic) | JSON Key | 类型 |
|-------------|----------------------|----------|------|
| id | id | `id` | String |
| title | title | `title` | String |
| sourceType | source_type | `source_type` | String |
| dotMatrixWidth | dot_matrix_width | `dot_matrix_width` | int |
| dotMatrixHeight | dot_matrix_height | `dot_matrix_height` | int |
| dotMatrixData | dot_matrix_data | `dot_matrix_data` | `List<List<int>>` |
| pageCount | page_count | `page_count` | int |
| createdAt | created_at | `created_at` | DateTime |

> JSON 传输统一使用 **snake_case** 键名。前端 `fromJson`/`toJson` 已对齐后端。

### User

| 前端 (Dart) | 后端 (Python) | JSON Key | 类型 |
|-------------|-------------|----------|------|
| id | id | `id` | String |
| username | username | `username` | String |
| email | email | `email` | String |
| avatar | avatar | `avatar` | String? |
| bio | bio | `bio` | String? |

> User 字段无下划线，两端自动一致。

---

## 5. 前端 API Client 方法一览

文件: `book_scanner/lib/data/services/api_client.dart`

```dart
// Auth
login(username, password)           → POST /api/auth/login
register(username, email, password)  → POST /api/auth/register
getProfile()                         → GET /api/auth/profile
updateProfile({username, avatar, bio}) → PUT /api/auth/profile
uploadAvatar(path, {bytes})          → POST /api/auth/avatar

// Records
getRecords({search, page, pageSize}) → GET /api/records
getRecord(id)                        → GET /api/records/{id}
createRecord(data)                   → POST /api/records
renameRecord(id, title)             → PUT /api/records/{id}
deleteRecord(id)                     → DELETE /api/records/{id}

// Device
getDeviceStatus()                    → GET /api/device/status
connectDevice(id, {useWifi})         → POST /api/device/connect
disconnectDevice()                   → POST /api/device/connect (device_id: "")
initializeDevice()                   → POST /api/device/initialize
startPrint()                         → POST /api/device/start
stopPrint()                          → POST /api/device/stop
paperReady()                         → POST /api/device/paper-ready

// Logs
getLogs({deviceId, limit})           → GET /api/logs
uploadLogs(logs)                     → POST /api/logs/upload

// Token
loadToken()          → SharedPreferences 读取
saveToken(token)     → SharedPreferences 写入
clearToken()         → SharedPreferences 删除
hasToken             → bool 判断
```

---

## 6. Provider 调用关系

```
登录/注册流程:
  AuthNotifier → ApiClient.login() → 存储 token → 状态更新

自动登录:
  main() → AuthNotifier._tryAutoLogin() → ApiClient.loadToken()
        → ApiClient.getProfile() 验证 → 成功/失败

记录列表:
  RepoNotifier → ApiClient.getRecords() → BrailleRecord.fromJson()

设备控制:
  DeviceNotifier → ApiClient.connectDevice() / initializeDevice() / startPrint()
                 + HardwareCommService (MQTT/BLE/WiFi 桩代码)

个人资料:
  ProfileNotifier → ApiClient.getProfile() / updateProfile() / uploadAvatar()
```

---

## 7. 硬件通信 (独立通道)

REST API 之外，设备实时状态通过独立硬件通信通道传输:

| 通道 | 文件 | 状态 |
|------|------|------|
| MQTT | `mqtt_comm_service.dart` | 桩代码 (待接入) |
| BLE | `ble_comm_service.dart` | 桩代码 (待接入) |
| WiFi TCP | `wifi_comm_service.dart` | 桩代码 (待接入) |

三种服务均实现 `IHardwareComm` 接口，通过 `StreamController` 推送消息到 UI。

**JSON 命令协议** (APP → 硬件):
```json
CMD_START_PRINT, CMD_PAUSE_PRINT, CMD_STOP_PRINT, CMD_EMERGENCY_STOP
```

**JSON 状态协议** (硬件 → APP):
```json
STATUS_PROGRESS {current, total, percentage}
STATUS_ERROR {code, msg}
STATUS_IDLE
STATUS_CONNECTED
```

---

## 8. 端口说明

| 端口 | 用途 | 运行位置 |
|------|------|---------|
| 8001 | FastAPI 后端 (uvicorn) | Windows 服务器 |
| 9000 | 宝塔反向代理 (前端连接的入口) | Windows 服务器 |
| 3000 | Flutter Web 开发预览 (可选) | 本地 |

> 前端 `ApiClient.baseUrl = 'http://119.91.119.89:9000'`
> 宝塔面板将 `:9000` 代理到后端 `:8001`，所以前端连 9000 即可。

---

## 9. 认证技术细节

| 项目 | 值 |
|------|-----|
| 算法 | HS256 |
| 密钥 | 来自 `.env` 中 `SECRET_KEY` |
| 过期 | 1440 分钟 (24 小时) |
| 密码哈希 | sha256_crypt (主力), bcrypt (兼容) |
| Token 载体 | `{ sub: username, exp: timestamp }` |
| 前端存储 | SharedPreferences key: `access_token` |
| 鉴权中间件 | `get_current_user()` 依赖注入 |
| 自动注入 | Dio 拦截器 `onRequest` |

---

## 10. 错误处理

| HTTP 状态 | 含义 | 响应体 |
|-----------|------|--------|
| 200 | 成功 | 业务数据 |
| 401 | 未认证 / Token 过期 | `{ detail: "..." }` |
| 404 | 资源不存在 | `{ detail: "..." }` |
| 422 | 参数校验失败 | `{ detail: [...] }` |
| 500 | 服务器内部错误 | `{ detail: "..." }` |

前端处理:
- Dio 拦截器捕获 401 → 不清除 token (由业务层决定)
- 各 Provider 的 try/catch 捕获网络异常 → 设置 error 状态
- 自动登录: profile 失败 → 清除 token, 跳转登录页

---

## 11. 已知问题与修复记录

| 问题 | 状态 | 修复 |
|------|------|------|
| BrailleRecord fromJson 使用 camelCase 键名 | 已修复 | 改为 snake_case: `source_type`, `dot_matrix_width`, `created_at` 等 |
| 端口 9000 vs 8001 | 已说明 | 宝塔面板反向代理 9000→8001 |
| 硬件通信桩代码 | 待接入 | MQTT/BLE/WiFi 三种通道均标记 TODO |
| demo-mock-flow 离线模式 | 正常 | 前端使用 DatabaseHelper 本地数据, 不调 API |
