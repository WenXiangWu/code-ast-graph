# 增量更新机制设计

> 当 Git 项目更新后，如何高效地增量更新知识图谱

## 📋 目录

1. [问题场景](#问题场景)
2. [设计目标](#设计目标)
3. [增量更新策略](#增量更新策略)
4. [变更检测机制](#变更检测机制)
5. [实现方案](#实现方案)
6. [性能优化](#性能优化)
7. [使用示例](#使用示例)

---

## 问题场景

### 典型场景

1. **初始扫描**：从 Git 克隆项目，执行首次知识图谱构建
2. **项目更新**：项目代码发生变更（新增、修改、删除文件）
3. **增量更新**：只更新变更的部分，而不是全量重新扫描

### 当前问题

现有实现只有两种模式：
- `force_rescan=False`：如果项目已存在，直接跳过
- `force_rescan=True`：全量重新扫描，效率低

**问题**：
- 无法检测项目是否更新
- 无法只更新变更的文件
- 全量扫描耗时且浪费资源

---

## 设计目标

### 核心目标

1. **自动检测变更**：自动检测项目文件的变化
2. **增量更新**：只处理变更的文件
3. **高效性能**：大幅减少扫描时间
4. **数据一致性**：确保知识图谱与代码库同步

### 功能需求

- ✅ 支持 Git 仓库的变更检测
- ✅ 支持文件系统的变更检测（基于时间戳和文件哈希）
- ✅ 文件级别的增量更新
- ✅ 自动清理已删除文件的实体
- ✅ 记录项目版本信息（Git commit hash、扫描时间等）

---

## 增量更新策略

### 策略对比

| 策略 | 优点 | 缺点 | 适用场景 |
|------|------|------|----------|
| **全量扫描** | 简单、数据一致 | 耗时、资源消耗大 | 首次扫描、重大重构后 |
| **基于 Git Diff** | 精确、高效 | 需要 Git 仓库 | Git 项目 |
| **基于文件哈希** | 通用、不依赖 Git | 需要存储文件哈希 | 非 Git 项目 |
| **基于时间戳** | 简单 | 不够精确 | 简单场景 |

### 推荐策略：混合策略

**Git 项目**：优先使用 Git Diff，回退到文件哈希  
**非 Git 项目**：使用文件哈希 + 时间戳

---

## 变更检测机制

### 1. Git 变更检测

#### 数据模型

```python
@dataclass
class FileChange:
    """文件变更信息"""
    file_path: str
    change_type: str  # 'added', 'modified', 'deleted', 'renamed'
    old_path: Optional[str] = None  # 重命名时的旧路径
    old_hash: Optional[str] = None  # 旧文件哈希
    new_hash: Optional[str] = None  # 新文件哈希

@dataclass
class ProjectVersion:
    """项目版本信息"""
    project_name: str
    commit_hash: str
    commit_time: datetime
    branch: str
    scanned_at: datetime
    file_count: int
    entity_count: int
```

#### Git 变更检测实现

```python
class GitChangeDetector:
    """Git 变更检测器"""
    
    def __init__(self, repo_path: str):
        self.repo_path = Path(repo_path)
        self.repo = None
    
    def detect_changes(
        self, 
        last_commit_hash: Optional[str] = None
    ) -> List[FileChange]:
        """
        检测文件变更
        
        Args:
            last_commit_hash: 上次扫描的 commit hash，None 表示首次扫描
        
        Returns:
            文件变更列表
        """
        import git
        
        if self.repo is None:
            self.repo = git.Repo(self.repo_path)
        
        # 获取当前 commit
        current_commit = self.repo.head.commit
        
        # 如果是首次扫描
        if last_commit_hash is None:
            # 返回所有文件作为新增
            changes = []
            for item in current_commit.tree.traverse():
                if item.type == 'blob' and self._is_code_file(item.path):
                    changes.append(FileChange(
                        file_path=item.path,
                        change_type='added',
                        new_hash=item.hexsha
                    ))
            return changes
        
        # 获取上次 commit
        try:
            last_commit = self.repo.commit(last_commit_hash)
        except git.BadName:
            # commit 不存在，返回所有文件
            return self.detect_changes(None)
        
        # 计算 diff
        changes = []
        diff = last_commit.diff(current_commit)
        
        for item in diff:
            if item.deleted_file:
                changes.append(FileChange(
                    file_path=item.a_path,
                    change_type='deleted',
                    old_hash=item.a_blob.hexsha if item.a_blob else None
                ))
            elif item.new_file:
                changes.append(FileChange(
                    file_path=item.b_path,
                    change_type='added',
                    new_hash=item.b_blob.hexsha if item.b_blob else None
                ))
            elif item.renamed_file:
                changes.append(FileChange(
                    file_path=item.b_path,
                    change_type='renamed',
                    old_path=item.a_path,
                    old_hash=item.a_blob.hexsha if item.a_blob else None,
                    new_hash=item.b_blob.hexsha if item.b_blob else None
                ))
            else:
                # 修改的文件
                changes.append(FileChange(
                    file_path=item.b_path,
                    change_type='modified',
                    old_hash=item.a_blob.hexsha if item.a_blob else None,
                    new_hash=item.b_blob.hexsha if item.b_blob else None
                ))
        
        return changes
    
    def get_current_version(self) -> ProjectVersion:
        """获取当前项目版本信息"""
        commit = self.repo.head.commit
        return ProjectVersion(
            project_name=self.repo.working_dir,
            commit_hash=commit.hexsha,
            commit_time=datetime.fromtimestamp(commit.committed_date),
            branch=self.repo.active_branch.name,
            scanned_at=datetime.now(),
            file_count=0,  # 需要统计
            entity_count=0  # 需要统计
        )
    
    def _is_code_file(self, path: str) -> bool:
        """判断是否为代码文件"""
        code_extensions = {'.java', '.py', '.ts', '.js', '.cpp', '.c', '.h'}
        return Path(path).suffix in code_extensions
```

### 2. 文件哈希变更检测

#### 数据模型

```python
@dataclass
class FileMetadata:
    """文件元数据"""
    file_path: str
    file_hash: str  # SHA256 哈希
    file_size: int
    modified_time: datetime
    language: str
```

#### 文件哈希检测实现

```python
import hashlib
from pathlib import Path

class FileHashChangeDetector:
    """基于文件哈希的变更检测器"""
    
    def __init__(self, project_path: str):
        self.project_path = Path(project_path)
        self.stored_metadata: Dict[str, FileMetadata] = {}
    
    def load_metadata(self, metadata_file: str):
        """加载已存储的文件元数据"""
        import json
        if Path(metadata_file).exists():
            with open(metadata_file, 'r') as f:
                data = json.load(f)
                self.stored_metadata = {
                    path: FileMetadata(**meta)
                    for path, meta in data.items()
                }
    
    def save_metadata(self, metadata_file: str):
        """保存文件元数据"""
        import json
        data = {
            path: {
                'file_path': meta.file_path,
                'file_hash': meta.file_hash,
                'file_size': meta.file_size,
                'modified_time': meta.modified_time.isoformat(),
                'language': meta.language
            }
            for path, meta in self.stored_metadata.items()
        }
        with open(metadata_file, 'w') as f:
            json.dump(data, f, indent=2)
    
    def detect_changes(self) -> List[FileChange]:
        """检测文件变更"""
        changes = []
        current_files = {}
        
        # 扫描当前文件
        for file_path in self._scan_code_files():
            metadata = self._get_file_metadata(file_path)
            current_files[str(file_path)] = metadata
        
        # 检测新增和修改的文件
        for file_path, metadata in current_files.items():
            if file_path not in self.stored_metadata:
                # 新增文件
                changes.append(FileChange(
                    file_path=file_path,
                    change_type='added',
                    new_hash=metadata.file_hash
                ))
            else:
                stored = self.stored_metadata[file_path]
                if stored.file_hash != metadata.file_hash:
                    # 文件已修改
                    changes.append(FileChange(
                        file_path=file_path,
                        change_type='modified',
                        old_hash=stored.file_hash,
                        new_hash=metadata.file_hash
                    ))
        
        # 检测删除的文件
        for file_path in self.stored_metadata:
            if file_path not in current_files:
                changes.append(FileChange(
                    file_path=file_path,
                    change_type='deleted',
                    old_hash=self.stored_metadata[file_path].file_hash
                ))
        
        # 更新元数据
        self.stored_metadata = current_files
        
        return changes
    
    def _get_file_metadata(self, file_path: Path) -> FileMetadata:
        """获取文件元数据"""
        stat = file_path.stat()
        file_hash = self._calculate_hash(file_path)
        
        # 检测语言
        language = self._detect_language(file_path)
        
        return FileMetadata(
            file_path=str(file_path),
            file_hash=file_hash,
            file_size=stat.st_size,
            modified_time=datetime.fromtimestamp(stat.st_mtime),
            language=language
        )
    
    def _calculate_hash(self, file_path: Path) -> str:
        """计算文件 SHA256 哈希"""
        sha256 = hashlib.sha256()
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b""):
                sha256.update(chunk)
        return sha256.hexdigest()
    
    def _detect_language(self, file_path: Path) -> str:
        """检测文件语言"""
        ext_to_lang = {
            '.java': 'java',
            '.py': 'python',
            '.ts': 'typescript',
            '.js': 'javascript',
            '.cpp': 'cpp',
            '.c': 'c',
            '.h': 'c'
        }
        return ext_to_lang.get(file_path.suffix, 'unknown')
    
    def _scan_code_files(self) -> Iterator[Path]:
        """扫描代码文件"""
        code_extensions = {'.java', '.py', '.ts', '.js', '.cpp', '.c', '.h'}
        for file_path in self.project_path.rglob('*'):
            if file_path.is_file() and file_path.suffix in code_extensions:
                yield file_path
```

---

## 实现方案

### 1. 扩展存储接口

```python
class GraphStorage(ABC):
    """扩展的存储接口"""
    
    # ... 现有方法 ...
    
    @abstractmethod
    def get_project_version(self, project_name: str) -> Optional[ProjectVersion]:
        """获取项目版本信息"""
        pass
    
    @abstractmethod
    def save_project_version(self, version: ProjectVersion) -> bool:
        """保存项目版本信息"""
        pass
    
    @abstractmethod
    def get_file_entities(self, project_name: str, file_path: str) -> List[CodeEntity]:
        """获取文件对应的所有实体"""
        pass
    
    @abstractmethod
    def delete_file_entities(self, project_name: str, file_path: str) -> int:
        """删除文件对应的所有实体"""
        pass
    
    @abstractmethod
    def update_file_entities(
        self, 
        project_name: str, 
        file_path: str, 
        entities: List[CodeEntity]
    ) -> int:
        """更新文件对应的实体（先删除再创建）"""
        pass
```

### 2. 增量更新服务

```python
class IncrementalUpdateService:
    """增量更新服务"""
    
    def __init__(
        self,
        change_detector: Union[GitChangeDetector, FileHashChangeDetector],
        parser: CodeParser,
        storage: GraphStorage
    ):
        self.change_detector = change_detector
        self.parser = parser
        self.storage = storage
    
    def update_project(
        self,
        project_name: str,
        project_path: str,
        force_full_scan: bool = False
    ) -> Dict:
        """
        增量更新项目
        
        Args:
            project_name: 项目名称
            project_path: 项目路径
            force_full_scan: 是否强制全量扫描
        
        Returns:
            更新结果
        """
        logger.info(f"开始增量更新项目: {project_name}")
        
        # 1. 获取上次扫描的版本信息
        last_version = self.storage.get_project_version(project_name)
        
        # 2. 检测变更
        if force_full_scan or last_version is None:
            logger.info("执行全量扫描")
            return self._full_scan(project_name, project_path)
        
        # 3. 检测文件变更
        if isinstance(self.change_detector, GitChangeDetector):
            changes = self.change_detector.detect_changes(
                last_commit_hash=last_version.commit_hash
            )
        else:
            changes = self.change_detector.detect_changes()
        
        if not changes:
            logger.info("没有检测到变更")
            return {
                'success': True,
                'updated': False,
                'message': '项目无变更'
            }
        
        logger.info(f"检测到 {len(changes)} 个文件变更")
        
        # 4. 处理变更
        stats = {
            'added': 0,
            'modified': 0,
            'deleted': 0,
            'renamed': 0
        }
        
        self.storage.begin_transaction()
        try:
            for change in changes:
                if change.change_type == 'deleted':
                    # 删除文件对应的实体
                    deleted_count = self.storage.delete_file_entities(
                        project_name, change.file_path
                    )
                    stats['deleted'] += deleted_count
                    logger.info(f"删除文件 {change.file_path}: {deleted_count} 个实体")
                
                elif change.change_type == 'renamed':
                    # 重命名：先删除旧路径，再添加新路径
                    old_deleted = self.storage.delete_file_entities(
                        project_name, change.old_path
                    )
                    # 解析新文件
                    new_file = self._get_file_from_path(change.file_path)
                    parse_result = self.parser.parse(new_file, project_info)
                    self.storage.create_entities(parse_result.entities)
                    self.storage.create_relationships(parse_result.relationships)
                    stats['renamed'] += 1
                
                elif change.change_type in ['added', 'modified']:
                    # 新增或修改：解析文件并更新实体
                    file = self._get_file_from_path(change.file_path)
                    parse_result = self.parser.parse(file, project_info)
                    
                    if change.change_type == 'modified':
                        # 先删除旧实体
                        self.storage.delete_file_entities(
                            project_name, change.file_path
                        )
                        stats['modified'] += 1
                    else:
                        stats['added'] += 1
                    
                    # 创建新实体
                    self.storage.create_entities(parse_result.entities)
                    self.storage.create_relationships(parse_result.relationships)
            
            # 5. 更新项目版本信息
            if isinstance(self.change_detector, GitChangeDetector):
                new_version = self.change_detector.get_current_version()
            else:
                new_version = ProjectVersion(
                    project_name=project_name,
                    commit_hash='',  # 非 Git 项目
                    commit_time=datetime.now(),
                    branch='',
                    scanned_at=datetime.now(),
                    file_count=0,
                    entity_count=0
                )
            
            self.storage.save_project_version(new_version)
            self.storage.commit_transaction()
            
            logger.info(f"增量更新完成: {stats}")
            
            return {
                'success': True,
                'updated': True,
                'stats': stats,
                'changes_count': len(changes)
            }
            
        except Exception as e:
            self.storage.rollback_transaction()
            logger.error(f"增量更新失败: {e}", exc_info=True)
            raise
    
    def _full_scan(self, project_name: str, project_path: str) -> Dict:
        """全量扫描"""
        from .scan_service import ScanService
        scan_service = ScanService(
            input_source=FileSystemCodeInput(project_path),
            parser=self.parser,
            storage=self.storage
        )
        return scan_service.scan_project(project_name, project_path, force_rescan=True)
    
    def _get_file_from_path(self, file_path: str) -> CodeFile:
        """从路径获取 CodeFile 对象"""
        path = Path(file_path)
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        return CodeFile(
            path=path,
            content=content,
            language=self._detect_language(path),
            size=path.stat().st_size,
            modified_time=datetime.fromtimestamp(path.stat().st_mtime)
        )
```

### 3. Git 输入源集成

```python
class GitCodeInput(CodeInput):
    """Git 代码输入源（支持增量更新）"""
    
    def __init__(self, repo_path: str, branch: str = 'main'):
        self.repo_path = Path(repo_path)
        self.branch = branch
        self.repo = None
    
    def get_changes_since(self, commit_hash: str) -> List[FileChange]:
        """获取自指定 commit 以来的变更"""
        if self.repo is None:
            import git
            self.repo = git.Repo(self.repo_path)
        
        detector = GitChangeDetector(str(self.repo_path))
        return detector.detect_changes(commit_hash)
    
    def get_current_commit(self) -> str:
        """获取当前 commit hash"""
        if self.repo is None:
            import git
            self.repo = git.Repo(self.repo_path)
        return self.repo.head.commit.hexsha
```

---

## 性能优化

### 1. 批量操作

- 批量删除实体
- 批量创建实体
- 批量创建关系

### 2. 并行处理

```python
from concurrent.futures import ThreadPoolExecutor

def update_files_parallel(
    self,
    changes: List[FileChange],
    max_workers: int = 4
) -> Dict:
    """并行处理文件变更"""
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(self._process_change, change): change
            for change in changes
        }
        
        results = []
        for future in futures:
            change = futures[future]
            try:
                result = future.result()
                results.append(result)
            except Exception as e:
                logger.error(f"处理变更失败 {change.file_path}: {e}")
        
        return self._aggregate_results(results)
```

### 3. 增量索引

只对变更的文件建立索引，避免重复处理未变更的文件。

---

## 使用示例

### 示例 1：Git 项目的增量更新

```python
from src.services.incremental_update import IncrementalUpdateService
from src.inputs.git_input import GitCodeInput
from src.parsers.java import JavaParser
from src.storage.neo4j import Neo4jStorage

# 1. 初始化组件
git_input = GitCodeInput('/path/to/repo')
parser = JavaParser()
storage = Neo4jStorage(uri='bolt://localhost:7687', user='neo4j', password='password')

# 2. 创建增量更新服务
update_service = IncrementalUpdateService(
    change_detector=GitChangeDetector('/path/to/repo'),
    parser=parser,
    storage=storage
)

# 3. 执行增量更新
result = update_service.update_project(
    project_name='my-project',
    project_path='/path/to/repo'
)

print(f"更新结果: {result}")
# 输出: {
#   'success': True,
#   'updated': True,
#   'stats': {'added': 5, 'modified': 3, 'deleted': 1, 'renamed': 0},
#   'changes_count': 9
# }
```

### 示例 2：定时自动更新

```python
import schedule
import time

def auto_update_project():
    """自动更新项目"""
    update_service = IncrementalUpdateService(...)
    result = update_service.update_project('my-project', '/path/to/repo')
    logger.info(f"自动更新完成: {result}")

# 每小时执行一次
schedule.every().hour.do(auto_update_project)

while True:
    schedule.run_pending()
    time.sleep(60)
```

### 示例 3：Git Webhook 触发更新

```python
from flask import Flask, request

app = Flask(__name__)

@app.route('/webhook/git', methods=['POST'])
def git_webhook():
    """Git Webhook 处理"""
    payload = request.json
    
    # 解析 Webhook 事件
    if payload.get('ref') == 'refs/heads/main':
        # 拉取最新代码
        repo = git.Repo('/path/to/repo')
        repo.remotes.origin.pull()
        
        # 执行增量更新
        update_service = IncrementalUpdateService(...)
        result = update_service.update_project(
            project_name='my-project',
            project_path='/path/to/repo'
        )
        
        return {'status': 'success', 'result': result}
    
    return {'status': 'ignored'}

if __name__ == '__main__':
    app.run(port=5000)
```

---

## 数据存储设计

### Neo4j Schema 扩展

```cypher
// 项目版本节点
(:ProjectVersion {
    project_name: string,
    commit_hash: string,
    commit_time: datetime,
    branch: string,
    scanned_at: datetime,
    file_count: int,
    entity_count: int
})

// 文件元数据节点
(:FileMetadata {
    file_path: string,
    file_hash: string,
    file_size: int,
    modified_time: datetime,
    language: string
})

// 关系
(:Project)-[:HAS_VERSION]->(:ProjectVersion)
(:Project)-[:HAS_FILE]->(:FileMetadata)
(:CodeEntity)-[:FROM_FILE]->(:FileMetadata)
```

---

## 总结

增量更新机制的核心要点：

1. **变更检测**：基于 Git Diff 或文件哈希
2. **增量处理**：只处理变更的文件
3. **数据一致性**：删除旧实体，创建新实体
4. **版本追踪**：记录项目版本信息
5. **性能优化**：批量操作、并行处理

通过增量更新，可以：
- ✅ 大幅减少扫描时间（只处理变更文件）
- ✅ 降低资源消耗（CPU、内存、网络）
- ✅ 支持实时更新（Git Webhook 触发）
- ✅ 保持数据一致性（自动清理已删除文件）
