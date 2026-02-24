"""
扫描 Java 项目脚本
"""

import sys
import asyncio
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

# 注意：此脚本需要插件系统，在新项目中可能需要调整
# from src.plugins import initialize_all_plugins, get_plugin


async def main():
    """主函数"""
    
    if len(sys.argv) < 3:
        print("用法: python scan_project.py <project_name> <project_path> [force_rescan]")
        print("\n示例:")
        print("  python scan_project.py user-service /path/to/user-service")
        print("  python scan_project.py user-service /path/to/user-service true")
        sys.exit(1)
    
    project_name = sys.argv[1]
    project_path = sys.argv[2]
    force_rescan = len(sys.argv) > 3 and sys.argv[3].lower() == 'true'
    
    print(f"=" * 60)
    print(f"扫描 Java 项目: {project_name}")
    print(f"项目路径: {project_path}")
    print(f"强制重扫: {force_rescan}")
    print(f"=" * 60)
    
    # 初始化插件
    print("\n[1] 初始化 jQAssistant 插件...")
    results = initialize_all_plugins()
    
    if not results.get('jqassistant'):
        print("❌ 插件初始化失败，请检查配置")
        sys.exit(1)
    
    print("✅ 插件初始化成功")
    
    # 获取工具
    from src.jqassistant.mcp_tools import get_jqassistant_tools
    tools = get_jqassistant_tools()
    
    # 扫描项目
    print(f"\n[2] 开始扫描项目: {project_name}")
    print("⏳ 这可能需要几分钟，请耐心等待...")
    
    result = await tools.scan_project(project_name, project_path, force_rescan)
    
    if result.get('success'):
        print(f"✅ 扫描成功")
        print(f"   方法: {result.get('method', 'unknown')}")
        if result.get('skipped'):
            print(f"   状态: 项目已存在，跳过扫描")
            print(f"   提示: 使用 force_rescan=true 强制重新扫描")
    else:
        print(f"❌ 扫描失败")
        print(f"   错误: {result.get('error')}")
        if result.get('help'):
            print(f"   帮助: {result.get('help')}")
    
    # 显示统计信息
    print(f"\n[3] 查询项目信息...")
    plugin = get_plugin('jqassistant')
    project_info = plugin.client.get_project_info(project_name)
    
    if project_info:
        print(f"✅ 项目信息:")
        print(f"   类型数: {project_info.get('type_count', 0)}")
        print(f"   依赖数: {project_info.get('dependency_count', 0)}")
        print(f"   扫描时间: {project_info.get('scanned_at', 'N/A')}")
    
    print("\n" + "=" * 60)
    print("✅ 完成")


if __name__ == "__main__":
    asyncio.run(main())
