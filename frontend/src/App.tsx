import { Routes, Route } from 'react-router-dom'
import { Layout } from 'antd'
import AppHeader from './components/AppHeader'
import ProjectManagement from './pages/ProjectManagement'
import GraphQuery from './pages/GraphQuery'
import GraphVisualization from './pages/GraphVisualization'
import './App.css'

const { Content } = Layout

function App() {
  return (
    <Layout style={{ minHeight: '100vh' }}>
      <AppHeader />
      <Content style={{ padding: '24px', background: '#0f172a' }}>
        <Routes>
          <Route path="/" element={<ProjectManagement />} />
          <Route path="/query" element={<GraphQuery />} />
          <Route path="/visualization" element={<GraphVisualization />} />
        </Routes>
      </Content>
    </Layout>
  )
}

export default App
