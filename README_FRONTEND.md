# Code AST Graph - 前端项目

## 技术栈

- **React 18** - UI 框架
- **TypeScript** - 类型安全
- **Vite** - 构建工具
- **Ant Design 5** - UI 组件库
- **React Router** - 路由管理
- **TanStack Query** - 数据获取和缓存
- **Vis Network** - 图形可视化
- **Zustand** - 状态管理（如需要）

## 快速开始

### 安装依赖

```bash
cd frontend
npm install
```

### 启动开发服务器

```bash
npm run dev
```

前端将在 http://localhost:3000 启动

### 构建生产版本

```bash
npm run build
```

## 项目结构

```
frontend/
├── src/
│   ├── api/          # API 调用
│   ├── components/   # 可复用组件
│   ├── pages/        # 页面组件
│   ├── types/        # TypeScript 类型定义
│   ├── App.tsx       # 主应用组件
│   └── main.tsx      # 入口文件
├── public/           # 静态资源
├── index.html        # HTML 模板
├── package.json      # 依赖配置
├── tsconfig.json     # TypeScript 配置
└── vite.config.ts    # Vite 配置
```

## 页面说明

1. **项目管理** (`/`) - 项目列表、扫描、统计
2. **图谱查询** (`/query`) - 查询调用关系和依赖
3. **可视化** (`/visualization`) - 图形可视化展示

## 后端 API

前端通过 `/api` 代理到后端服务（http://localhost:8000）
