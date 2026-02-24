# 关系追踪功能说明

## 概述

Python AST 插件现在支持识别和存储以下特殊关系：
1. **Dubbo调用关系** - 识别 `@DubboReference`、`@Reference` 和 `@DubboService`、`@Service` 注解
2. **MQ监听关系** - 识别 `@KafkaListener`、`@RabbitListener` 和 `@RocketMQMessageListener` 注解
3. **MQ发送关系** - 识别 `KafkaTemplate.send()`、`RabbitTemplate.send()` 和 `RocketMQTemplate.send()` 调用
4. **Mapper和表的关系** - 识别 `@Mapper` 注解的接口，并推断对应的数据库表

## 新增的节点类型

### MQTopic 节点
- **属性**:
  - `name`: Topic/Queue名称
  - `mq_type`: MQ类型（KAFKA/RABBITMQ/ROCKETMQ）
  - `group_id`: 消费者组ID（Kafka和RocketMQ）

### Table 节点
- **属性**:
  - `name`: 表名
  - `entity_fqn`: 实体类的FQN（如果可推断）

## 新增的关系类型

### DUBBO_CALLS
- **说明**: 类通过 `@DubboReference` 或 `@Reference` 字段调用Dubbo服务
- **方向**: `Type` → `Type`
- **属性**:
  - `field_name`: 字段名称

**示例**:
```java
public class UserService {
    @DubboReference
    private OrderService orderService;  // 创建 DUBBO_CALLS 关系
    
    @Reference  // 也支持 @Reference (com.alibaba.dubbo.config.annotation.Reference)
    private PaymentService paymentService;  // 创建 DUBBO_CALLS 关系
}
```

### DUBBO_PROVIDES
- **说明**: 类通过 `@DubboService` 或 `@Service` (Dubbo) 注解提供Dubbo服务
- **方向**: `Type` → `Type`
- **说明**: 指向服务接口

**示例**:
```java
@DubboService
public class OrderServiceImpl implements OrderService {  // 创建 DUBBO_PROVIDES 关系
}

@Service  // 也支持 @Service (com.alibaba.dubbo.config.annotation.Service)
public class PaymentServiceImpl implements PaymentService {  // 创建 DUBBO_PROVIDES 关系
}
```

### LISTENS_TO_MQ
- **说明**: 方法监听MQ消息
- **方向**: `Method` → `MQTopic`
- **说明**: 方法通过 `@KafkaListener`、`@RabbitListener` 或 `@RocketMQMessageListener` 监听MQ

**示例**:
```java
@KafkaListener(topics = "activity_award_notify", groupId = "room-service")
public void onMessage(ConsumerRecord<String, String> record) {  // 创建 LISTENS_TO_MQ 关系
}

@RocketMQMessageListener(topic = "order_topic", consumerGroup = "order-group")
public class OrderListener implements RocketMQListener<String> {  // 创建 LISTENS_TO_MQ 关系
}
```

### SENDS_TO_MQ
- **说明**: 方法发送MQ消息
- **方向**: `Method` → `MQTopic`
- **说明**: 方法中调用 `KafkaTemplate.send()`、`RabbitTemplate.send()` 或 `RocketMQTemplate.send()`

**示例**:
```java
public void sendMessage() {
    kafkaTemplate.send("activity_award_notify", message);  // 创建 SENDS_TO_MQ 关系
}

public void sendRocketMQMessage() {
    rocketMQTemplate.send("order_topic:order_tag", message);  // 创建 SENDS_TO_MQ 关系
}
```

### MAPPER_FOR_TABLE
- **说明**: Mapper接口对应的数据库表
- **方向**: `Type` → `Table`
- **说明**: Mapper接口与数据库表的映射关系

**识别规则**:
1. 有 `@Mapper` 注解的接口
2. 接口名以 `Mapper` 结尾
3. 包名包含 `mapper` 且方法参数中包含实体类（domain.db或entity包下的类）

**示例**:
```java
@Mapper
public interface ChatroomHostGuardActiveInfoMapper {  // 推断表名: chatroom_host_guard_active_info
    // 创建 MAPPER_FOR_TABLE 关系
}

// 没有@Mapper注解，但接口名以Mapper结尾
public interface ChatroomInteractionSwitchMapper {  // 推断表名: chatroom_interaction_switch
    int insertSelective(ChatroomInteractionSwitchDO record);
    // 创建 MAPPER_FOR_TABLE 关系
}
```

## 表名推断规则

Mapper接口的表名推断采用以下策略（按优先级）：

1. **从接口名推断**:
   - 去掉 `Mapper` 后缀
   - 驼峰转下划线命名
   - 例如: `ChatroomHostGuardActiveInfoMapper` → `chatroom_host_guard_active_info`

2. **从方法参数推断**:
   - 查找方法参数中的实体类（通常在 `domain.db`、`domain` 或 `entity` 包下）
   - 从实体类名推断表名
   - 去掉 `DO`、`Entity` 等后缀后转下划线
   - 例如: `ChatroomInteractionSwitchDO` → `chatroom_interaction_switch`

3. **从导入的实体类推断**:
   - 查找导入语句中的实体类（`domain.db`、`domain` 或 `entity` 包下的类）
   - 从实体类名推断表名

## 使用示例

### 查询Dubbo调用关系

```cypher
// 查找所有Dubbo调用
MATCH (caller:Type)-[r:DUBBO_CALLS]->(service:Type)
RETURN caller.name, r.field_name, service.name

// 查找某个类调用的所有Dubbo服务
MATCH (caller:Type {fqn: 'com.example.UserService'})-[r:DUBBO_CALLS]->(service:Type)
RETURN service.name, r.field_name
```

### 查询MQ监听关系

```cypher
// 查找所有MQ监听
MATCH (m:Method)-[:LISTENS_TO_MQ]->(topic:MQTopic)
RETURN m.signature, topic.name, topic.mq_type, topic.group_id

// 查找监听特定Topic的方法
MATCH (m:Method)-[:LISTENS_TO_MQ]->(topic:MQTopic {name: 'activity_award_notify'})
RETURN m.signature, m.class_fqn
```

### 查询MQ发送关系

```cypher
// 查找所有MQ发送
MATCH (m:Method)-[:SENDS_TO_MQ]->(topic:MQTopic)
RETURN m.signature, topic.name, topic.mq_type

// 查找发送到特定Topic的方法
MATCH (m:Method)-[:SENDS_TO_MQ]->(topic:MQTopic {name: 'activity_award_notify'})
RETURN m.signature, m.class_fqn
```

### 查询Mapper和表的关系

```cypher
// 查找所有Mapper和表的映射
MATCH (mapper:Type)-[:MAPPER_FOR_TABLE]->(table:Table)
RETURN mapper.fqn, table.name

// 查找特定表对应的Mapper
MATCH (mapper:Type)-[:MAPPER_FOR_TABLE]->(table:Table {name: 'chatroom_host_guard_active_info'})
RETURN mapper.fqn, mapper.name
```

### 完整的技术方案查询示例

```cypher
// 查询某个接口的完整调用链（包括Dubbo、MQ、数据库）
MATCH (iface:Type {fqn: 'com.example.OrderService'})
OPTIONAL MATCH (impl:Type)-[:IMPLEMENTS]->(iface)
OPTIONAL MATCH (impl)-[:DUBBO_PROVIDES]->(iface)
OPTIONAL MATCH (caller:Type)-[:DUBBO_CALLS]->(iface)
OPTIONAL MATCH (method:Method)-[:LISTENS_TO_MQ]->(topic:MQTopic)
WHERE method.class_fqn = impl.fqn OR method.class_fqn = caller.fqn
OPTIONAL MATCH (mapper:Type)-[:MAPPER_FOR_TABLE]->(table:Table)
WHERE mapper.fqn STARTS WITH impl.fqn
RETURN iface, impl, caller, method, topic, mapper, table
```

## 技术方案生成中的应用

在生成技术方案时，这些关系可以用于：

1. **接口依赖分析**: 
   - 通过 `DUBBO_CALLS` 关系查找接口的调用方
   - 通过 `DUBBO_PROVIDES` 关系查找接口的实现类

2. **消息流转分析**:
   - 通过 `LISTENS_TO_MQ` 和 `SENDS_TO_MQ` 关系构建消息流转图
   - 分析消息的生产者和消费者

3. **数据访问分析**:
   - 通过 `MAPPER_FOR_TABLE` 关系查找接口涉及的数据表
   - 分析接口的数据访问模式

4. **完整调用链**:
   - 结合继承、实现、Dubbo调用、MQ消息、数据库访问等关系
   - 构建完整的接口调用链和数据流图

## 注意事项

1. **表名推断**: 表名推断基于命名约定，可能不完全准确。建议在生成技术方案时人工验证。

2. **MQ Topic提取**: Topic名称的提取主要基于源代码正则匹配，对于复杂的表达式可能无法识别。
   - RocketMQ的destination格式为 `topic:tag`，提取时会去掉tag部分，只保留topic名称。

3. **Dubbo服务接口**: 如果字段类型无法解析为FQN，将使用原始类型名。

5. **Dubbo注解识别**: 
   - 支持 `@DubboReference` 和 `@Reference` (com.alibaba.dubbo.config.annotation.Reference)
   - 支持 `@DubboService` 和 `@Service` (com.alibaba.dubbo.config.annotation.Service)
   - 通过注解的FQN中包含 "dubbo" 关键字来判断是否为Dubbo注解

4. **性能考虑**: 这些关系的识别会增加解析时间，但对于技术方案生成非常有用。
