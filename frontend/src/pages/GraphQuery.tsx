import { useState, useEffect, useRef } from 'react'
import { Card, Select, Input, Button, Space, message, Spin, Radio } from 'antd'
import { SearchOutlined } from '@ant-design/icons'
import { useQuery } from '@tanstack/react-query'
import { getProjects } from '../api/projects'
import { getProjectGraph } from '../api/graph'
import { Network } from 'vis-network'
import { DataSet } from 'vis-data'

export default function GraphQuery() {
  const [selectedProject, setSelectedProject] = useState<string>('')
  const [startClass, setStartClass] = useState<string>('')
  const [maxDepth, setMaxDepth] = useState<number>(3)
  const [filterMode, setFilterMode] = useState<string>('moderate')
  const [shouldQuery, setShouldQuery] = useState(false)
  const networkRef = useRef<HTMLDivElement>(null)
  const networkInstance = useRef<Network | null>(null)

  const { data: projectsData } = useQuery({
    queryKey: ['projects'],
    queryFn: getProjects,
  })

  const { data: graphData, isLoading, refetch } = useQuery({
    queryKey: ['projectGraph', selectedProject, startClass, maxDepth, filterMode],
    queryFn: () => getProjectGraph(selectedProject, startClass, maxDepth, filterMode),
    enabled: shouldQuery && !!selectedProject,
  })

  // 当图数据变化时，渲染可视化
  useEffect(() => {
    if (graphData && networkRef.current && graphData.nodes && graphData.edges) {
      const nodes = new DataSet(
        graphData.nodes.map((node: any) => ({
          id: node.id,
          label: node.name,
          title: node.id, // 鼠标悬停显示完整限定名
          shape: 'box',
          color: {
            background: '#3b82f6',
            border: '#1e40af',
            highlight: {
              background: '#60a5fa',
              border: '#1e40af',
            }
          },
          font: {
            color: '#ffffff',
            size: 14,
          }
        }))
      )

      const edges = new DataSet(
        graphData.edges.map((edge: any, index: number) => ({
          id: index,
          from: edge.from,
          to: edge.to,
          arrows: 'to',
          color: {
            color: '#64748b',
            highlight: '#3b82f6',
          },
          smooth: {
            type: 'curvedCW',
            roundness: 0.2,
          }
        }))
      )

      const data = { nodes, edges }

      const options = {
        layout: {
          hierarchical: {
            direction: 'LR', // 从左到右布局
            sortMethod: 'directed',
            levelSeparation: 200,
            nodeSpacing: 150,
          }
        },
        physics: {
          enabled: false, // 禁用物理效果，使用层级布局
        },
        interaction: {
          dragNodes: true,
          dragView: true,
          zoomView: true,
          hover: true,
        },
        nodes: {
          borderWidth: 2,
          borderWidthSelected: 3,
        },
        edges: {
          width: 2,
          selectionWidth: 3,
        }
      }

      // 销毁旧实例
      if (networkInstance.current) {
        networkInstance.current.destroy()
      }

      // 创建新实例
      networkInstance.current = new Network(networkRef.current, data, options)

      // 添加点击事件
      networkInstance.current.on('selectNode', (params) => {
        if (params.nodes.length > 0) {
          const nodeId = params.nodes[0]
          console.log('选中节点:', nodeId)
        }
      })
    }
  }, [graphData])

  const handleSearch = () => {
    if (!selectedProject) {
      message.warning('请先选择项目')
      return
    }
    setShouldQuery(true)
    refetch()
  }

  return (
    <div className="app-container">
      <div className="page-header">
        <h1>🔍 图谱查询</h1>
        <p>查询项目的调用关系和依赖关系</p>
      </div>

      <Card style={{ marginBottom: 24 }}>
        <Space direction="vertical" style={{ width: '100%' }} size="large">
          <div>
            <label style={{ display: 'block', marginBottom: 8, color: '#e2e8f0' }}>
              选择项目
            </label>
            <Select
              style={{ width: '100%' }}
              placeholder="选择项目"
              value={selectedProject}
              onChange={setSelectedProject}
              options={projectsData?.projects?.map((p: any) => ({
                label: p.name,
                value: p.name,
              }))}
            />
          </div>
          <div>
            <label style={{ display: 'block', marginBottom: 8, color: '#e2e8f0' }}>
              起始类（可选）
            </label>
            <Input
              placeholder="输入类名，例如：UserService"
              value={startClass}
              onChange={(e) => setStartClass(e.target.value)}
            />
          </div>
          <div>
            <label style={{ display: 'block', marginBottom: 8, color: '#e2e8f0' }}>
              最大深度
            </label>
            <Select
              style={{ width: '100%' }}
              value={maxDepth}
              onChange={setMaxDepth}
              options={[1, 2, 3, 4, 5].map((d) => ({
                label: `${d} 层`,
                value: d,
              }))}
            />
          </div>
          <div>
            <label style={{ display: 'block', marginBottom: 8, color: '#e2e8f0' }}>
              过滤模式
            </label>
            <Radio.Group 
              value={filterMode} 
              onChange={(e) => setFilterMode(e.target.value)}
              buttonStyle="solid"
            >
              <Radio.Button value="none">不过滤</Radio.Button>
              <Radio.Button value="loose">宽松</Radio.Button>
              <Radio.Button value="moderate">适中（推荐）</Radio.Button>
              <Radio.Button value="strict">严格</Radio.Button>
            </Radio.Group>
            <div style={{ marginTop: 8, fontSize: 12, color: '#94a3b8' }}>
              {filterMode === 'none' && '显示所有依赖，包括工具类和DTO'}
              {filterMode === 'loose' && '只过滤JDK核心类（如String、List等）'}
              {filterMode === 'moderate' && '过滤JDK和常见工具类（推荐使用）'}
              {filterMode === 'strict' && '过滤所有噪音类（包括DTO、Entity等）'}
            </div>
          </div>
          <Button
            type="primary"
            icon={<SearchOutlined />}
            onClick={handleSearch}
            loading={isLoading}
            size="large"
          >
            查询
          </Button>
        </Space>
      </Card>

      {isLoading && (
        <Card>
          <div style={{ textAlign: 'center', padding: '40px' }}>
            <Spin size="large" />
            <p style={{ marginTop: 16, color: '#94a3b8' }}>正在查询图谱数据...</p>
          </div>
        </Card>
      )}

      {graphData && !isLoading && (
        <>
          <Card title="📊 查询结果" style={{ marginBottom: 24 }}>
            <Space size="large">
              <div>
                <span style={{ color: '#94a3b8' }}>节点数：</span>
                <span style={{ color: '#3b82f6', fontSize: 20, fontWeight: 'bold' }}>
                  {graphData.total_nodes}
                </span>
              </div>
              <div>
                <span style={{ color: '#94a3b8' }}>边数：</span>
                <span style={{ color: '#10b981', fontSize: 20, fontWeight: 'bold' }}>
                  {graphData.total_edges}
                </span>
              </div>
              {graphData.filtered_count > 0 && (
                <div>
                  <span style={{ color: '#94a3b8' }}>已过滤：</span>
                  <span style={{ color: '#f59e0b', fontSize: 20, fontWeight: 'bold' }}>
                    {graphData.filtered_count}
                  </span>
                </div>
              )}
            </Space>
          </Card>

          <Card title="🗺️ 调用关系图" style={{ marginBottom: 24 }}>
            <div
              ref={networkRef}
              style={{
                width: '100%',
                height: '600px',
                border: '1px solid #334155',
                borderRadius: '8px',
                background: '#1e293b',
              }}
            />
            <div style={{ marginTop: 16, color: '#94a3b8', fontSize: 12 }}>
              💡 提示：
              <ul style={{ marginTop: 8, paddingLeft: 20 }}>
                <li>拖拽画布移动视图</li>
                <li>滚动鼠标滚轮缩放</li>
                <li>点击节点查看详情</li>
                <li>箭头表示依赖方向</li>
              </ul>
            </div>
          </Card>
        </>
      )}

      {graphData && graphData.total_nodes === 0 && !isLoading && (
        <Card>
          <div style={{ textAlign: 'center', padding: '40px' }}>
            <p style={{ color: '#94a3b8', fontSize: 16 }}>
              未找到相关的依赖关系
            </p>
            <p style={{ color: '#64748b', fontSize: 14, marginTop: 8 }}>
              {startClass ? '请尝试其他类名或不指定起始类' : '该项目可能没有依赖关系数据'}
            </p>
          </div>
        </Card>
      )}
    </div>
  )
}
