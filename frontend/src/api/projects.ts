import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  timeout: 30000,
})

export interface Project {
  name: string
  path: string
  status: string
}

export interface RepoItem {
  name: string
  path: string
  git_url: string
  branch: string
  current_commit_id: string
  current_commit_time: string
  scanned_commit_id: string
  scanned_at: string
  can_build: boolean
}

export async function getRepos(): Promise<{ repos: RepoItem[] }> {
  const response = await api.get('/repos')
  return response.data
}

export async function cloneRepo(gitUrl: string, branch: string = 'master'): Promise<{ success: boolean; message?: string; repo_name?: string; path?: string }> {
  const response = await api.post('/repos/clone', {
    git_url: gitUrl,
    branch: branch || 'master',
  })
  return response.data
}

export interface ProjectStats {
  types: number
  methods: number
  fields: number
}

export async function getProjects(): Promise<{ projects: Project[] }> {
  const response = await api.get('/projects')
  return response.data
}

export async function scanProject(
  projectName: string,
  projectPath: string,
  force: boolean = false
): Promise<any> {
  const response = await api.post(`/projects/${projectName}/scan`, {
    project_path: projectPath,
    force,
  })
  return response.data
}

export async function getProjectStats(projectName: string): Promise<ProjectStats> {
  const response = await api.get(`/projects/${projectName}/stats`)
  return response.data
}
