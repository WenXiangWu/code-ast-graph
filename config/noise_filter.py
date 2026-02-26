"""
噪音过滤配置
定义在图谱查询中应该过滤掉的噪音类和包
"""

# JDK 标准库包前缀
JDK_PACKAGES = [
    'java.lang.',
    'java.util.',
    'java.io.',
    'java.nio.',
    'java.net.',
    'java.time.',
    'java.sql.',
    'java.math.',
    'java.text.',
    'java.util.concurrent.',
    'java.util.stream.',
    'java.util.function.',
    'javax.servlet.',
    'javax.annotation.',
]

# 常见工具类库包前缀
COMMON_UTIL_PACKAGES = [
    'org.apache.commons.',
    'org.springframework.util.',
    'com.google.common.',
    'org.slf4j.',
    'org.apache.logging.',
    'lombok.',
    'cn.hutool.',
    'com.alibaba.fastjson.',
    'com.fasterxml.jackson.',
    'org.apache.http.',
]

# 常见数据传输对象后缀
DTO_SUFFIXES = [
    'DTO',
    'Dto',
    'VO',
    'Vo',
    'DO',
    'Do',
    'Request',
    'Response',
    'Req',
    'Resp',
    'Result',
]

# 常见基础设施/噪音类名（精确匹配或包含）
NOISE_CLASS_NAMES = [
    'Code',       # 枚举/状态码
    'Log',        # 日志
    'Logger',
    'Constants',
    'BaseEntity',
    'BaseVO',
]

# 常见实体类后缀（可选，根据业务需要决定是否过滤）
ENTITY_SUFFIXES = [
    'Entity',
    'Model',
    'PO',
    'Po',
]

# 常见工具类后缀
UTIL_SUFFIXES = [
    'Utils',
    'Util',
    'Helper',
    'Constants',
    'Constant',
]

# 业务核心类关键词（保留这些类）
BUSINESS_KEYWORDS = [
    'Service',
    'Manager',
    'Facade',
    'Controller',
    'Handler',
    'Processor',
    'Strategy',
    'Factory',
    'Builder',
    'Listener',
    'Consumer',
    'Producer',
    'Component',
    'Adapter',
]


def is_noise_class(fqn: str, class_name: str, filter_mode: str = 'moderate') -> bool:
    """
    判断一个类是否为噪音类
    
    Args:
        fqn: 类的全限定名
        class_name: 类的简单名称
        filter_mode: 过滤模式
            - 'strict': 严格模式，过滤所有噪音（包括DTO、Entity）
            - 'moderate': 适中模式，过滤JDK和工具类（默认）
            - 'loose': 宽松模式，只过滤JDK核心类
            - 'none': 不过滤
    
    Returns:
        True 表示是噪音类，应该过滤掉
    """
    if not fqn:
        return True
    
    if filter_mode == 'none':
        return False
    
    # 1. JDK 标准库（所有模式都过滤）
    for pkg in JDK_PACKAGES:
        if fqn.startswith(pkg):
            return True
    
    # 2. 宽松模式只过滤JDK
    if filter_mode == 'loose':
        return False
    
    # 3. 常见工具类库（适中和严格模式过滤）
    for pkg in COMMON_UTIL_PACKAGES:
        if fqn.startswith(pkg):
            return True
    
    # 4. 工具类（适中和严格模式过滤）
    for suffix in UTIL_SUFFIXES:
        if class_name.endswith(suffix):
            return True
    
    # 5. 基础设施噪音类名（moderate 和 strict 都过滤）
    if filter_mode in ['moderate', 'strict']:
        for noise_name in NOISE_CLASS_NAMES:
            if class_name == noise_name:
                return True
    
    # 6. DTO/VO/Response 等（moderate 和 strict 都过滤）
    if filter_mode in ['moderate', 'strict']:
        for suffix in DTO_SUFFIXES:
            if class_name.endswith(suffix):
                return True
    
    # 7. Entity 后缀（只在严格模式过滤）
    if filter_mode == 'strict':
        for suffix in ENTITY_SUFFIXES:
            if class_name.endswith(suffix):
                return True
    
    # 8. 业务核心类，保留
    for keyword in BUSINESS_KEYWORDS:
        if keyword in class_name:
            return False
    
    return False


def get_noise_filter_cypher_condition(filter_mode: str = 'moderate') -> str:
    """
    生成 Cypher 查询的过滤条件
    
    Args:
        filter_mode: 过滤模式
    
    Returns:
        Cypher WHERE 子句片段
    """
    if filter_mode == 'none':
        return ''
    
    conditions = []
    
    # JDK 包过滤（所有模式）
    jdk_conditions = [f"NOT n.fqn STARTS WITH '{pkg}'" for pkg in JDK_PACKAGES]
    conditions.extend(jdk_conditions)
    
    if filter_mode in ['moderate', 'strict']:
        # 工具类库包过滤
        util_conditions = [f"NOT n.fqn STARTS WITH '{pkg}'" for pkg in COMMON_UTIL_PACKAGES]
        conditions.extend(util_conditions)
        
        # 工具类后缀过滤
        util_suffix_conditions = [f"NOT n.name ENDS WITH '{suffix}'" for suffix in UTIL_SUFFIXES]
        conditions.extend(util_suffix_conditions)
    
    if filter_mode == 'strict':
        # DTO/VO 后缀过滤
        dto_conditions = [f"NOT n.name ENDS WITH '{suffix}'" for suffix in DTO_SUFFIXES]
        conditions.extend(dto_conditions)
        
        # Entity 后缀过滤
        entity_conditions = [f"NOT n.name ENDS WITH '{suffix}'" for suffix in ENTITY_SUFFIXES]
        conditions.extend(entity_conditions)
    
    return ' AND ' + ' AND '.join(conditions) if conditions else ''


def get_noise_filter_function(filter_mode: str = 'moderate'):
    """
    返回一个过滤函数，用于在 Python 代码中过滤节点
    
    Args:
        filter_mode: 过滤模式
    
    Returns:
        过滤函数 (fqn, name) -> bool，返回 True 表示保留该节点
    """
    def filter_func(fqn: str, name: str) -> bool:
        return not is_noise_class(fqn, name, filter_mode)
    
    return filter_func
