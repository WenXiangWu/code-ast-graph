import { Routes, Route } from 'react-router-dom'
import { Layout } from 'antd'
import AppHeader from './components/AppHeader'
import ProjectManagement from './pages/ProjectManagement'
import GraphVisualization from './pages/GraphVisualization'
import MCPQuery from './pages/MCPQuery'
import ApiDocs from './pages/ApiDocs'
import './App.css'

const { Content } = Layout

function App() {
  return (
    <Layout style={{ minHeight: '100vh' }}>
      <AppHeader />
      <Content style={{ padding: '24px 32px', background: '#f1f5f9' }}>
        <Routes>
          <Route path="/" element={<ProjectManagement />} />
          <Route path="/visualization" element={<GraphVisualization />} />
          <Route path="/mcp" element={<MCPQuery />} />
          <Route path="/api-docs" element={<ApiDocs />} />
        </Routes>
      </Content>
    </Layout>
  )
}

export default App
