import { useEffect, useRef } from 'react'
import { Card } from 'antd'
import { Network } from 'vis-network'
import { DataSet } from 'vis-data'

export default function GraphVisualization() {
  const networkRef = useRef<HTMLDivElement>(null)
  const networkInstanceRef = useRef<Network | null>(null)

  useEffect(() => {
    if (!networkRef.current) return

    // 示例数据
    const nodes = new DataSet([
      { id: 1, label: 'Node 1' },
      { id: 2, label: 'Node 2' },
      { id: 3, label: 'Node 3' },
    ])

    const edges = new DataSet([
      { from: 1, to: 2 },
      { from: 2, to: 3 },
    ])

    const data = { nodes, edges }
    const options = {
      nodes: {
        color: {
          background: '#6366f1',
          border: '#4f46e5',
        },
        font: {
          color: '#e2e8f0',
        },
      },
      edges: {
        color: '#94a3b8',
      },
      physics: {
        enabled: true,
      },
    }

    const network = new Network(networkRef.current, data, options)
    networkInstanceRef.current = network

    return () => {
      if (networkInstanceRef.current) {
        networkInstanceRef.current.destroy()
      }
    }
  }, [])

  return (
    <div className="app-container">
      <div className="page-header">
        <h1>📊 图谱可视化</h1>
        <p>可视化项目的知识图谱结构</p>
      </div>

      <Card>
        <div
          ref={networkRef}
          style={{
            width: '100%',
            height: '600px',
            background: '#1e293b',
            borderRadius: '8px',
          }}
        />
      </Card>
    </div>
  )
}
