import { Card } from 'antd'
import { ApiOutlined } from '@ant-design/icons'

export default function ApiDocs() {
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
            <ApiOutlined style={{ fontSize: '20px', color: '#3b82f6' }} />
            <span>API 文档</span>
          </div>
        }
        style={{
          height: 'calc(100vh - 112px)',
          display: 'flex',
          flexDirection: 'column',
        }}
        bodyStyle={{
          padding: 0,
          flex: 1,
          display: 'flex',
          flexDirection: 'column',
          overflow: 'hidden',
        }}
      >
        <iframe
          src="http://localhost:18000/docs"
          style={{
            width: '100%',
            height: '100%',
            border: 'none',
            flex: 1,
            background: '#ffffff',
          }}
          title="API Documentation"
        />
      </Card>
    </div>
  )
}
