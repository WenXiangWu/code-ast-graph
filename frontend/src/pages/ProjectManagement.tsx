import { useState, useRef, useEffect } from 'react'
import {
  Card,
  Table,
  Button,
  Input,
  Space,
  message,
  Statistic,
  Row,
  Col,
  Modal,
  Form,
  Tag,
  Tooltip,
  Popconfirm,
} from 'antd'
import {
  ReloadOutlined,
  BuildOutlined,
  DownloadOutlined,
  CheckCircleOutlined,
  DeleteOutlined,
} from '@ant-design/icons'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  getRepos,
  cloneRepo,
  scanProject,
  getScanTaskStatus,
  deleteProjectGraph,
  deleteRepo,
  getProjectStats,
} from '../api/projects'
import type { RepoItem } from '../api/projects'

export default function ProjectManagement() {
  const [selectedProject, setSelectedProject] = useState<string>('')
  const [cloneModalVisible, setCloneModalVisible] = useState(false)
  const statsCardRef = useRef<HTMLDivElement>(null)
  const [buildingRepo, setBuildingRepo] = useState<string | null>(null)
  const [form] = Form.useForm()
  const queryClient = useQueryClient()

  // 获取仓库列表（git-repos + Neo4j 构建信息）
  const { data: reposData, isLoading, isError, error, refetch } = useQuery({
    queryKey: ['repos'],
    queryFn: getRepos,
    retry: 1,
  })

  // 获取项目统计（仅对已构建项目生效）
  const { data: stats, isFetching: statsLoading, isError: statsError, error: statsErrorDetail, refetch: refetchStats } = useQuery({
    queryKey: ['projectStats', selectedProject],
    queryFn: () => getProjectStats(selectedProject),
    enabled: !!selectedProject,
    retry: 1,
  })

  // 统计数据加载完成后滚动到统计卡片
  useEffect(() => {
    if (selectedProject && stats && statsCardRef.current) {
      statsCardRef.current.scrollIntoView({ behavior: 'smooth', block: 'nearest' })
    }
  }, [selectedProject, stats])

  // 克隆仓库
  const cloneMutation = useMutation({
    mutationFn: ({ gitUrl, branch }: { gitUrl: string; branch: string }) =>
      cloneRepo(gitUrl, branch),
    onSuccess: (data) => {
      if (data.success) {
        message.success('克隆成功')
        setCloneModalVisible(false)
        form.resetFields()
      } else {
        message.error(data.message || '克隆失败')
      }
      queryClient.invalidateQueries({ queryKey: ['repos'] })
    },
    onError: (error: any) => {
      message.error(error.response?.data?.detail || '克隆失败')
    },
  })

  // 构建图谱（异步：启动后轮询）
  const scanMutation = useMutation({
    mutationFn: async ({
      projectName,
      projectPath,
      force,
    }: {
      projectName: string
      projectPath: string
      force: boolean
    }) => {
      const data = await scanProject(projectName, projectPath, force)
      if (!data.success && !data.task_id) {
        throw new Error(data.message || '构建启动失败')
      }
      const taskId = data.task_id
      if (taskId) {
        // 异步模式：轮询直到完成
        return new Promise<void>((resolve, reject) => {
          const pollOnce = async () => {
            const status = await getScanTaskStatus(taskId)
            if (status.status === 'completed') {
              resolve()
            } else if (status.status === 'failed') {
              reject(new Error(status.error || '构建失败'))
            } else {
              setTimeout(pollOnce, 2000)
            }
          }
          pollOnce()
        })
      }
      return data
    },
    onMutate: ({ projectName }) => {
      setBuildingRepo(projectName)
      message.loading({ content: '构建中，大项目可能需要数分钟，请耐心等待…', key: 'build', duration: 0 })
    },
    onSuccess: () => {
      message.success({ content: '知识图谱构建完成', key: 'build' })
      queryClient.invalidateQueries({ queryKey: ['repos'] })
    },
    onError: (error: any) => {
      message.error({ content: error.message || error.response?.data?.detail || '构建失败', key: 'build' })
    },
    onSettled: () => {
      setBuildingRepo(null)
    },
  })

  // 删除图
  const deleteGraphMutation = useMutation({
    mutationFn: deleteProjectGraph,
    onSuccess: (data) => {
      if (data.success) {
        message.success('图谱已删除')
        queryClient.invalidateQueries({ queryKey: ['repos'] })
      } else {
        message.error(data.message || '删除失败')
      }
    },
    onError: (error: any) => {
      message.error(error.response?.data?.detail || '删除失败')
    },
  })

  // 删除本地仓库
  const deleteRepoMutation = useMutation({
    mutationFn: deleteRepo,
    onSuccess: (data) => {
      if (data.success) {
        message.success('本地仓库已删除')
        queryClient.invalidateQueries({ queryKey: ['repos'] })
      } else {
        message.error(data.message || '删除失败')
      }
    },
    onError: (error: any) => {
      message.error(error.response?.data?.detail || '删除失败')
    },
  })

  const handleClone = (values: { gitUrl: string; branch?: string }) => {
    cloneMutation.mutate({
      gitUrl: values.gitUrl,
      branch: values.branch || 'master',
    })
  }

  const handleBuild = (repo: RepoItem) => {
    scanMutation.mutate({
      projectName: repo.name,
      projectPath: repo.path,
      force: true,
    })
  }

  const formatTime = (v: string) => {
    if (!v) return '—'
    const s = String(v).trim()
    // 过长时截取 YYYY-MM-DD HH:mm:ss 部分展示，完整内容放 Tooltip
    if (s.length > 22) {
      const m = s.match(/^(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}(?::\d{2})?)/)
      return m ? m[1] : s.slice(0, 19)
    }
    return s
  }

  const columns = [
    {
      title: '项目名称',
      dataIndex: 'name',
      key: 'name',
      align: 'left' as const,
      ellipsis: true,
      render: (text: string, record: RepoItem) => (
        <Space wrap style={{ maxWidth: 200 }}>
          <span>{text}</span>
          {record.scanned_commit_id && record.current_commit_id === record.scanned_commit_id && (
            <Tag color="success" icon={<CheckCircleOutlined />}>
              已同步
            </Tag>
          )}
        </Space>
      ),
    },
    {
      title: '当前 Commit',
      dataIndex: 'current_commit_id',
      key: 'current_commit_id',
      align: 'left' as const,
      width: 120,
      ellipsis: { showTitle: false },
      render: (v: string) =>
        v ? (
          <Tooltip title={v}>
            <code style={{ fontSize: 14 }}>{v.slice(0, 8)}</code>
          </Tooltip>
        ) : (
          <span style={{ color: '#999' }}>—</span>
        ),
    },
    {
      title: '当前 Commit 时间',
      dataIndex: 'current_commit_time',
      key: 'current_commit_time',
      align: 'left' as const,
      ellipsis: { showTitle: false },
      render: (v: string) => {
        const display = formatTime(v)
        return v ? (
          <Tooltip title={v}>
            <span>{display}</span>
          </Tooltip>
        ) : (
          <span style={{ color: '#999' }}>—</span>
        )
      },
    },
    {
      title: '构建状态',
      dataIndex: 'scanned_commit_id',
      key: 'build_status',
      align: 'center' as const,
      width: 100,
      render: (v: string) =>
        v ? (
          <Tag color="success" icon={<CheckCircleOutlined />}>
            已构建
          </Tag>
        ) : (
          <Tag color="default">未构建</Tag>
        ),
    },
    {
      title: '构建时 Commit',
      dataIndex: 'scanned_commit_id',
      key: 'scanned_commit_id',
      align: 'left' as const,
      width: 120,
      ellipsis: { showTitle: false },
      render: (v: string) =>
        v ? (
          <Tooltip title={v}>
            <code style={{ fontSize: 14 }}>{v.slice(0, 8)}</code>
          </Tooltip>
        ) : (
          <span style={{ color: '#999' }}>无</span>
        ),
    },
    {
      title: '构建时间',
      dataIndex: 'scanned_at',
      key: 'scanned_at',
      align: 'left' as const,
      ellipsis: { showTitle: false },
      render: (v: string, record: RepoItem) => {
        if (!record.scanned_commit_id) return <span style={{ color: '#999' }}>—</span>
        const display = formatTime(v)
        return v ? (
          <Tooltip title={v}>
            <span>{display}</span>
          </Tooltip>
        ) : (
          <span style={{ color: '#999' }}>—</span>
        )
      },
    },
    {
      title: '操作',
      key: 'action',
      align: 'left' as const,
      width: 420,
      render: (_: any, record: RepoItem) => (
        <Space size="small" wrap={false} style={{ flexWrap: 'nowrap' }}>
          <Tooltip title={!record.scanned_commit_id ? '请先构建项目后再查看统计' : ''}>
            <span>
              <Button
                size="middle"
                onClick={() => setSelectedProject(record.name)}
                loading={statsLoading && selectedProject === record.name}
                disabled={!record.scanned_commit_id}
              >
                统计
              </Button>
            </span>
          </Tooltip>
          <Tooltip
            title={
              buildingRepo === record.name
                ? '构建中，请耐心等待'
                : record.can_build
                  ? '当前代码与构建版本不一致，点击重新构建'
                  : '当前代码已构建，无需重新构建'
            }
          >
            <span>
              <Button
                type="primary"
                size="middle"
                icon={<BuildOutlined />}
                disabled={!record.can_build || buildingRepo === record.name}
                loading={buildingRepo === record.name}
                onClick={() => handleBuild(record)}
              >
                {buildingRepo === record.name ? '构建中' : '构建'}
              </Button>
            </span>
          </Tooltip>
          {record.scanned_commit_id ? (
            <Popconfirm
              title="确定删除该项目的知识图谱？"
              onConfirm={() => deleteGraphMutation.mutate(record.name)}
            >
              <Button
                size="middle"
                danger
                icon={<DeleteOutlined />}
                disabled={deleteGraphMutation.isPending}
              >
                删除图
              </Button>
            </Popconfirm>
          ) : null}
          <Popconfirm
            title="确定删除本地仓库？此操作不可恢复"
            onConfirm={() => deleteRepoMutation.mutate(record.name)}
          >
            <Button
              size="middle"
              danger
              icon={<DeleteOutlined />}
              disabled={deleteRepoMutation.isPending}
            >
              删除本地仓库
            </Button>
          </Popconfirm>
        </Space>
      ),
    },
  ]

  const repos = reposData?.repos || []

  return (
    <div className="app-container">
      <Card
        title="已克隆项目"
        extra={
          <Space size="middle">
            <Button
              size="large"
              icon={<ReloadOutlined />}
              onClick={() =>
                queryClient.invalidateQueries({ queryKey: ['repos'] })
              }
            >
              刷新
            </Button>
            <Button
              type="primary"
              size="large"
              icon={<DownloadOutlined />}
              onClick={() => setCloneModalVisible(true)}
            >
              克隆仓库
            </Button>
          </Space>
        }
        style={{ marginBottom: 24 }}
      >
        <Table
          columns={columns}
          dataSource={repos}
          loading={isLoading}
          rowKey="name"
          pagination={{ pageSize: 10 }}
          scroll={{ x: 'max-content' }}
          locale={{
            emptyText: isError
              ? (
                <span>
                  加载失败：{String(error instanceof Error ? error.message : (error as any)?.response?.data?.detail || '未知错误')}，
                  <Button type="link" onClick={() => refetch()} style={{ padding: 0 }}>点击重试</Button>
                </span>
              )
              : '暂无已克隆项目，请先克隆 Git 仓库',
          }}
        />
      </Card>

      {selectedProject && (
        <div ref={statsCardRef}>
          <Card
            title={`${selectedProject} - 统计信息`}
            style={{ marginBottom: 24 }}
            loading={statsLoading}
          >
            {statsError ? (
              <div style={{ color: '#dc2626', padding: '16px 0' }}>
                获取统计失败：{String(statsErrorDetail instanceof Error ? statsErrorDetail.message : (statsErrorDetail as any)?.response?.data?.detail || '未知错误')}
                <Button type="link" onClick={() => refetchStats()} style={{ marginLeft: 8 }}>重试</Button>
              </div>
            ) : (
              <Row gutter={16}>
                <Col span={8}>
                  <Statistic title="类型" value={stats?.types ?? 0} />
                </Col>
                <Col span={8}>
                  <Statistic title="方法" value={stats?.methods ?? 0} />
                </Col>
                <Col span={8}>
                  <Statistic title="字段" value={stats?.fields ?? 0} />
                </Col>
              </Row>
            )}
          </Card>
        </div>
      )}

      <Modal
        title="克隆 Git 仓库"
        open={cloneModalVisible}
        onCancel={() => {
          setCloneModalVisible(false)
          form.resetFields()
        }}
        onOk={() => form.submit()}
        confirmLoading={cloneMutation.isPending}
      >
        <Form form={form} layout="vertical" onFinish={handleClone}>
          <Form.Item
            name="gitUrl"
            label="Git URL"
            rules={[{ required: true, message: '请输入 Git 仓库地址' }]}
          >
            <Input
              placeholder="如: https://github.com/org/repo.git 或 git@github.com:org/repo.git"
            />
          </Form.Item>
          <Form.Item name="branch" label="分支" initialValue="master">
            <Input placeholder="默认 master" />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  )
}
