import { useState, useEffect } from 'react'
import { Card, Form, Input, Button, Select, message, Descriptions, Table, Tag, Tabs, Space, Typography, Tree } from 'antd'
import { SearchOutlined, ApiOutlined, DatabaseOutlined, CloudOutlined, ClockCircleOutlined, MessageOutlined, ApartmentOutlined, FunctionOutlined, SwapOutlined, BarChartOutlined } from '@ant-design/icons'
import type { DataNode } from 'antd/es/tree'
import axios from 'axios'
import { JsonView, defaultStyles } from 'react-json-view-lite'
import 'react-json-view-lite/dist/index.css'
import './MCPQuery.css'

const { Title, Text } = Typography
const { TabPane } = Tabs

interface CallNode {
  node_type: string
  project: string
  class_fqn: string
  class_name: string
  method_name?: string
  method_signature?: string
  arch_layer?: string
  dubbo_interface?: string
  dubbo_method?: string
  via_field?: string
  table_name?: string
  mapper_name?: string
  mq_topic?: string
  mq_role?: string
  job_type?: string
  cron_expr?: string
  children: CallNode[]
}

interface MCPQueryResult {
  success: boolean
  message: string
  endpoints: Array<{
    project: string
    class_fqn: string
    method: string
    path: string
    http_method: string
  }>
  internal_classes: Array<{
    project: string
    class_fqn: string
    class_name: string
    arch_layer: string
  }>
  dubbo_calls: Array<{
    caller_project: string
    caller_class: string
    caller_method: string
    dubbo_interface: string
    dubbo_method: string
    via_field: string
  }>
  tables: Array<{
    project: string
    mapper_fqn: string
    mapper_name: string
    table_name: string
  }>
  aries_jobs: Array<{
    project: string
    class_fqn: string
    class_name: string
    job_type: string
    cron_expr?: string
  }>
  mq_info: Array<{
    project: string
    class_fqn: string
    class_name: string
    mq_type: string
    topic: string
    role: string
    method?: string
  }>
  call_tree?: CallNode
}

const STORAGE_KEY = 'mcp-query-last-result'

/** 无结果时的空数据结构，用于始终展示下方统计与 Tab 区域 */
const EMPTY_RESULT: MCPQueryResult = {
  success: false,
  message: '',
  endpoints: [],
  internal_classes: [],
  dubbo_calls: [],
  tables: [],
  aries_jobs: [],
  mq_info: [],
}

/** 调用统计：类频次、方法列表、表、MQ、前端入口 */
interface CallStatistics {
  class_stats: Array<{
    class: string
    call_count: number
    methods: string[]
    project: string
  }>
  tables: string[]
  mq_list: string[]
  frontend_entries: Array<{
    project: string
    class_fqn: string
    method: string
    path: string
    http_method: string
  }>
}

function collectCallStatistics(root: CallNode, result: MCPQueryResult): CallStatistics {
  const classMap = new Map<string, { count: number; methods: Set<string>; project: string }>()
  const tables = new Set<string>()
  const mqList = new Set<string>()

  function walk(node: CallNode) {
    if (node.node_type === 'method' || node.node_type === 'interface' || node.node_type === 'aries_job') {
      const key = node.class_fqn || ''
      if (key) {
        if (!classMap.has(key)) {
          classMap.set(key, { count: 0, methods: new Set(), project: node.project || '' })
        }
        const ent = classMap.get(key)!
        ent.count += 1
        if (node.method_name) ent.methods.add(node.method_name)
      }
    }
    if (node.node_type === 'db_call' && node.table_name) {
      tables.add(node.table_name)
    }
    if (node.node_type === 'mq' && node.mq_topic) {
      mqList.add(node.mq_topic)
    }
    node.children?.forEach(walk)
  }
  walk(root)

  const class_stats = Array.from(classMap.entries())
    .map(([cls, v]) => ({
      class: cls,
      call_count: v.count,
      methods: Array.from(v.methods).sort(),
      project: v.project,
    }))
    .sort((a, b) => b.call_count - a.call_count)

  return {
    class_stats,
    tables: Array.from(tables).sort(),
    mq_list: Array.from(mqList).sort(),
    frontend_entries: result.endpoints || [],
  }
}

function MCPQuery() {
  const [form] = Form.useForm()
  const [projects, setProjects] = useState<string[]>([])
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<MCPQueryResult | null>(() => {
    try {
      const raw = sessionStorage.getItem(STORAGE_KEY)
      if (raw) {
        const parsed = JSON.parse(raw) as MCPQueryResult
        if (parsed && typeof parsed.success === 'boolean') return parsed
      }
    } catch (_) {}
    return null
  })

  useEffect(() => {
    fetchProjects()
  }, [])

  // 持久化查询结果，切换 Tab 或离开再返回时保留
  useEffect(() => {
    if (result && result.success) {
      try {
        sessionStorage.setItem(STORAGE_KEY, JSON.stringify(result))
      } catch (_) {}
    }
  }, [result])

  const fetchProjects = async () => {
    try {
      const response = await axios.get('/api/projects')
      const projectNames = response.data.projects.map((p: any) => p.name)
      setProjects(projectNames)
    } catch (error) {
      console.error('获取项目列表失败:', error)
    }
  }

  const handleQuery = async (values: any) => {
    setLoading(true)
    setResult(null)
    
    try {
      const response = await axios.post(
        '/api/mcp/query',
        {
          project: values.project,
          class_fqn: values.class_fqn,
          method: values.method,
          max_depth: values.max_depth || 10
        }
      )
      
      if (response.data.success) {
        setResult(response.data)
        message.success('查询成功')
      } else {
        message.error(response.data.message || '查询失败')
      }
    } catch (error: any) {
      console.error('MCP 查询失败:', error)
      message.error(error.response?.data?.detail || '查询失败')
    } finally {
      setLoading(false)
    }
  }

  // 将 CallNode 转换为 Ant Design Tree DataNode
  const convertToTreeData = (node: CallNode, key: string = '0'): DataNode => {
    const { node_type, project, class_name, method_name, arch_layer } = node
    
    let title: React.ReactNode
    let icon: React.ReactNode
    
    if (node_type === 'method') {
      const layerColor = {
        'Controller': 'blue',
        'Service': 'green',
        'Manager': 'orange',
        'Mapper': 'purple',
        'Other': 'default'
      }[arch_layer || 'Other'] || 'default'
      
      title = (
        <Space>
          <Tag color={layerColor}>{arch_layer || 'Other'}</Tag>
          <Text strong>{project}</Text>
          <Text type="secondary">.</Text>
          <Text>{class_name}</Text>
          <Text type="secondary">.</Text>
          <Text code>{method_name}</Text>
        </Space>
      )
      icon = <FunctionOutlined style={{ color: '#1890ff' }} />
    } else if (node_type === 'interface') {
      title = (
        <Space>
          <Tag color="geekblue">接口</Tag>
          <Text strong>{project}</Text>
          <Text type="secondary">.</Text>
          <Text italic>{class_name}</Text>
          <Text type="secondary">.</Text>
          <Text code>{method_name}</Text>
        </Space>
      )
      icon = <ApiOutlined style={{ color: '#2f54eb' }} />
    } else if (node_type === 'dubbo_call') {
      const interfaceName = node.dubbo_interface?.split('.').pop() || 'Unknown'
      title = (
        <Space>
          <Tag color="red">Dubbo</Tag>
          <Text strong>{interfaceName}</Text>
          <Text type="secondary">.</Text>
          <Text code>{node.dubbo_method}</Text>
          <Text type="secondary" style={{ fontSize: '12px' }}>(via: {node.via_field})</Text>
        </Space>
      )
      icon = <SwapOutlined style={{ color: '#ff4d4f' }} />
    } else if (node_type === 'db_call') {
      title = (
        <Space>
          <Tag color="purple">数据库</Tag>
          <Text strong>{node.table_name}</Text>
          <Text type="secondary" style={{ fontSize: '12px' }}>(Mapper: {node.mapper_name})</Text>
        </Space>
      )
      icon = <DatabaseOutlined style={{ color: '#722ed1' }} />
    } else if (node_type === 'mq') {
      title = (
        <Space>
          <Tag color="orange">MQ</Tag>
          <Text strong>{node.mq_topic}</Text>
          <Text type="secondary">({node.mq_role})</Text>
        </Space>
      )
      icon = <MessageOutlined style={{ color: '#fa8c16' }} />
    } else if (node_type === 'aries_job') {
      title = (
        <Space>
          <Tag color="cyan">Aries Job</Tag>
          <Text strong>{class_name}</Text>
          <Text type="secondary">({node.job_type})</Text>
        </Space>
      )
      icon = <ClockCircleOutlined style={{ color: '#13c2c2' }} />
    } else {
      title = <Text>{class_name}</Text>
      icon = <ApartmentOutlined />
    }
    
    const children = node.children?.map((child, index) => 
      convertToTreeData(child, `${key}-${index}`)
    ) || []
    
    return {
      key,
      title,
      icon,
      children: children.length > 0 ? children : undefined
    }
  }

  const endpointColumns = [
    { title: '项目', dataIndex: 'project', key: 'project', width: 200 },
    { title: '类', dataIndex: 'class_fqn', key: 'class_fqn', width: 300 },
    { title: '方法', dataIndex: 'method', key: 'method', width: 150 },
    { title: 'HTTP 方法', dataIndex: 'http_method', key: 'http_method', width: 100 },
    { title: '路径', dataIndex: 'path', key: 'path', ellipsis: true },
  ]

  const classColumns = [
    { title: '项目', dataIndex: 'project', key: 'project', width: 200 },
    { title: '类名', dataIndex: 'class_name', key: 'class_name', width: 200 },
    { title: '全限定名', dataIndex: 'class_fqn', key: 'class_fqn', ellipsis: true },
    { 
      title: '架构层', 
      dataIndex: 'arch_layer', 
      key: 'arch_layer', 
      width: 120,
      render: (layer: string) => {
        const colorMap: Record<string, string> = {
          'Controller': 'blue',
          'Service': 'green',
          'Manager': 'cyan',
          'Mapper': 'orange',
          'Repository': 'purple',
          'Entity': 'gold'
        }
        return <Tag color={colorMap[layer] || 'default'}>{layer}</Tag>
      }
    },
  ]

  const dubboColumns = [
    { title: '调用项目', dataIndex: 'caller_project', key: 'caller_project', width: 180 },
    { title: '调用类', dataIndex: 'caller_class', key: 'caller_class', width: 250, ellipsis: true },
    { title: '调用方法', dataIndex: 'caller_method', key: 'caller_method', width: 150 },
    { title: 'Dubbo 接口', dataIndex: 'dubbo_interface', key: 'dubbo_interface', width: 250, ellipsis: true },
    { title: 'Dubbo 方法', dataIndex: 'dubbo_method', key: 'dubbo_method', width: 150 },
    { title: '注入字段', dataIndex: 'via_field', key: 'via_field', width: 150 },
  ]

  const tableColumns = [
    { title: '项目', dataIndex: 'project', key: 'project', width: 200 },
    { title: 'Mapper', dataIndex: 'mapper_name', key: 'mapper_name', width: 200 },
    { title: 'Mapper 全路径', dataIndex: 'mapper_fqn', key: 'mapper_fqn', ellipsis: true },
    { title: '表名', dataIndex: 'table_name', key: 'table_name', width: 250 },
  ]

  const jobColumns = [
    { title: '项目', dataIndex: 'project', key: 'project', width: 200 },
    { title: '类名', dataIndex: 'class_name', key: 'class_name', width: 200 },
    { title: '全限定名', dataIndex: 'class_fqn', key: 'class_fqn', ellipsis: true },
    { 
      title: '任务类型', 
      dataIndex: 'job_type', 
      key: 'job_type', 
      width: 120,
      render: (type: string) => <Tag color={type === 'scheduled' ? 'blue' : 'orange'}>{type}</Tag>
    },
    { title: 'Cron 表达式', dataIndex: 'cron_expr', key: 'cron_expr', width: 200 },
  ]

  const mqColumns = [
    { title: '项目', dataIndex: 'project', key: 'project', width: 180 },
    { title: '类名', dataIndex: 'class_name', key: 'class_name', width: 180 },
    { title: '全限定名', dataIndex: 'class_fqn', key: 'class_fqn', ellipsis: true },
    { 
      title: 'MQ 类型', 
      dataIndex: 'mq_type', 
      key: 'mq_type', 
      width: 100,
      render: (type: string) => <Tag color={type === 'kafka' ? 'green' : 'orange'}>{type.toUpperCase()}</Tag>
    },
    { 
      title: '角色', 
      dataIndex: 'role', 
      key: 'role', 
      width: 100,
      render: (role: string) => <Tag color={role === 'consumer' ? 'blue' : 'purple'}>{role}</Tag>
    },
    { title: 'Topic', dataIndex: 'topic', key: 'topic', width: 250 },
    { title: '方法', dataIndex: 'method', key: 'method', width: 150 },
  ]

  return (
    <div className="app-container">
      <Card 
        bordered={false}
      >
        <Form
          form={form}
          layout="inline"
          onFinish={handleQuery}
          style={{ marginBottom: 0 }}
        >
          <Form.Item
            name="project"
            label={<span style={{ color: '#1e293b', fontSize: '15px', fontWeight: 500 }}>项目名称</span>}
            rules={[{ required: true, message: '请选择项目' }]}
            style={{ marginBottom: 0 }}
          >
            <Select
              placeholder="选择项目"
              style={{ width: 250 }}
              showSearch
              filterOption={(input, option) =>
                (option?.children as string)?.toLowerCase().includes(input.toLowerCase())
              }
            >
              {projects.map(p => (
                <Select.Option key={p} value={p}>{p}</Select.Option>
              ))}
            </Select>
          </Form.Item>

          <Form.Item
            name="class_fqn"
            label={<span style={{ color: '#1e293b', fontSize: '15px', fontWeight: 500 }}>类全限定名</span>}
            rules={[{ required: true, message: '请输入类全限定名' }]}
            style={{ marginBottom: 0 }}
          >
            <Input 
              placeholder="com.example.Service" 
              style={{ width: 350 }}
            />
          </Form.Item>

          <Form.Item
            name="method"
            label={<span style={{ color: '#1e293b', fontSize: '15px', fontWeight: 500 }}>方法名</span>}
            rules={[{ required: true, message: '请输入方法名' }]}
            style={{ marginBottom: 0 }}
          >
            <Input 
              placeholder="methodName" 
              style={{ width: 200 }}
            />
          </Form.Item>

          <Form.Item
            name="max_depth"
            label={<span style={{ color: '#1e293b', fontSize: '15px', fontWeight: 500 }}>最大深度</span>}
            initialValue={10}
            style={{ marginBottom: 0 }}
          >
            <Input 
              type="number" 
              placeholder="10" 
              style={{ width: 100 }}
            />
          </Form.Item>

          <Form.Item style={{ marginBottom: 0 }}>
            <Button 
              type="primary" 
              htmlType="submit" 
              icon={<SearchOutlined />}
              loading={loading}
              size="large"
            >
              查询
            </Button>
          </Form.Item>
        </Form>
      </Card>

      {/* 下方统计与 Tab 始终展示：无结果时用空数据，有结果时用查询数据；结果会持久化到 sessionStorage，切换 Tab 或离开再返回不丢失 */}
      <Card 
        style={{ marginTop: 24 }}
        bordered={false}
      >
        <Space direction="vertical" size="large" style={{ width: '100%' }}>
          {/* 统计概览 */}
          <Descriptions 
            bordered 
            column={3}
            size="middle"
            labelStyle={{ 
              fontWeight: 600,
              fontSize: '14px',
              padding: '12px 16px'
            }}
            contentStyle={{ 
              fontSize: '16px',
              fontWeight: 600,
              padding: '12px 16px'
            }}
          >
            <Descriptions.Item label={<><ApiOutlined style={{ marginRight: 8 }} /> 前端入口</>}>
              <span style={{ color: '#60a5fa' }}>{(result?.endpoints ?? EMPTY_RESULT.endpoints).length}</span>
            </Descriptions.Item>
            <Descriptions.Item label={<><CloudOutlined style={{ marginRight: 8 }} /> 内部类</>}>
              <span style={{ color: '#34d399' }}>{(result?.internal_classes ?? EMPTY_RESULT.internal_classes).length}</span>
            </Descriptions.Item>
            <Descriptions.Item label={<><ApiOutlined style={{ marginRight: 8 }} /> Dubbo 调用</>}>
              <span style={{ color: '#fbbf24' }}>{(result?.dubbo_calls ?? EMPTY_RESULT.dubbo_calls).length}</span>
            </Descriptions.Item>
            <Descriptions.Item label={<><DatabaseOutlined style={{ marginRight: 8 }} /> 数据库表</>}>
              <span style={{ color: '#f472b6' }}>{(result?.tables ?? EMPTY_RESULT.tables).length}</span>
            </Descriptions.Item>
            <Descriptions.Item label={<><ClockCircleOutlined style={{ marginRight: 8 }} /> Aries Job</>}>
              <span style={{ color: '#a78bfa' }}>{(result?.aries_jobs ?? EMPTY_RESULT.aries_jobs).length}</span>
            </Descriptions.Item>
            <Descriptions.Item label={<><MessageOutlined style={{ marginRight: 8 }} /> MQ 信息</>}>
              <span style={{ color: '#fb923c' }}>{(result?.mq_info ?? EMPTY_RESULT.mq_info).length}</span>
            </Descriptions.Item>
          </Descriptions>

          {/* 详细结果 Tab：有结果用 result，无结果用 EMPTY_RESULT，切换 Tab 不清除 */}
          <Tabs 
            defaultActiveKey="call-tree"
            type="card"
            destroyInactiveTabPane={false}
          >
            {/* 调用树：有 call_tree 时展示树，无时展示空状态 */}
            <TabPane 
              tab={<span><ApartmentOutlined /> 调用树</span>} 
              key="call-tree"
            >
              {result?.call_tree ? (
                <div style={{ padding: '16px', background: '#fff' }}>
                  <Tree
                    showLine
                    showIcon
                    defaultExpandAll
                    treeData={[convertToTreeData(result.call_tree)]}
                    style={{ fontSize: '14px' }}
                  />
                </div>
              ) : (
                <div className="mcp-empty-tab">请在上方输入条件并点击「查询」后查看调用树</div>
              )}
            </TabPane>

            {/* 调用统计 */}
            <TabPane 
              tab={<span><BarChartOutlined /> 调用统计</span>} 
              key="call-stats"
            >
              {result?.call_tree ? (
                <div className="call-stats-json-wrapper">
                  <JsonView
                    data={collectCallStatistics(result.call_tree, result)}
                    shouldExpandNode={(level: number) => level < 2}
                    style={defaultStyles}
                  />
                </div>
              ) : (
                <div className="mcp-empty-tab">请先完成查询后再查看调用统计</div>
              )}
            </TabPane>

            <TabPane 
              tab={<span><ApiOutlined /> 前端入口 ({(result?.endpoints ?? EMPTY_RESULT.endpoints).length})</span>} 
              key="1"
            >
              <Table
                dataSource={result?.endpoints ?? EMPTY_RESULT.endpoints}
                columns={endpointColumns}
                rowKey={(_, index) => `endpoint-${index}`}
                pagination={false}
                size="middle"
                locale={{ emptyText: '暂无数据，请先查询' }}
              />
            </TabPane>

            <TabPane 
              tab={<span><CloudOutlined /> 内部类 ({(result?.internal_classes ?? EMPTY_RESULT.internal_classes).length})</span>} 
              key="2"
            >
              <Table
                dataSource={result?.internal_classes ?? EMPTY_RESULT.internal_classes}
                columns={classColumns}
                rowKey={(_, index) => `class-${index}`}
                pagination={{ pageSize: 20, showSizeChanger: true, showTotal: (total) => `共 ${total} 条` }}
                size="middle"
                locale={{ emptyText: '暂无数据，请先查询' }}
              />
            </TabPane>

            <TabPane 
              tab={<span><ApiOutlined /> Dubbo 调用 ({(result?.dubbo_calls ?? EMPTY_RESULT.dubbo_calls).length})</span>} 
              key="3"
            >
              <Table
                dataSource={result?.dubbo_calls ?? EMPTY_RESULT.dubbo_calls}
                columns={dubboColumns}
                rowKey={(_, index) => `dubbo-${index}`}
                pagination={{ pageSize: 20, showSizeChanger: true, showTotal: (total) => `共 ${total} 条` }}
                size="middle"
                locale={{ emptyText: '暂无数据，请先查询' }}
              />
            </TabPane>

            <TabPane 
              tab={<span><DatabaseOutlined /> 数据库表 ({(result?.tables ?? EMPTY_RESULT.tables).length})</span>} 
              key="4"
            >
              <Table
                dataSource={result?.tables ?? EMPTY_RESULT.tables}
                columns={tableColumns}
                rowKey={(_, index) => `table-${index}`}
                pagination={{ pageSize: 20, showSizeChanger: true, showTotal: (total) => `共 ${total} 条` }}
                size="middle"
                locale={{ emptyText: '暂无数据，请先查询' }}
              />
            </TabPane>

            <TabPane 
              tab={<span><ClockCircleOutlined /> Aries Job ({(result?.aries_jobs ?? EMPTY_RESULT.aries_jobs).length})</span>} 
              key="5"
            >
              <Table
                dataSource={result?.aries_jobs ?? EMPTY_RESULT.aries_jobs}
                columns={jobColumns}
                rowKey={(_, index) => `job-${index}`}
                pagination={false}
                size="middle"
                locale={{ emptyText: '暂无数据，请先查询' }}
              />
            </TabPane>

            <TabPane 
              tab={<span><MessageOutlined /> MQ 信息 ({(result?.mq_info ?? EMPTY_RESULT.mq_info).length})</span>} 
              key="6"
            >
              <Table
                dataSource={result?.mq_info ?? EMPTY_RESULT.mq_info}
                columns={mqColumns}
                rowKey={(_, index) => `mq-${index}`}
                pagination={{ pageSize: 20, showSizeChanger: true, showTotal: (total) => `共 ${total} 条` }}
                size="middle"
                locale={{ emptyText: '暂无数据，请先查询' }}
              />
            </TabPane>
          </Tabs>
        </Space>
      </Card>
    </div>
  )
}

export default MCPQuery
