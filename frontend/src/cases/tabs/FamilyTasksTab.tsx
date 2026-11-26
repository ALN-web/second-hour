import { useState } from 'react'
import type { FamilyMemberItem, CaseTaskItem } from '../types'
import { api, fmtTime } from '../../api'

interface FamilyTasksTabProps {
  caseId: string
  familyMembers: FamilyMemberItem[]
  tasks: CaseTaskItem[]
  onRefresh: () => void
}

export function FamilyTasksTab({
  caseId,
  familyMembers,
  tasks,
  onRefresh,
}: FamilyTasksTabProps) {
  const [filter, setFilter] = useState<'all' | 'open' | 'done'>('all')

  // Add Task Modal state
  const [taskModalOpen, setTaskModalOpen] = useState(false)
  const [taskTitle, setTaskTitle] = useState('')
  const [taskDesc, setTaskDesc] = useState('')
  const [taskPriority, setTaskPriority] = useState<'low' | 'medium' | 'high'>('medium')
  const [taskDueAt, setTaskDueAt] = useState('')
  const [taskDueSource, setTaskDueSource] = useState('Family Follow-up')
  const [taskAssignee, setTaskAssignee] = useState('')
  const [creatingTask, setCreatingTask] = useState(false)

  // Add Member Modal state
  const [memberModalOpen, setMemberModalOpen] = useState(false)
  const [memberName, setMemberName] = useState('')
  const [memberRole, setMemberRole] = useState('member')
  const [memberRel, setMemberRel] = useState('Family')
  const [memberPhone, setMemberPhone] = useState('')
  const [memberPerms, setMemberPerms] = useState('View & Add Tasks')
  const [addingMember, setAddingMember] = useState(false)

  const handleToggleTask = async (taskId: string) => {
    try {
      await api(`/api/cases/${caseId}/tasks/${taskId}/toggle`, {
        method: 'POST',
      })
      onRefresh()
    } catch (e) {
      console.error('Failed to toggle task:', e)
    }
  }

  const handleCreateTask = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!taskTitle.trim()) return

    setCreatingTask(true)
    try {
      await api(`/api/cases/${caseId}/tasks/create`, {
        method: 'POST',
        body: {
          title: taskTitle.trim(),
          description: taskDesc.trim(),
          priority: taskPriority,
          due_at: taskDueAt ? new Date(taskDueAt).toISOString() : null,
          due_source: taskDueSource.trim(),
          assignee_id: taskAssignee || null,
        },
      })
      setTaskModalOpen(false)
      setTaskTitle('')
      setTaskDesc('')
      onRefresh()
    } catch (err) {
      console.error('Failed to create task:', err)
    } finally {
      setCreatingTask(false)
    }
  }

  const handleAddMember = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!memberName.trim()) return

    setAddingMember(true)
    try {
      await api(`/api/cases/${caseId}/members`, {
        method: 'POST',
        body: {
          name: memberName.trim(),
          role: memberRole,
          relationship: memberRel.trim(),
          contact_number: memberPhone.trim(),
          permissions_summary: memberPerms,
        },
      })
      setMemberModalOpen(false)
      setMemberName('')
      setMemberPhone('')
      onRefresh()
    } catch (err) {
      console.error('Failed to add member:', err)
    } finally {
      setAddingMember(false)
    }
  }

  const filteredTasks = tasks.filter((t) => {
    if (filter === 'open') return t.status === 'open'
    if (filter === 'done') return t.status === 'done'
    return true
  })

  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
      {/* LEFT 1 COL: Authorized Family Members */}
      <div className="card p-6 bg-white border border-slate-200 rounded-2xl shadow-sm space-y-4">
        <div className="flex items-center justify-between border-b border-slate-100 pb-3">
          <div>
            <h3 className="text-base font-bold text-navy-950 flex items-center gap-2">
              <span>👥</span>
              <span>Authorized Family Members</span>
            </h3>
            <p className="text-xs text-slate-500 mt-0.5">
              Authorized contacts with access to case documents and updates
            </p>
          </div>

          <button
            onClick={() => setMemberModalOpen(true)}
            className="text-xs font-semibold text-accent-500 hover:underline cursor-pointer"
          >
            + Add Member
          </button>
        </div>

        <div className="space-y-3">
          {familyMembers.map((m) => (
            <div
              key={m.user_id}
              className="p-3.5 bg-slate-50/80 rounded-xl border border-slate-200/80 space-y-1.5"
            >
              <div className="flex items-center justify-between">
                <span className="text-sm font-bold text-navy-950">{m.name}</span>
                <span className={`chip text-[11px] font-semibold px-2 py-0.5 rounded border ${
                  m.role === 'coordinator'
                    ? 'bg-navy-900 text-white border-navy-950'
                    : 'bg-slate-100 text-slate-700 border-slate-300'
                }`}>
                  {m.role.toUpperCase()}
                </span>
              </div>
              <div className="flex items-center gap-2 text-xs text-slate-500">
                <span>Relation: <strong className="text-slate-700">{m.relationship}</strong></span>
                <span>·</span>
                <span>{m.contact_number}</span>
              </div>
              <div className="text-[11px] text-slate-500 pt-1 border-t border-slate-200 flex items-center gap-1">
                <span>Permissions:</span>
                <span className="font-medium text-slate-700">{m.permissions_summary}</span>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* RIGHT 2 COLS: Case Task Checklist */}
      <div className="lg:col-span-2 card p-6 bg-white border border-slate-200 rounded-2xl shadow-sm space-y-5">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-slate-100 pb-3">
          <div>
            <h3 className="text-base font-bold text-navy-950 flex items-center gap-2">
              <span>☑️</span>
              <span>Case Action Checklist</span>
            </h3>
            <p className="text-xs text-slate-500 mt-0.5">
              Priority actions, scheme document requests, and surveyor appointments
            </p>
          </div>

          <div className="flex items-center gap-2">
            <div className="flex items-center gap-1 bg-slate-100 p-1 rounded-xl text-xs font-semibold">
              <button
                onClick={() => setFilter('all')}
                className={`px-3 py-1 rounded-lg transition ${
                  filter === 'all' ? 'bg-white text-navy-950 shadow-2xs' : 'text-slate-600'
                }`}
              >
                All ({tasks.length})
              </button>
              <button
                onClick={() => setFilter('open')}
                className={`px-3 py-1 rounded-lg transition ${
                  filter === 'open' ? 'bg-white text-navy-950 shadow-2xs' : 'text-slate-600'
                }`}
              >
                Open ({tasks.filter((t) => t.status === 'open').length})
              </button>
              <button
                onClick={() => setFilter('done')}
                className={`px-3 py-1 rounded-lg transition ${
                  filter === 'done' ? 'bg-white text-navy-950 shadow-2xs' : 'text-slate-600'
                }`}
              >
                Done
              </button>
            </div>

            <button
              onClick={() => setTaskModalOpen(true)}
              className="btn-accent text-xs px-3.5 py-1.5 rounded-xl font-semibold shadow-xs cursor-pointer"
            >
              + New Task
            </button>
          </div>
        </div>

        {/* Task List */}
        <div className="space-y-3">
          {filteredTasks.map((t) => {
            const isDone = t.status === 'done'
            return (
              <div
                key={t.task_id}
                onClick={() => handleToggleTask(t.task_id)}
                className={`p-4 rounded-xl border transition cursor-pointer flex items-start gap-3.5 ${
                  isDone
                    ? 'bg-slate-50/50 border-slate-200/60 opacity-60'
                    : 'bg-white border-slate-200 hover:border-navy-300 hover:shadow-xs'
                }`}
              >
                {/* Checkbox */}
                <input
                  type="checkbox"
                  checked={isDone}
                  onChange={() => {}} // handled by div click
                  className="mt-1 h-4 w-4 rounded text-accent-500 focus:ring-accent-500 border-slate-300 cursor-pointer"
                />

                <div className="flex-1 space-y-1">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <h4 className={`text-sm font-bold ${
                      isDone ? 'line-through text-slate-500' : 'text-navy-950'
                    }`}>
                      {t.title}
                    </h4>

                    <span className={`chip text-[10px] font-bold px-2 py-0.5 rounded ${
                      t.priority === 'high'
                        ? 'bg-red-50 text-red-700 border border-red-200'
                        : t.priority === 'medium'
                        ? 'bg-amber-50 text-amber-800 border border-amber-200'
                        : 'bg-slate-100 text-slate-700 border border-slate-200'
                    }`}>
                      {t.priority.toUpperCase()} PRIORITY
                    </span>
                  </div>

                  {t.description && (
                    <p className="text-xs text-slate-600 leading-relaxed">
                      {t.description}
                    </p>
                  )}

                  <div className="flex flex-wrap items-center gap-3 pt-1 text-[11px] text-slate-400">
                    {t.assignee_name && (
                      <span className="font-semibold text-slate-600 bg-slate-100 px-2 py-0.5 rounded text-[10px]">
                        👤 {t.assignee_name}
                      </span>
                    )}
                    {t.due_at && (
                      <span>
                        Due: <strong className="text-slate-700">{fmtTime(t.due_at)}</strong>
                      </span>
                    )}
                    {t.due_source && (
                      <span className="text-slate-500 font-medium italic">
                        ({t.due_source})
                      </span>
                    )}
                  </div>
                </div>
              </div>
            )
          })}

          {filteredTasks.length === 0 && (
            <div className="text-center py-10 text-xs text-slate-500">
              No tasks match this filter. Click "+ New Task" above to add one.
            </div>
          )}
        </div>
      </div>

      {/* Add Task Modal */}
      {taskModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-xs p-4">
          <div className="bg-white rounded-2xl max-w-md w-full p-6 shadow-2xl border border-slate-200 space-y-4">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3">
              <h3 className="text-base font-bold text-navy-950">Add Case Task</h3>
              <button
                onClick={() => setTaskModalOpen(false)}
                className="text-slate-400 hover:text-slate-600 text-sm"
              >
                ✕
              </button>
            </div>

            <form onSubmit={handleCreateTask} className="space-y-3.5">
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Task Title *
                </label>
                <input
                  type="text"
                  required
                  placeholder="e.g. Call surveyor to confirm visit time"
                  value={taskTitle}
                  onChange={(e) => setTaskTitle(e.target.value)}
                  className="w-full text-xs p-2.5 bg-slate-50 border border-slate-200 rounded-lg focus:outline-none focus:ring-1 focus:ring-accent-500"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Description / Action Notes
                </label>
                <textarea
                  rows={2}
                  value={taskDesc}
                  onChange={(e) => setTaskDesc(e.target.value)}
                  className="w-full text-xs p-2.5 bg-slate-50 border border-slate-200 rounded-lg focus:outline-none focus:ring-1 focus:ring-accent-500"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">
                    Priority
                  </label>
                  <select
                    value={taskPriority}
                    onChange={(e) => setTaskPriority(e.target.value as any)}
                    className="w-full text-xs p-2 bg-slate-50 border border-slate-200 rounded-lg"
                  >
                    <option value="high">High Priority</option>
                    <option value="medium">Medium Priority</option>
                    <option value="low">Low Priority</option>
                  </select>
                </div>
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">
                    Assignee
                  </label>
                  <select
                    value={taskAssignee}
                    onChange={(e) => setTaskAssignee(e.target.value)}
                    className="w-full text-xs p-2 bg-slate-50 border border-slate-200 rounded-lg"
                  >
                    <option value="">Unassigned</option>
                    {familyMembers.map((m) => (
                      <option key={m.user_id} value={m.user_id}>
                        {m.name} ({m.relationship})
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">
                    Due Date (Optional)
                  </label>
                  <input
                    type="datetime-local"
                    value={taskDueAt}
                    onChange={(e) => setTaskDueAt(e.target.value)}
                    className="w-full text-xs p-2 bg-slate-50 border border-slate-200 rounded-lg"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">
                    Due Source / Reason
                  </label>
                  <input
                    type="text"
                    value={taskDueSource}
                    onChange={(e) => setTaskDueSource(e.target.value)}
                    placeholder="e.g. Protocol"
                    className="w-full text-xs p-2 bg-slate-50 border border-slate-200 rounded-lg"
                  />
                </div>
              </div>

              <div className="flex justify-end gap-2 pt-2 border-t border-slate-100">
                <button
                  type="button"
                  onClick={() => setTaskModalOpen(false)}
                  className="btn-ghost text-xs px-4 py-2"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={creatingTask || !taskTitle.trim()}
                  className="btn-accent text-xs px-5 py-2 rounded-xl font-semibold shadow"
                >
                  {creatingTask ? 'Adding...' : 'Create Task'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Add Member Modal */}
      {memberModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-xs p-4">
          <div className="bg-white rounded-2xl max-w-md w-full p-6 shadow-2xl border border-slate-200 space-y-4">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3">
              <h3 className="text-base font-bold text-navy-950">Add Authorized Family Contact</h3>
              <button
                onClick={() => setMemberModalOpen(false)}
                className="text-slate-400 hover:text-slate-600 text-sm"
              >
                ✕
              </button>
            </div>

            <form onSubmit={handleAddMember} className="space-y-3.5">
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Full Name *
                </label>
                <input
                  type="text"
                  required
                  placeholder="e.g. Ramesh Sharma"
                  value={memberName}
                  onChange={(e) => setMemberName(e.target.value)}
                  className="w-full text-xs p-2.5 bg-slate-50 border border-slate-200 rounded-lg focus:outline-none focus:ring-1 focus:ring-accent-500"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">
                    Relationship
                  </label>
                  <input
                    type="text"
                    placeholder="e.g. Father / Attorney"
                    value={memberRel}
                    onChange={(e) => setMemberRel(e.target.value)}
                    className="w-full text-xs p-2 bg-slate-50 border border-slate-200 rounded-lg"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">
                    Contact Phone
                  </label>
                  <input
                    type="text"
                    placeholder="+91 98450 00000"
                    value={memberPhone}
                    onChange={(e) => setMemberPhone(e.target.value)}
                    className="w-full text-xs p-2 bg-slate-50 border border-slate-200 rounded-lg"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Access Role
                </label>
                <select
                  value={memberRole}
                  onChange={(e) => setMemberRole(e.target.value)}
                  className="w-full text-xs p-2 bg-slate-50 border border-slate-200 rounded-lg"
                >
                  <option value="coordinator">Coordinator (Full Case & Approval Access)</option>
                  <option value="member">Member (View & Add Tasks)</option>
                  <option value="viewer">Viewer (Read Only)</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Permissions Notes
                </label>
                <input
                  type="text"
                  placeholder="e.g. View & Add Tasks, Hospital Follow-up"
                  value={memberPerms}
                  onChange={(e) => setMemberPerms(e.target.value)}
                  className="w-full text-xs p-2.5 bg-slate-50 border border-slate-200 rounded-lg"
                />
              </div>

              <div className="flex justify-end gap-2 pt-2 border-t border-slate-100">
                <button
                  type="button"
                  onClick={() => setMemberModalOpen(false)}
                  className="btn-ghost text-xs px-4 py-2"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={addingMember || !memberName.trim()}
                  className="btn-accent text-xs px-5 py-2 rounded-xl font-semibold shadow"
                >
                  {addingMember ? 'Adding...' : 'Add Family Member'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}
