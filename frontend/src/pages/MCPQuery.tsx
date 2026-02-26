import { useState, useEffect } from 'react'
import { Card, Form, Input, Button, Select, message, Descriptions, Table, Tag, Tabs, Space, Typography, Tree } from 'antd'
import { SearchOutlined, ApiOutlined, DatabaseOutlined, CloudOutlined, ClockCircleOutlined, MessageOutlined, ApartmentOutlined, FunctionOutlined, SwapOutlined } from '@ant-design/icons'
import type { DataNode } from 'antd/es/tree'
import axios from 'axios'
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

function MCPQuery() {
  const [form] = Form.useForm()
  const [projects, setProjects] = useState<string[]>([])
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<MCPQueryResult | null>(null)

  useEffect(() => {
    fetchProjects()
  }, [])

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

      {result && result.success && (
        <Card 
          style={{ 
            marginTop: 24,
          }}
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
                <span style={{ color: '#60a5fa' }}>{result.endpoints.length}</span>
              </Descriptions.Item>
              <Descriptions.Item label={<><CloudOutlined style={{ marginRight: 8 }} /> 内部类</>}>
                <span style={{ color: '#34d399' }}>{result.internal_classes.length}</span>
              </Descriptions.Item>
              <Descriptions.Item label={<><ApiOutlined style={{ marginRight: 8 }} /> Dubbo 调用</>}>
                <span style={{ color: '#fbbf24' }}>{result.dubbo_calls.length}</span>
              </Descriptions.Item>
              <Descriptions.Item label={<><DatabaseOutlined style={{ marginRight: 8 }} /> 数据库表</>}>
                <span style={{ color: '#f472b6' }}>{result.tables.length}</span>
              </Descriptions.Item>
              <Descriptions.Item label={<><ClockCircleOutlined style={{ marginRight: 8 }} /> Aries Job</>}>
                <span style={{ color: '#a78bfa' }}>{result.aries_jobs.length}</span>
              </Descriptions.Item>
              <Descriptions.Item label={<><MessageOutlined style={{ marginRight: 8 }} /> MQ 信息</>}>
                <span style={{ color: '#fb923c' }}>{result.mq_info.length}</span>
              </Descriptions.Item>
            </Descriptions>

            {/* 详细结果 */}
            <Tabs 
              defaultActiveKey="call-tree"
              type="card"
            >
              {/* 新增：调用树 Tab */}
              {result.call_tree && (
                <TabPane 
                  tab={<span><ApartmentOutlined /> 调用树</span>} 
                  key="call-tree"
                >
                  <div style={{ padding: '16px', background: '#fff' }}>
                    <Tree
                      showLine
                      showIcon
                      defaultExpandAll
                      treeData={[convertToTreeData(result.call_tree)]}
                      style={{ fontSize: '14px' }}
                    />
                  </div>
                </TabPane>
              )}

              <TabPane 
                tab={<span><ApiOutlined /> 前端入口 ({result.endpoints.length})</span>} 
                key="1"
              >
                <Table
                  dataSource={result.endpoints}
                  columns={endpointColumns}
                  rowKey={(record, index) => `endpoint-${index}`}
                  pagination={false}
                  size="middle"
                  locale={{ emptyText: '暂无数据' }}
                />
              </TabPane>

              <TabPane 
                tab={<span><CloudOutlined /> 内部类 ({result.internal_classes.length})</span>} 
                key="2"
              >
                <Table
                  dataSource={result.internal_classes}
                  columns={classColumns}
                  rowKey={(record, index) => `class-${index}`}
                  pagination={{ pageSize: 20, showSizeChanger: true, showTotal: (total) => `共 ${total} 条` }}
                  size="middle"
                  locale={{ emptyText: '暂无数据' }}
                />
              </TabPane>

              <TabPane 
                tab={<span><ApiOutlined /> Dubbo 调用 ({result.dubbo_calls.length})</span>} 
                key="3"
              >
                <Table
                  dataSource={result.dubbo_calls}
                  columns={dubboColumns}
                  rowKey={(record, index) => `dubbo-${index}`}
                  pagination={{ pageSize: 20, showSizeChanger: true, showTotal: (total) => `共 ${total} 条` }}
                  size="middle"
                  locale={{ emptyText: '暂无数据' }}
                />
              </TabPane>

              <TabPane 
                tab={<span><DatabaseOutlined /> 数据库表 ({result.tables.length})</span>} 
                key="4"
              >
                <Table
                  dataSource={result.tables}
                  columns={tableColumns}
                  rowKey={(record, index) => `table-${index}`}
                  pagination={{ pageSize: 20, showSizeChanger: true, showTotal: (total) => `共 ${total} 条` }}
                  size="middle"
                  locale={{ emptyText: '暂无数据' }}
                />
              </TabPane>

              <TabPane 
                tab={<span><ClockCircleOutlined /> Aries Job ({result.aries_jobs.length})</span>} 
                key="5"
              >
                <Table
                  dataSource={result.aries_jobs}
                  columns={jobColumns}
                  rowKey={(record, index) => `job-${index}`}
                  pagination={false}
                  size="middle"
                  locale={{ emptyText: '暂无数据' }}
                />
              </TabPane>

              <TabPane 
                tab={<span><MessageOutlined /> MQ 信息 ({result.mq_info.length})</span>} 
                key="6"
              >
                <Table
                  dataSource={result.mq_info}
                  columns={mqColumns}
                  rowKey={(record, index) => `mq-${index}`}
                  pagination={{ pageSize: 20, showSizeChanger: true, showTotal: (total) => `共 ${total} 条` }}
                  size="middle"
                  locale={{ emptyText: '暂无数据' }}
                />
              </TabPane>
            </Tabs>
          </Space>
        </Card>
      )}
    </div>
  )
}

export default MCPQuery
