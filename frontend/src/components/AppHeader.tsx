import { Layout, Menu } from 'antd'
import { useNavigate, useLocation } from 'react-router-dom'
import { ProjectOutlined, SearchOutlined, NodeIndexOutlined, ApiOutlined, FileTextOutlined } from '@ant-design/icons'

const { Header } = Layout

const menuItems = [
  {
    key: '/',
    icon: <ProjectOutlined />,
    label: '项目管理',
  },
  {
    key: '/query',
    icon: <SearchOutlined />,
    label: '图谱查询',
  },
  {
    key: '/visualization',
    icon: <NodeIndexOutlined />,
    label: '图谱设计',
  },
  {
    key: '/mcp',
    icon: <ApiOutlined />,
    label: 'MCP 查询',
  },
  {
    key: '/api-docs',
    icon: <FileTextOutlined />,
    label: 'API Docs',
  },
]

export default function AppHeader() {
  const navigate = useNavigate()
  const location = useLocation()

  return (
    <Header style={{ 
      background: '#1e293b', 
      borderBottom: '1px solid #334155',
      display: 'flex',
      alignItems: 'center',
      padding: '0 24px',
      height: 64,
      minHeight: 64,
    }}>
      <div style={{ 
        color: '#e2e8f0', 
        fontSize: '22px', 
        fontWeight: 600,
        marginRight: '48px'
      }}>
        🗺️ Code AST Graph
      </div>
      <Menu
        theme="dark"
        mode="horizontal"
        selectedKeys={[location.pathname]}
        items={menuItems}
        onClick={({ key }) => navigate(key)}
        style={{ 
          background: 'transparent',
          borderBottom: 'none',
          flex: 1,
          fontSize: 18,
          minHeight: 64,
          lineHeight: '64px',
        }}
      />
    </Header>
  )
}
