with open(r'd:\cursor\bixin-ai-agent-platform\backend\agents\code_registry.py', encoding='utf-8') as f:
    src = f.read()
print('tech_plan_agent in CODE_AGENTS:', '"tech_plan_agent"' in src)
print('_build_tech_plan_agent defined:', 'async def _build_tech_plan_agent' in src)
print('mcp_code_search tool:', 'mcp__code_index_mcp__mcp_code_search' in src)
print('ast_query_call_stats tool:', 'mcp__code_ast_mcp__ast_query_call_stats' in src)
print('mcp_read_full_file tool:', 'mcp__code_index_mcp__mcp_read_full_file' in src)
print()
skill = open(r'd:\cursor\bixin-ai-agent-platform\.claude\skills\tech-plan-generator\SKILL.md', encoding='utf-8').read()
print('SKILL.md lines:', len(skill.splitlines()))
print('stage1 (mcp_code_search):', 'mcp__code_index_mcp__mcp_code_search' in skill)
print('stage2 (ast_query_call_stats):', 'ast_query_call_stats' in skill)
print('stage3 (mcp_read_full_file):', 'mcp_read_full_file' in skill)
print('stage3 (_code_research dir):', '_code_research' in skill)
print()
print('ALL OK' if all([
    '"tech_plan_agent"' in src,
    'async def _build_tech_plan_agent' in src,
    'mcp__code_index_mcp__mcp_code_search' in src,
    'mcp__code_ast_mcp__ast_query_call_stats' in src,
    'mcp__code_index_mcp__mcp_read_full_file' in src,
    'mcp_read_full_file' in skill,
    '_code_research' in skill,
]) else 'SOME CHECKS FAILED')
