# MCP 标准化查询接口说明

## 概述

MCP (Model Context Protocol) 查询接口提供结构化的全链路代码分析功能，用于自动生成技术方案。

## API 接口

### 端点

```
POST /api/mcp/query
```

### 请求参数

```json
{
  "project": "yuer-chatroom-service",     // 项目名称（必填）
  "class_fqn": "com.xxx.NobleController", // 类的全限定名（必填）
  "method": "openNoble",                  // 方法名（必填）
  "max_depth": 10                         // 最大查询深度（可选，默认 10）
}
```

### 返回结果

```json
{
  "success": true,
  "message": "查询成功：共找到 6 个内部类、0 个 Dubbo 调用、0 个表",
  "endpoints": [
    {
      "project": "yuer-chatroom-service",
      "class_fqn": "com.yupaopao.chatroom.controller.NobleController",
      "method": "openNoble",
      "path": "/noble/open",
      "http_method": "POST"
    }
  ],
  "internal_classes": [
    {
      "project": "yuer-chatroom-service",
      "class_fqn": "com.yupaopao.chatroom.controller.NobleController",
      "class_name": "NobleController",
      "arch_layer": "Controller"
    }
  ],
  "dubbo_calls": [
    {
      "caller_project": "yuer-chatroom-service",
      "caller_class": "com.yupaopao.chatroom.manager.NobleManager",
      "caller_method": "changeNobleInfo",
      "dubbo_interface": "com.yupaopao.user.api.UserRemoteService",
      "dubbo_method": "updateUserInfo",
      "via_field": "userRemoteService"
    }
  ],
  "tables": [
    {
      "project": "yuer-chatroom-service",
      "mapper_fqn": "com.yupaopao.chatroom.mapper.NobleRecordMapper",
      "mapper_name": "NobleRecordMapper",
      "table_name": "noble_record"
    }
  ],
  "aries_jobs": [
    {
      "project": "yuer-chatroom-service",
      "class_fqn": "com.yupaopao.chatroom.job.NobleExpireJob",
      "class_name": "NobleExpireJob",
      "job_type": "scheduled",
      "cron_expr": "0 0 1 * * ?"
    }
  ],
  "mq_info": [
    {
      "project": "yuer-chatroom-service",
      "class_fqn": "com.yupaopao.chatroom.listener.NobleEventListener",
      "class_name": "NobleEventListener",
      "mq_type": "kafka",
      "topic": "noble-event-topic",
      "role": "consumer",
      "method": "handleNobleEvent"
    }
  ]
}
```

## 返回字段说明

### 1. endpoints（前端用户入口）
- `project`: 项目名称
- `class_fqn`: 类的全限定路径
- `method`: 方法名
- `path`: HTTP 路径
- `http_method`: HTTP 方法（GET/POST/PUT/DELETE）

### 2. internal_classes（涉及的内部类）
- `project`: 项目名称
- `class_fqn`: 类的全限定路径
- `class_name`: 类名
- `arch_layer`: 架构层（Controller/Service/Manager/Repository/Mapper/Entity/Other）

### 3. dubbo_calls（外部 Dubbo 调用）
- `caller_project`: 调用方项目
- `caller_class`: 调用方类
- `caller_method`: 调用方方法
- `dubbo_interface`: Dubbo 接口全路径
- `dubbo_method`: Dubbo 方法名
- `via_field`: 注入字段名

### 4. tables（涉及的数据库表）
- `project`: 项目名称
- `mapper_fqn`: Mapper 的全限定路径
- `mapper_name`: Mapper 名称
- `table_name`: 表名

### 5. aries_jobs（涉及的定时任务）
- `project`: 项目名称
- `class_fqn`: 类的全限定路径
- `class_name`: 类名
- `job_type`: 任务类型（scheduled/delayed）
- `cron_expr`: Cron 表达式（可选）

### 6. mq_info（涉及的 MQ 信息）
- `project`: 项目名称
- `class_fqn`: 类的全限定路径
- `class_name`: 类名
- `mq_type`: MQ 类型（kafka/rocket）
- `topic`: Topic 名称
- `role`: 角色（consumer/producer）
- `method`: 方法名（可选）

## 使用示例

### Python 示例

```python
import requests

response = requests.post(
    "http://localhost:8000/api/mcp/query",
    json={
        "project": "yuer-chatroom-service",
        "class_fqn": "com.yupaopao.chatroom.controller.NobleController",
        "method": "openNoble",
        "max_depth": 10
    }
)

result = response.json()
if result['success']:
    print(f"查询成功: {result['message']}")
    print(f"涉及 {len(result['internal_classes'])} 个内部类")
    print(f"调用 {len(result['dubbo_calls'])} 个外部服务")
    print(f"操作 {len(result['tables'])} 个数据库表")
```

### cURL 示例

```bash
curl -X POST "http://localhost:8000/api/mcp/query" \
  -H "Content-Type: application/json" \
  -d '{
    "project": "yuer-chatroom-service",
    "class_fqn": "com.yupaopao.chatroom.controller.NobleController",
    "method": "openNoble",
    "max_depth": 10
  }'
```

## 前端使用

访问 `http://localhost:3000/mcp` 即可使用可视化界面进行查询。

## 错误处理

### 常见错误

1. **参数不完整**
```json
{
  "success": false,
  "message": "参数不完整：project、class_fqn、method 都是必填项",
  ...
}
```

2. **方法未找到**
```json
{
  "success": false,
  "message": "未找到方法: yuer-chatroom-service.com.xxx.NobleController.openNoble",
  ...
}
```

3. **查询失败**
```json
{
  "success": false,
  "message": "查询失败: 具体错误信息",
  ...
}
```

## 后续扩展

该接口设计为标准化的 MCP 协议，可以：
1. 封装为独立的 MCP 服务器
2. 供其他 AI Agent 调用
3. 集成到技术方案自动生成流程中
