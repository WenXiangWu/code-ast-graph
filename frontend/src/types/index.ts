export interface Project {
  name: string
  path: string
  status: string
}

export interface ProjectStats {
  types: number
  methods: number
  fields: number
}

export interface GraphNode {
  id: string
  name: string
}

export interface GraphEdge {
  from: string
  to: string
  depth: number
}

export interface GraphData {
  nodes: GraphNode[]
  edges: GraphEdge[]
  total_nodes: number
  total_edges: number
}
