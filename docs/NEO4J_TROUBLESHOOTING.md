# Neo4j 无法访问问题排查报告

## 🔍 排查结论

**根本原因：Neo4j 进程尚未启动，容器卡在启动阶段。**

### 详细发现

1. **端口映射正常**
   - 主机 7474、7687 端口在监听
   - Docker 端口映射 `7474:7474`、`7687:7687` 配置正确

2. **容器状态为 unhealthy**
   - 健康检查持续失败，报错：`Connection refused`
   - 说明容器内部 Neo4j 服务未在监听

3. **Neo4j 进程未运行**（关键）
   - 容器内当前进程：`tini`、`docker-entrypoint.sh`、`wget`
   - **没有 Java/Neo4j 进程**
   - 卡在 `wget` 下载 APOC 插件阶段（或之后步骤未执行）

4. **APOC 插件已下载**
   - `/var/lib/neo4j/plugins/apoc.jar` 已存在（约 3.9MB）
   - 但入口脚本可能未继续到启动 Neo4j

5. **HTTP 访问失败**
   - `Invoke-WebRequest` 报：连接被远程主机关闭
   - 因 Neo4j 未运行，Docker 端口转发无真实服务可转发

---

## ✅ 解决方案

### 方案一：使用官方精简 Neo4j 镜像（推荐）

新建容器，不依赖 APOC 自动下载，启动更快：

```powershell
# 停止并删除旧容器
docker stop jqassistant-neo4j
docker rm jqassistant-neo4j

# 使用官方镜像启动（code-ast-graph 项目用）
docker run -d `
  --name neo4j `
  -p 7474:7474 `
  -p 7687:7687 `
  -e NEO4J_AUTH=neo4j/jqassistant123 `
  neo4j:5.15.0
```

等待约 30 秒后访问：http://127.0.0.1:7474/

**注意**：Neo4j 5.x 与 4.x 有差异，若需兼容 jQAssistant 的 4.4，可改用：

```powershell
docker run -d `
  --name neo4j `
  -p 7474:7474 `
  -p 7687:7687 `
  -e NEO4J_AUTH=neo4j/jqassistant123 `
  neo4j:4.4.26
```

### 方案二：挂载插件目录避免重复下载

若必须使用带 APOC 的 jqassistant-neo4j 镜像，可先持久化插件目录：

```powershell
# 创建插件目录
mkdir -p $HOME/neo4j-plugins

# 将已有 apoc.jar 复制出来（从旧容器）
docker cp jqassistant-neo4j:/var/lib/neo4j/plugins/apoc.jar $HOME/neo4j-plugins/

# 使用卷挂载启动新容器，避免每次下载
docker run -d `
  --name neo4j `
  -p 7474:7474 `
  -p 7687:7687 `
  -e NEO4J_AUTH=neo4j/jqassistant123 `
  -v ${HOME}/neo4j-plugins:/plugins `
  neo4j:4.4.26
```

### 方案三：等待当前容器完成启动

若希望保留 `jqassistant-neo4j` 容器，可多等几分钟，观察 Neo4j 是否最终启动：

```powershell
# 持续查看容器内是否有 java 进程
docker exec jqassistant-neo4j ps aux | findstr java
```

若一段时间后仍无 java 进程，建议采用方案一或方案二。

---

## 📋 更新 .env 配置

采用新容器名 `neo4j` 后，确认 `.env` 中 Neo4j 配置与容器一致：

```
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=jqassistant123
```

---

## 🔧 验证步骤

启动新容器后，可按以下步骤验证：

```powershell
# 1. 等待约 30 秒
Start-Sleep -Seconds 30

# 2. 检查 Neo4j 是否在运行
docker exec neo4j ps aux | findstr java

# 3. 测试 HTTP 访问
Invoke-WebRequest -Uri "http://127.0.0.1:7474/" -UseBasicParsing | Select-Object StatusCode

# 4. 浏览器打开
# http://127.0.0.1:7474/
# 连接 URL: bolt://localhost:7687
# 用户名: neo4j
# 密码: jqassistant123
```
