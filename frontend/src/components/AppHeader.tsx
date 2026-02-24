import { Layout, Menu } from 'antd'
import { useNavigate, useLocation } from 'react-router-dom'
import { ProjectOutlined, SearchOutlined, NodeIndexOutlined } from '@ant-design/icons'

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
    label: '可视化',
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
      padding: '0 24px'
    }}>
      <div style={{ 
        color: '#e2e8f0', 
        fontSize: '20px', 
        fontWeight: 'bold',
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
          flex: 1
        }}
      />
    </Header>
  )
}
