import { useState } from 'react'
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
} from 'antd'
import {
  ReloadOutlined,
  BuildOutlined,
  DownloadOutlined,
  CheckCircleOutlined,
} from '@ant-design/icons'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  getRepos,
  cloneRepo,
  scanProject,
  getProjectStats,
} from '../api/projects'
import type { RepoItem } from '../api/projects'

export default function ProjectManagement() {
  const [selectedProject, setSelectedProject] = useState<string>('')
  const [cloneModalVisible, setCloneModalVisible] = useState(false)
  const [buildingRepo, setBuildingRepo] = useState<string | null>(null)
  const [form] = Form.useForm()
  const queryClient = useQueryClient()

  // 获取仓库列表（git-repos + Neo4j 构建信息）
  const { data: reposData, isLoading } = useQuery({
    queryKey: ['repos'],
    queryFn: getRepos,
  })

  // 获取项目统计
  const { data: stats } = useQuery({
    queryKey: ['projectStats', selectedProject],
    queryFn: () => getProjectStats(selectedProject),
    enabled: !!selectedProject,
  })

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

  // 构建图谱
  const scanMutation = useMutation({
    mutationFn: ({
      projectName,
      projectPath,
      force,
    }: {
      projectName: string
      projectPath: string
      force: boolean
    }) => scanProject(projectName, projectPath, force),
    onMutate: ({ projectName }) => {
      setBuildingRepo(projectName)
    },
    onSuccess: () => {
      message.success('知识图谱构建完成')
      queryClient.invalidateQueries({ queryKey: ['repos'] })
    },
    onError: (error: any) => {
      message.error(error.response?.data?.detail || '构建失败')
    },
    onSettled: () => {
      setBuildingRepo(null)
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

  const columns = [
    {
      title: '项目名称',
      dataIndex: 'name',
      key: 'name',
      render: (text: string, record: RepoItem) => (
        <Space>
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
      width: 120,
      ellipsis: true,
      render: (v: string) =>
        v ? (
          <Tooltip title={v}>
            <code style={{ fontSize: 12 }}>{v.slice(0, 8)}</code>
          </Tooltip>
        ) : (
          <span style={{ color: '#999' }}>—</span>
        ),
    },
    {
      title: '当前 Commit 时间',
      dataIndex: 'current_commit_time',
      key: 'current_commit_time',
      width: 140,
      render: (v: string) => v || <span style={{ color: '#999' }}>—</span>,
    },
    {
      title: '构建时 Commit',
      dataIndex: 'scanned_commit_id',
      key: 'scanned_commit_id',
      width: 120,
      ellipsis: true,
      render: (v: string) =>
        v ? (
          <Tooltip title={v}>
            <code style={{ fontSize: 12 }}>{v.slice(0, 8)}</code>
          </Tooltip>
        ) : (
          <span style={{ color: '#999' }}>未构建</span>
        ),
    },
    {
      title: '构建时间',
      dataIndex: 'scanned_at',
      key: 'scanned_at',
      width: 160,
      render: (v: string) => v || <span style={{ color: '#999' }}>—</span>,
    },
    {
      title: '操作',
      key: 'action',
      width: 180,
      render: (_: any, record: RepoItem) => (
        <Space>
          <Button
            size="small"
            onClick={() => setSelectedProject(record.name)}
          >
            统计
          </Button>
          <Tooltip
            title={
              record.can_build
                ? '当前代码与构建版本不一致，点击重新构建'
                : '当前代码已构建，无需重新构建'
            }
          >
            <span>
              <Button
                type="primary"
                size="small"
                icon={<BuildOutlined />}
                disabled={!record.can_build}
                loading={buildingRepo === record.name}
                onClick={() => handleBuild(record)}
              >
                构建
              </Button>
            </span>
          </Tooltip>
        </Space>
      ),
    },
  ]

  const repos = reposData?.repos || []

  return (
    <div className="app-container">
      <div className="page-header">
        <h1>🗺️ 知识图谱管理</h1>
        <p>克隆 Git 仓库到 git-repos，扫描并构建架构知识图谱</p>
      </div>

      <Card
        title="已克隆项目"
        extra={
          <Space>
            <Button
              icon={<ReloadOutlined />}
              onClick={() =>
                queryClient.invalidateQueries({ queryKey: ['repos'] })
              }
            >
              刷新
            </Button>
            <Button
              type="primary"
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
          locale={{
            emptyText: '暂无已克隆项目，请先克隆 Git 仓库',
          }}
        />
      </Card>

      {selectedProject && stats && (
        <Card
          title={`${selectedProject} - 统计信息`}
          style={{ marginBottom: 24 }}
        >
          <Row gutter={16}>
            <Col span={8}>
              <Statistic title="类型" value={stats.types} />
            </Col>
            <Col span={8}>
              <Statistic title="方法" value={stats.methods} />
            </Col>
            <Col span={8}>
              <Statistic title="字段" value={stats.fields} />
            </Col>
          </Row>
        </Card>
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
