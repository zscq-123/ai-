export type AgentTone = '亲切自然' | '简洁专业'
export type AgentCostMode = 'economy' | 'balanced' | 'quality'

export type AgentSkill = {
  id: string
  title: string
  text: string
  type: '官方技能' | '自定义技能'
  tools: number
  enabled: boolean
}

export type AgentConfiguration = {
  draft: boolean
  handoff: boolean
  translate: boolean
  tone: AgentTone
  cost_mode: AgentCostMode
  skills: AgentSkill[]
}

export type AgentDraft = {
  answer: string
  intent: string
  requires_human: boolean
  handoff_recommended: boolean
  language_assist_applied: boolean
  skill_id: string | null
  tone: AgentTone
  cost_mode: AgentCostMode
}

const aiServiceUrl = (import.meta.env.VITE_AI_SERVICE_URL || 'http://127.0.0.1:8000').replace(/\/$/, '')

async function payload<T>(response: Response, fallback: string): Promise<T> {
  const body = await response.json().catch(() => null) as { detail?: string } | T | null
  if (!response.ok) {
    throw new Error(body && typeof body === 'object' && 'detail' in body && body.detail ? body.detail : fallback)
  }
  return body as T
}

export async function getAgentConfiguration(): Promise<AgentConfiguration> {
  const response = await fetch(`${aiServiceUrl}/v1/agent/settings`)
  return payload<AgentConfiguration>(response, '无法读取后端 Agent 配置。')
}

export async function updateAgentConfiguration(
  values: Partial<Pick<AgentConfiguration, 'draft' | 'handoff' | 'translate' | 'tone' | 'cost_mode'>>,
): Promise<AgentConfiguration> {
  const response = await fetch(`${aiServiceUrl}/v1/agent/settings`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(values),
  })
  return payload<AgentConfiguration>(response, '后端 Agent 配置保存失败。')
}

export async function updateAgentSkill(
  skillId: string,
  values: Partial<Pick<AgentSkill, 'title' | 'text' | 'tools' | 'enabled'>>,
): Promise<AgentSkill> {
  const response = await fetch(`${aiServiceUrl}/v1/agent/skills/${encodeURIComponent(skillId)}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(values),
  })
  return payload<AgentSkill>(response, 'Agent 技能保存失败。')
}

export async function createAgentSkill(): Promise<AgentSkill> {
  const response = await fetch(`${aiServiceUrl}/v1/agent/skills`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({}),
  })
  return payload<AgentSkill>(response, 'Agent 技能创建失败。')
}

export async function generateAgentDraft(values: {
  channel: 'chat' | 'email' | 'review'
  customer_name: string
  subject: string
  message: string
}): Promise<AgentDraft> {
  const response = await fetch(`${aiServiceUrl}/v1/agent/draft`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(values),
  })
  return payload<AgentDraft>(response, '后端 Agent 暂时无法生成回复建议。')
}
