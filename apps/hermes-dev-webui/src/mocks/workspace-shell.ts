export interface ShellSessionItem {
  readonly id: string
  readonly title: string
  readonly preview: string
  readonly time: string
  readonly model: string
}

export const defaultShellSession: ShellSessionItem = {
  id: 'workspace-shell',
  title: 'Workspace shell review',
  preview: 'Validate the three-column layout across all five themes.',
  time: 'Now',
  model: 'deepseek-chat',
}

export const shellSessions: readonly ShellSessionItem[] = [
  defaultShellSession,
  {
    id: 'memory-context',
    title: 'Memory context notes',
    preview: 'Static preview of future context inspection surfaces.',
    time: '18m',
    model: 'deepseek-chat',
  },
  {
    id: 'tool-event',
    title: 'Tool event anatomy',
    preview: 'Plan readable states without executing any tools.',
    time: '1h',
    model: 'Preview',
  },
  {
    id: 'theme-regression',
    title: 'Theme regression pass',
    preview: 'Obsidian, Paper, Song, Ink, and Sakura Night.',
    time: '2h',
    model: 'Preview',
  },
] as const

export const workspaceCapabilities = [
  'Conversation',
  'Memory Context',
  'Tool Events',
  'Workspace',
] as const
