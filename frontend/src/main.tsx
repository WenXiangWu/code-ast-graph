import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { ConfigProvider } from 'antd'
import zhCN from 'antd/locale/zh_CN'
import App from './App'
import './index.css'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
    },
  },
})

// 主题定制：放大字体、优化圆角与间距
const theme = {
  token: {
    fontSize: 15,
    fontSizeHeading1: 28,
    fontSizeHeading2: 22,
    fontSizeHeading3: 18,
    fontSizeHeading4: 16,
    fontSizeHeading5: 15,
    borderRadius: 8,
    colorText: '#1e293b',
    colorPrimary: '#2563eb',
  },
  components: {
    Table: {
      fontSize: 15,
      headerBg: '#f8fafc',
      headerColor: '#334155',
    },
    Button: {
      fontSize: 15,
      controlHeight: 36,
    },
    Card: {
      headerFontSize: 17,
    },
    Input: {
      fontSize: 15,
    },
  },
}

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <ConfigProvider locale={zhCN} theme={theme}>
        <BrowserRouter>
          <App />
        </BrowserRouter>
      </ConfigProvider>
    </QueryClientProvider>
  </React.StrictMode>,
)
