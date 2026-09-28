import { useState, useEffect } from 'react';
import { getAgents } from '../api/client';
import { Bot } from 'lucide-react';

const TONE_COLORS = {
  analytical: '#3b82f6',
  friendly: '#10b981',
  witty: '#f59e0b',
  professional: '#6366f1',
};

export default function Agents() {
  const [agents, setAgents] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getAgents()
      .then((res) => setAgents(res.data))
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="loading">
        <div className="spinner" />
        <p>Loading agents...</p>
      </div>
    );
  }

  return (
    <div>
      <div className="page-header">
        <h1 className="page-title">Realm Agents</h1>
        <p className="page-subtitle">
          AI personas that engage with your posts — each with unique expertise and personality
        </p>
      </div>

      <div className="agents-grid">
        {agents.map((agent) => (
          <div key={agent.id} className="agent-card">
            <div className="agent-card-header">
              <div
                className="agent-avatar-lg"
                style={{
                  background: `linear-gradient(135deg, ${TONE_COLORS[agent.tone] || '#6c5ce7'}, #a855f7)`,
                }}
              >
                {agent.name[0]}
              </div>
              <div>
                <div className="agent-name">
                  {agent.name}
                  {agent.is_community && (
                    <span style={{ fontSize: 11, color: 'var(--text-muted)', marginLeft: 6 }}>
                      Community
                    </span>
                  )}
                </div>
                <div className="agent-role">{agent.role}</div>
              </div>
            </div>

            <p className="agent-desc">{agent.description}</p>

            <div className="agent-tags">
              {(agent.expertise_tags || []).map((tag) => (
                <span key={tag} className="agent-tag">
                  {tag}
                </span>
              ))}
            </div>
          </div>
        ))}
      </div>

      {agents.length === 0 && (
        <div className="empty-state">
          <Bot size={48} style={{ opacity: 0.3, marginBottom: 12 }} />
          <p className="empty-state-text">No agents available yet.</p>
        </div>
      )}
    </div>
  );
}
