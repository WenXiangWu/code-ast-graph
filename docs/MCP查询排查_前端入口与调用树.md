# MCP 查询排查：前端入口为空、下游节点不在树中

## 一、前端入口为空

### 原因说明
- 前端入口来自图上的 **RpcEndpoint** 与 **Method -[:EXPOSES]-> RpcEndpoint**。
- Controller 方法若使用 **多 path**，例如：
  ```java
  @PostMapping(path = {
      "/chatroom/v1/chatroom/room/reward",
      "/chatroom/gift/reward"
  })
  public Response<RewardGiftVO> rewardGift(...) { ... }
  ```
  旧逻辑只支持单 path（单个 Literal），多 path 时 `_extract_rpc_path` 返回 `None`，不会创建 RpcEndpoint，导致前端入口为空。

### 已做修改（scanner_v2）
- 新增 **`_extract_rpc_paths`**：支持单 path 与 **path = { "/a", "/b" }** 等多值，返回 `List[str]`。
- 创建 RpcEndpoint 时按 **每个 path 各建一条**，保证多 path 也会出现在「前端入口」中。
- **需要重新扫描** yuer-chatroom-pro-web 后，再查 MCP 才会出现前端入口。

---

## 二、下游核心节点（如 RewardService.rewardRoomGift）不在调用树中

### 可能原因

1. **图中没有 CALLS 边**
   - 调用树依赖 **Method -[:CALLS]-> Method**。
   - 若 Controller 调用的是接口（如 `RewardService`），扫描时未解析到**实现类方法**并建立 CALLS，则树中不会出现该下游。
   - **处理**：确认扫描是否包含实现类、是否对「接口调用」解析到具体实现并写入 CALLS。

2. **之前按「当前项目」过滤**
   - 旧逻辑只保留 `called_project.name = $current_project` 的 CALLS，同仓库多模块（如 web 与 service 分属不同 Project 节点）时会把 Service 侧调用过滤掉。
   - **已做修改**：构建调用树时**不再按项目过滤** CALLS，所有 CALLS 都会展开，避免漏掉跨模块的 Service 等节点。

3. **CALLS 数量被 LIMIT 截断**
   - 旧逻辑 `LIMIT 10`，若一个方法调用超过 10 个其他方法，后面的（可能包含核心 Service）会被截断。
   - **已做修改**：`LIMIT` 已提高到 **80**，减少因截断导致的核心下游缺失。

4. **Dubbo 下游未入图**
   - `rewardTradeRemoteService.rewardRoomGift` 是 Dubbo 调用，树中会先出现 **dubbo_call** 节点，再递归展开**实现类方法**。
   - 若实现类（如 `RewardTradeRemoteServiceImpl`）所在项目**未被扫描**，图中没有对应 Method/CLASS 和 IMPLEMENTS，则 Dubbo 节点下不会挂载实现类子树。
   - **处理**：把 Dubbo 接口的**实现类所在项目**也纳入扫描，保证图中有 IMPLEMENTS 和实现类 Method，树中才会出现该核心节点。

5. **接口“简化签名”导致实现类未展开（已修复）**
   - Scanner 创建的 CALLS 边指向的是**简化签名**：`com.xxx.RewardService.rewardGift(...)`，而图中接口若由扫描得到，其 Method 是**完整签名**。
   - `_find_implementation_methods` 原先只按**完整签名**匹配接口方法，导致匹配不到，实现类（如 `RewardServiceImpl.rewardGift`）不会作为子树展开，其下的 DUBBO_CALLS（如 `rewardTradeRemoteService.rewardRoomGift`）也就不会出现在树中。
   - **处理**：在 `_find_implementation_methods` 中，当入参为简化签名（以 `(...)` 结尾）时，按「接口 FQN + 方法名」再查一次，从而找到实现类方法并展开子树（见下方修改汇总）。

### 建议自检（Neo4j）

```cypher
// 1) 入口方法是否有 EXPOSES -> RpcEndpoint（多 path 修复并重扫后应有）
MATCH (m:Method)-[:EXPOSES]->(ep:RpcEndpoint)
WHERE m.name = 'rewardGift'
RETURN m.signature, ep.path, ep.http_method;

// 2) 入口方法是否有 CALLS 到 RewardService.rewardGift
MATCH (start:Method {name: 'rewardGift'})-[:CALLS*1..5]->(called:Method)
WHERE called.name = 'rewardGift'
RETURN start.signature, called.signature;

// 3) RewardService 中是否有 DUBBO_CALLS 到 rewardRoomGift 接口方法
MATCH (caller:Method)-[r:DUBBO_CALLS]->(ifaceMethod:Method)
WHERE ifaceMethod.name = 'rewardRoomGift'
RETURN caller.signature, ifaceMethod.signature, type(r);
```

若 (1) 无结果：需确认多 path 已生效并**重新扫描**；  
若 (2) 无结果：图中缺少 Controller → Service 的 CALLS，需检查扫描是否解析接口到实现；  
若 (3) 无结果：图中缺少 Dubbo 调用边，需检查 Dubbo 注入与 DUBBO_CALLS 的写入。

---

## 三、修改汇总

| 问题           | 文件/位置              | 修改内容 |
|----------------|------------------------|----------|
| 前端入口为空   | scanner_v2 `_extract_rpc_path` | 支持多 path：`_extract_rpc_paths` + 按 path 创建多个 RpcEndpoint |
| 下游不在树中   | mcp_query `_build_call_tree`  | 去掉 CALLS 的「当前项目」过滤；LIMIT 10 → 80 |
| 实现类/下游仍不在树中 | mcp_query `_find_implementation_methods` | 支持简化签名：当 `method_sig` 以 `(...)` 结尾时，按接口 FQN + 方法名查找实现类，保证 Controller→Service→Dubbo 链上的 RewardService.rewardGift 等节点能展开 |

**注意**：多 path 与 RpcEndpoint 的修复需要**重新扫描**对应项目后，MCP 查询结果才会出现前端入口；调用树修改无需重扫，只影响后续查询。
