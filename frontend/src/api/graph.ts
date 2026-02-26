import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  timeout: 30000,
})

export interface GraphData {
  nodes: Array<{ id: string; name: string }>
  edges: Array<{ from: string; to: string; depth: number }>
  total_nodes: number
  total_edges: number
  filtered_count?: number
  filter_mode?: string
}

export async function getProjectGraph(
  projectName: string,
  startClass?: string,
  maxDepth: number = 3,
  filterMode: string = 'moderate'
): Promise<GraphData> {
  const response = await api.get(`/projects/${encodeURIComponent(projectName)}/graph`, {
    params: { 
      start_class: startClass || undefined, 
      max_depth: maxDepth,
      filter_mode: filterMode
    },
    timeout: 120000,
  })
  return response.data
}
