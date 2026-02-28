import { useState, useEffect } from 'react'
import './App.css'

function App() {
  const [records, setRecords] = useState([])
  const [isFormOpen, setIsFormOpen] = useState(false)
  const [filterPerson, setFilterPerson] = useState('')
  const [filterDate, setFilterDate] = useState('')
  const [sortBy, setSortBy] = useState('date-desc')

  const [formData, setFormData] = useState({
    date: new Date().toISOString().split('T')[0],
    person: '',
    content: '',
    status: 'in-progress'
  })

  // Load records from localStorage on mount
  useEffect(() => {
    const savedRecords = localStorage.getItem('workRecords')
    if (savedRecords) {
      setRecords(JSON.parse(savedRecords))
    } else {
      // Demo data
      const demoRecords = [
        {
          id: Date.now() + 1,
          date: '2026-02-28',
          person: '张三',
          content: '完成Q1季度报告初稿，包含市场分析和财务预测',
          status: 'completed',
          createdAt: Date.now()
        },
        {
          id: Date.now() + 2,
          date: '2026-02-27',
          person: '李四',
          content: '与客户进行产品演示会议，收集反馈意见',
          status: 'in-progress',
          createdAt: Date.now() - 86400000
        },
        {
          id: Date.now() + 3,
          date: '2026-02-26',
          person: '王五',
          content: '优化系统性能，解决数据库查询慢的问题',
          status: 'completed',
          createdAt: Date.now() - 172800000
        }
      ]
      setRecords(demoRecords)
      localStorage.setItem('workRecords', JSON.stringify(demoRecords))
    }
  }, [])

  // Save to localStorage whenever records change
  useEffect(() => {
    if (records.length > 0) {
      localStorage.setItem('workRecords', JSON.stringify(records))
    }
  }, [records])

  const handleSubmit = (e) => {
    e.preventDefault()
    const newRecord = {
      id: Date.now(),
      ...formData,
      createdAt: Date.now()
    }
    setRecords([newRecord, ...records])
    setFormData({
      date: new Date().toISOString().split('T')[0],
      person: '',
      content: '',
      status: 'in-progress'
    })
    setIsFormOpen(false)
  }

  const handleDelete = (id) => {
    setRecords(records.filter(r => r.id !== id))
  }

  const handleStatusChange = (id, newStatus) => {
    setRecords(records.map(r =>
      r.id === id ? { ...r, status: newStatus } : r
    ))
  }

  // Get unique persons for filter dropdown
  const uniquePersons = [...new Set(records.map(r => r.person))].filter(Boolean)

  // Filter and sort records
  const filteredRecords = records
    .filter(r => !filterPerson || r.person === filterPerson)
    .filter(r => !filterDate || r.date === filterDate)
    .sort((a, b) => {
      switch (sortBy) {
        case 'date-desc':
          return new Date(b.date) - new Date(a.date)
        case 'date-asc':
          return new Date(a.date) - new Date(b.date)
        case 'person':
          return a.person.localeCompare(b.person)
        default:
          return 0
      }
    })

  const statusConfig = {
    'not-started': { label: '未开始', color: 'slate', icon: '○' },
    'in-progress': { label: '进行中', color: 'blue', icon: '◐' },
    'completed': { label: '已完成', color: 'emerald', icon: '●' },
    'blocked': { label: '受阻', color: 'rose', icon: '✕' }
  }

  return (
    <div className="app">
      {/* Header */}
      <header className="header">
        <div className="header-content">
          <div className="header-top">
            <div className="logo-area">
              <div className="logo-accent"></div>
              <h1 className="logo-title">Work Log</h1>
              <span className="logo-subtitle">部门工作记录系统</span>
            </div>
            <button
              className="btn-primary"
              onClick={() => setIsFormOpen(true)}
            >
              <span className="btn-icon">+</span>
              <span>新建记录</span>
            </button>
          </div>

          {/* Filters */}
          <div className="filters">
            <div className="filter-group">
              <label className="filter-label">筛选人员</label>
              <select
                className="filter-select"
                value={filterPerson}
                onChange={(e) => setFilterPerson(e.target.value)}
              >
                <option value="">全部人员</option>
                {uniquePersons.map(person => (
                  <option key={person} value={person}>{person}</option>
                ))}
              </select>
            </div>

            <div className="filter-group">
              <label className="filter-label">筛选日期</label>
              <input
                type="date"
                className="filter-input"
                value={filterDate}
                onChange={(e) => setFilterDate(e.target.value)}
              />
            </div>

            <div className="filter-group">
              <label className="filter-label">排序方式</label>
              <select
                className="filter-select"
                value={sortBy}
                onChange={(e) => setSortBy(e.target.value)}
              >
                <option value="date-desc">日期降序</option>
                <option value="date-asc">日期升序</option>
                <option value="person">按人员</option>
              </select>
            </div>

            {(filterPerson || filterDate) && (
              <button
                className="btn-clear"
                onClick={() => {
                  setFilterPerson('')
                  setFilterDate('')
                }}
              >
                清除筛选
              </button>
            )}
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="main">
        <div className="main-content">
          {/* Stats Bar */}
          <div className="stats-bar">
            <div className="stat-card">
              <div className="stat-number">{records.length}</div>
              <div className="stat-label">总记录数</div>
            </div>
            <div className="stat-card">
              <div className="stat-number">
                {records.filter(r => r.status === 'completed').length}
              </div>
              <div className="stat-label">已完成</div>
            </div>
            <div className="stat-card">
              <div className="stat-number">
                {records.filter(r => r.status === 'in-progress').length}
              </div>
              <div className="stat-label">进行中</div>
            </div>
            <div className="stat-card">
              <div className="stat-number">{uniquePersons.length}</div>
              <div className="stat-label">参与人员</div>
            </div>
          </div>

          {/* Records Grid */}
          {filteredRecords.length === 0 ? (
            <div className="empty-state">
              <div className="empty-icon">📋</div>
              <h3 className="empty-title">暂无工作记录</h3>
              <p className="empty-text">
                {records.length === 0
                  ? '点击上方"新建记录"按钮添加第一条工作记录'
                  : '没有符合筛选条件的记录'}
              </p>
            </div>
          ) : (
            <div className="records-grid">
              {filteredRecords.map((record, index) => (
                <div
                  key={record.id}
                  className="record-card"
                  style={{ animationDelay: `${index * 50}ms` }}
                >
                  <div className="record-header">
                    <div className="record-date-section">
                      <span className="record-date-day">
                        {new Date(record.date).getDate()}
                      </span>
                      <div className="record-date-meta">
                        <span className="record-date-month">
                          {new Date(record.date).toLocaleDateString('zh-CN', {
                            month: 'short'
                          })}
                        </span>
                        <span className="record-date-year">
                          {new Date(record.date).getFullYear()}
                        </span>
                      </div>
                    </div>

                    <div className="record-person">
                      <div className="person-avatar">
                        {record.person.charAt(0)}
                      </div>
                      <span className="person-name">{record.person}</span>
                    </div>
                  </div>

                  <div className="record-body">
                    <p className="record-content">{record.content}</p>
                  </div>

                  <div className="record-footer">
                    <select
                      className={`status-badge status-${record.status}`}
                      value={record.status}
                      onChange={(e) => handleStatusChange(record.id, e.target.value)}
                    >
                      {Object.entries(statusConfig).map(([key, config]) => (
                        <option key={key} value={key}>
                          {config.icon} {config.label}
                        </option>
                      ))}
                    </select>

                    <button
                      className="btn-delete"
                      onClick={() => handleDelete(record.id)}
                      title="删除记录"
                    >
                      <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
                        <path d="M2 4h12M5.333 4V2.667a1.333 1.333 0 011.334-1.334h2.666a1.333 1.333 0 011.334 1.334V4m2 0v9.333a1.333 1.333 0 01-1.334 1.334H4.667a1.333 1.333 0 01-1.334-1.334V4h9.334z" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
                      </svg>
                    </button>
                  </div>

                  <div className="record-decoration"></div>
                </div>
              ))}
            </div>
          )}
        </div>
      </main>

      {/* Add Record Modal */}
      {isFormOpen && (
        <div className="modal-overlay" onClick={() => setIsFormOpen(false)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h2 className="modal-title">新建工作记录</h2>
              <button
                className="modal-close"
                onClick={() => setIsFormOpen(false)}
              >
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
                  <path d="M18 6L6 18M6 6l12 12" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/>
                </svg>
              </button>
            </div>

            <form onSubmit={handleSubmit} className="modal-form">
              <div className="form-row">
                <div className="form-group">
                  <label className="form-label">日期</label>
                  <input
                    type="date"
                    className="form-input"
                    value={formData.date}
                    onChange={(e) => setFormData({...formData, date: e.target.value})}
                    required
                  />
                </div>

                <div className="form-group">
                  <label className="form-label">负责人</label>
                  <input
                    type="text"
                    className="form-input"
                    placeholder="输入姓名"
                    value={formData.person}
                    onChange={(e) => setFormData({...formData, person: e.target.value})}
                    required
                  />
                </div>
              </div>

              <div className="form-group">
                <label className="form-label">工作内容</label>
                <textarea
                  className="form-textarea"
                  placeholder="详细描述工作内容..."
                  rows="4"
                  value={formData.content}
                  onChange={(e) => setFormData({...formData, content: e.target.value})}
                  required
                />
              </div>

              <div className="form-group">
                <label className="form-label">进度状态</label>
                <div className="status-options">
                  {Object.entries(statusConfig).map(([key, config]) => (
                    <label key={key} className="status-option">
                      <input
                        type="radio"
                        name="status"
                        value={key}
                        checked={formData.status === key}
                        onChange={(e) => setFormData({...formData, status: e.target.value})}
                      />
                      <span className={`status-option-badge status-${key}`}>
                        <span className="status-icon">{config.icon}</span>
                        <span>{config.label}</span>
                      </span>
                    </label>
                  ))}
                </div>
              </div>

              <div className="form-actions">
                <button
                  type="button"
                  className="btn-secondary"
                  onClick={() => setIsFormOpen(false)}
                >
                  取消
                </button>
                <button type="submit" className="btn-primary">
                  <span>保存记录</span>
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Footer */}
      <footer className="footer">
        <p className="footer-text">
          Work Log System · Made with editorial design principles
        </p>
      </footer>
    </div>
  )
}

export default App
