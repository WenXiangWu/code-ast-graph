import { useState, useEffect } from 'react'
import { Card, Button, Space, message, Spin, Tabs, Statistic, Row, Col, Alert, Tooltip, Tag } from 'antd'
import { DatabaseOutlined, ReloadOutlined, LinkOutlined, QuestionCircleOutlined, CloseCircleOutlined } from '@ant-design/icons'
import axios from 'axios'

const { TabPane } = Tabs

// 节点类型说明
const NODE_TYPE_DESCRIPTIONS: Record<string, string> = {
  'Method': '方法节点 - 表示类中的方法定义',
  'CLASS': '类节点 - 表示 Java 类（非接口、非 Mapper）',
  'INTERFACE': '接口节点 - 表示 Java 接口定义',
  'MAPPER': 'Mapper 节点 - 表示 MyBatis Mapper 类（数据库访问层）',
  'Table': '数据库表节点 - 表示数据库中的表',
  'Project': '项目节点 - 表示一个代码仓库项目',
  'MQ_TOPIC': '消息队列主题节点 - 表示 Kafka/RocketMQ 的 Topic',
  'ARIES_JOB': 'Aries 任务节点 - 表示定时任务或延时任务',
  'RpcEndpoint': 'RPC 端点节点 - 表示对外暴露的 API 接口（HTTP/Dubbo）',
  'Field': '字段节点 - 表示类的成员变量',
}

// 关系类型说明
const RELATIONSHIP_TYPE_DESCRIPTIONS: Record<string, string> = {
  'DECLARES': '声明关系 - 类声明方法（CLASS/INTERFACE -> Method）',
  'CALLS': '调用关系 - 方法调用其他方法（Method -> Method）',
  'CONTAINS': '包含关系 - 项目包含类（Project -> CLASS/INTERFACE/MAPPER）',
  'IMPLEMENTS': '实现关系 - 类实现接口（CLASS -> INTERFACE）',
  'DUBBO_CALLS': 'Dubbo 调用关系 - 跨项目的 RPC 调用（Method -> Method）',
  'DB_CALL': '数据库调用关系 - Mapper 方法访问数据库表（Method -> Table）',
  'EXPOSES': '暴露关系 - 方法暴露为 RPC 端点（Method -> RpcEndpoint）',
  'PRODUCES': '生产关系 - 方法发送消息到 MQ（Method -> MQ_TOPIC）',
  'CONSUMES': '消费关系 - 方法消费 MQ 消息（Method -> MQ_TOPIC）',
  'SCHEDULES': '调度关系 - Aries Job 调度方法执行（ARIES_JOB -> Method）',
  'HAS_FIELD': '字段关系 - 类拥有字段（CLASS -> Field）',
}

interface GraphStats {
  total_nodes: number
  total_relationships: number
  node_labels: Record<string, number>
  relationship_types: Record<string, number>
  projects: string[]
  selected_project?: string
}

export default function GraphVisualization() {
  const [loading, setLoading] = useState(false)
  const [stats, setStats] = useState<GraphStats | null>(null)
  const [selectedProject, setSelectedProject] = useState<string | null>(null)

  useEffect(() => {
    fetchStats()
  }, [])

  const fetchStats = async (project?: string | null) => {
    setLoading(true)
    try {
      const url = project ? `/api/graph/stats?project=${encodeURIComponent(project)}` : '/api/graph/stats'
      const response = await axios.get(url)
      setStats(response.data)
      setSelectedProject(project || null)
    } catch (error) {
      console.error('获取图谱统计失败:', error)
      message.error('获取图谱统计失败')
    } finally {
      setLoading(false)
    }
  }

  const handleProjectClick = (project: string) => {
    if (selectedProject === project) {
      // 如果点击的是当前选中的项目，则取消筛选
      fetchStats(null)
    } else {
      // 否则筛选该项目
      fetchStats(project)
    }
  }

  const handleClearFilter = () => {
    fetchStats(null)
  }

  const openNeo4jBrowser = () => {
    window.open('http://localhost:17474/browser/', '_blank')
  }

  return (
    <div className="app-container">
      <Card
        title={
          <div style={{ 
            display: 'flex', 
            alignItems: 'center', 
            gap: '12px',
            fontSize: '17px',
            fontWeight: 600,
          }}>
            <DatabaseOutlined style={{ fontSize: '20px', color: '#3b82f6' }} />
            <span>图谱设计</span>
            {selectedProject && (
              <Tag 
                color="blue" 
                closable
                onClose={(e) => {
                  e.preventDefault()
                  handleClearFilter()
                }}
                style={{ fontSize: '14px', padding: '2px 8px' }}
              >
                筛选: {selectedProject}
              </Tag>
            )}
          </div>
        }
        extra={
          <Space>
            {selectedProject && (
              <Button 
                icon={<CloseCircleOutlined />} 
                onClick={handleClearFilter}
              >
                清除筛选
              </Button>
            )}
            <Button 
              icon={<ReloadOutlined />} 
              onClick={() => fetchStats(selectedProject)}
              loading={loading}
            >
              刷新统计
            </Button>
            <Button 
              type="primary"
              icon={<LinkOutlined />} 
              onClick={openNeo4jBrowser}
            >
              打开 Neo4j Browser
            </Button>
          </Space>
        }
      >
        <Spin spinning={loading}>
          {stats ? (
            <Space direction="vertical" size="large" style={{ width: '100%' }}>
              {/* 整体统计 */}
              <Card title="📊 图谱统计概览" size="small">
                <Row gutter={[16, 16]}>
                  <Col span={6}>
                    <Statistic 
                      title="节点总数" 
                      value={stats.total_nodes}
                      valueStyle={{ color: '#3b82f6', fontSize: '24px' }}
                    />
                  </Col>
                  <Col span={6}>
                    <Statistic 
                      title="关系总数" 
                      value={stats.total_relationships}
                      valueStyle={{ color: '#10b981', fontSize: '24px' }}
                    />
                  </Col>
                  <Col span={6}>
                    <Statistic 
                      title="节点类型" 
                      value={Object.keys(stats.node_labels).length}
                      valueStyle={{ color: '#f59e0b', fontSize: '24px' }}
                    />
                  </Col>
                  <Col span={6}>
                    <Statistic 
                      title="关系类型" 
                      value={Object.keys(stats.relationship_types).length}
                      valueStyle={{ color: '#8b5cf6', fontSize: '24px' }}
                    />
                  </Col>
                </Row>
              </Card>

              {/* 项目列表 */}
              {stats.projects.length > 0 && (
                <Card title="📦 已构建项目" size="small">
                  <Row gutter={[16, 16]}>
                    {stats.projects.map((project) => {
                      const isSelected = selectedProject === project
                      return (
                        <Col span={8} key={project}>
                          <div 
                            onClick={() => handleProjectClick(project)}
                            style={{ 
                              padding: '16px',
                              background: isSelected ? '#eff6ff' : '#f8fafc',
                              borderRadius: '8px',
                              border: isSelected ? '2px solid #3b82f6' : '1px solid #e2e8f0',
                              fontSize: '15px',
                              fontWeight: isSelected ? 600 : 500,
                              textAlign: 'center',
                              cursor: 'pointer',
                              transition: 'all 0.2s ease',
                              color: isSelected ? '#3b82f6' : '#1e293b',
                            }}
                            onMouseEnter={(e) => {
                              if (!isSelected) {
                                e.currentTarget.style.background = '#f1f5f9'
                                e.currentTarget.style.borderColor = '#cbd5e1'
                              }
                            }}
                            onMouseLeave={(e) => {
                              if (!isSelected) {
                                e.currentTarget.style.background = '#f8fafc'
                                e.currentTarget.style.borderColor = '#e2e8f0'
                              }
                            }}
                          >
                            {project}
                            {isSelected && (
                              <div style={{ 
                                marginTop: '4px', 
                                fontSize: '12px', 
                                color: '#3b82f6',
                                fontWeight: 400,
                              }}>
                                ✓ 已选中
                              </div>
                            )}
                          </div>
                        </Col>
                      )
                    })}
                  </Row>
                </Card>
              )}

              {/* 详细统计 */}
              <Tabs defaultActiveKey="1" size="large">
                <TabPane tab={`节点类型分布 (${Object.keys(stats.node_labels).length})`} key="1">
                  <Row gutter={[16, 16]}>
                    {Object.entries(stats.node_labels)
                      .sort(([, a], [, b]) => b - a)
                      .map(([label, count]) => (
                        <Col span={12} key={label}>
                          <div style={{ 
                            display: 'flex', 
                            justifyContent: 'space-between',
                            alignItems: 'center',
                            padding: '16px 20px',
                            background: '#f8fafc',
                            borderRadius: '8px',
                            border: '1px solid #e2e8f0',
                          }}>
                            <Space size="small">
                              <span style={{ fontWeight: 600, fontSize: '15px' }}>{label}</span>
                              {NODE_TYPE_DESCRIPTIONS[label] && (
                                <Tooltip title={NODE_TYPE_DESCRIPTIONS[label]} placement="right">
                                  <QuestionCircleOutlined style={{ 
                                    color: '#94a3b8', 
                                    fontSize: '14px',
                                    cursor: 'help',
                                  }} />
                                </Tooltip>
                              )}
                            </Space>
                            <span style={{ 
                              color: '#3b82f6', 
                              fontWeight: 700,
                              fontSize: '18px',
                            }}>
                              {count.toLocaleString()}
                            </span>
                          </div>
                        </Col>
                      ))}
                  </Row>
                </TabPane>

                <TabPane tab={`关系类型分布 (${Object.keys(stats.relationship_types).length})`} key="2">
                  <Row gutter={[16, 16]}>
                    {Object.entries(stats.relationship_types)
                      .sort(([, a], [, b]) => b - a)
                      .map(([type, count]) => (
                        <Col span={12} key={type}>
                          <div style={{ 
                            display: 'flex', 
                            justifyContent: 'space-between',
                            alignItems: 'center',
                            padding: '16px 20px',
                            background: '#f8fafc',
                            borderRadius: '8px',
                            border: '1px solid #e2e8f0',
                          }}>
                            <Space size="small">
                              <span style={{ fontWeight: 600, fontSize: '15px' }}>{type}</span>
                              {RELATIONSHIP_TYPE_DESCRIPTIONS[type] && (
                                <Tooltip title={RELATIONSHIP_TYPE_DESCRIPTIONS[type]} placement="right">
                                  <QuestionCircleOutlined style={{ 
                                    color: '#94a3b8', 
                                    fontSize: '14px',
                                    cursor: 'help',
                                  }} />
                                </Tooltip>
                              )}
                            </Space>
                            <span style={{ 
                              color: '#10b981', 
                              fontWeight: 700,
                              fontSize: '18px',
                            }}>
                              {count.toLocaleString()}
                            </span>
                          </div>
                        </Col>
                      ))}
                  </Row>
                </TabPane>
              </Tabs>
            </Space>
          ) : (
            <div style={{ textAlign: 'center', padding: '60px' }}>
              <DatabaseOutlined style={{ fontSize: '48px', color: '#cbd5e1', marginBottom: '16px' }} />
              <p style={{ fontSize: '16px', color: '#64748b' }}>暂无数据，请先在项目管理中导入项目</p>
            </div>
          )}
        </Spin>
      </Card>
    </div>
  )
}
