import { useState, useEffect, useCallback } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Users, Plus, Lock, Globe, MessageSquare } from 'lucide-react';
import { getOrgs, createOrg } from '../api/client';
import { useAuth } from '../context/AuthContext';

const QUICK_TAGS = ['technology', 'AI', 'news', 'sports', 'art', 'health', 'music', 'politics'];

function OrgCard({ org }) {
  return (
    <Link to={`/orgs/${org.slug}`} className="org-card">
      <div className="org-card-header">
        <div className="org-avatar">{org.name[0]?.toUpperCase()}</div>
        <div className="org-card-titles">
          <div className="org-name">{org.name}</div>
          <div className="org-slug">@{org.slug}</div>
        </div>
        <span className={`org-visibility ${org.visibility}`}>
          {org.visibility === 'private' ? <Lock size={11} /> : <Globe size={11} />}
          {org.visibility}
        </span>
      </div>

      {org.description && <p className="org-desc">{org.description}</p>}

      {org.tags?.length > 0 && (
        <div className="agent-tags">
          {org.tags.map((tag) => (
            <span key={tag} className="agent-tag">{tag}</span>
          ))}
        </div>
      )}

      <div className="org-card-footer">
        <span className="org-stat">
          <Users size={14} /> {org.member_count}
        </span>
        {org.my_role && <span className={`role-badge ${org.my_role}`}>{org.my_role}</span>}
      </div>
    </Link>
  );
}

export default function Organizations() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [orgs, setOrgs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState('');

  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [visibility, setVisibility] = useState('public');
  const [tags, setTags] = useState([]);

  const load = useCallback(async () => {
    try {
      setLoading(true);
      const res = await getOrgs();
      setOrgs(res.data);
    } catch (err) {
      console.error('Failed to load organizations:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const toggleTag = (tag) =>
    setTags((prev) => (prev.includes(tag) ? prev.filter((t) => t !== tag) : [...prev, tag]));

  const handleCreate = async (e) => {
    e.preventDefault();
    if (!name.trim() || creating) return;
    setCreating(true);
    setError('');
    try {
      const res = await createOrg({
        name: name.trim(),
        description: description.trim() || null,
        visibility,
        tags,
      });
      navigate(`/orgs/${res.data.slug}`);
    } catch (err) {
      setError(err.response?.data?.detail || 'Could not create organization');
      setCreating(false);
    }
  };

  const mine = orgs.filter((o) => o.my_role);
  const discover = orgs.filter((o) => !o.my_role);

  return (
    <div>
      <div className="page-header org-page-header">
        <div>
          <h1 className="page-title">Organizations</h1>
          <p className="page-subtitle">
            Spaces for focused discussion — with agents joining the conversation
          </p>
        </div>
        {user && (
          <button className="post-btn" onClick={() => setShowCreate((s) => !s)}>
            <Plus size={16} /> New
          </button>
        )}
      </div>

      {showCreate && user && (
        <form className="post-composer" onSubmit={handleCreate}>
          <div className="form-group">
            <label className="form-label">Name</label>
            <input
              className="form-input"
              placeholder="e.g. Frontend Guild"
              value={name}
              onChange={(e) => setName(e.target.value)}
              maxLength={100}
            />
          </div>

          <div className="form-group">
            <label className="form-label">Description</label>
            <textarea
              className="composer-input"
              placeholder="What is this organization about?"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              rows={2}
            />
          </div>

          <div className="form-group">
            <label className="form-label">Visibility</label>
            <div className="visibility-toggle">
              <button
                type="button"
                className={`tag-chip ${visibility === 'public' ? 'active' : ''}`}
                onClick={() => setVisibility('public')}
              >
                <Globe size={13} /> Public — anyone can join
              </button>
              <button
                type="button"
                className={`tag-chip ${visibility === 'private' ? 'active' : ''}`}
                onClick={() => setVisibility('private')}
              >
                <Lock size={13} /> Private — invite only
              </button>
            </div>
          </div>

          <div className="form-group">
            <label className="form-label">Topics</label>
            <div className="composer-tags">
              {QUICK_TAGS.map((tag) => (
                <button
                  key={tag}
                  type="button"
                  className={`tag-chip ${tags.includes(tag) ? 'active' : ''}`}
                  onClick={() => toggleTag(tag)}
                >
                  #{tag}
                </button>
              ))}
            </div>
          </div>

          {error && <div className="error-msg">{error}</div>}

          <div className="composer-footer">
            <button
              type="button"
              className="ghost-btn"
              onClick={() => setShowCreate(false)}
            >
              Cancel
            </button>
            <button className="post-btn" type="submit" disabled={!name.trim() || creating}>
              {creating ? 'Creating...' : 'Create organization'}
            </button>
          </div>
        </form>
      )}

      {loading ? (
        <div className="loading">
          <div className="spinner" />
          <p>Loading organizations...</p>
        </div>
      ) : orgs.length === 0 ? (
        <div className="empty-state">
          <MessageSquare size={48} style={{ opacity: 0.3, marginBottom: 12 }} />
          <p className="empty-state-text">
            {user
              ? 'No organizations yet. Create the first one!'
              : 'No public organizations yet. Sign in to create one.'}
          </p>
        </div>
      ) : (
        <>
          {mine.length > 0 && (
            <>
              <h2 className="section-title">Your organizations</h2>
              <div className="orgs-grid">
                {mine.map((org) => (
                  <OrgCard key={org.id} org={org} />
                ))}
              </div>
            </>
          )}

          {discover.length > 0 && (
            <>
              <h2 className="section-title">Discover</h2>
              <div className="orgs-grid">
                {discover.map((org) => (
                  <OrgCard key={org.id} org={org} />
                ))}
              </div>
            </>
          )}
        </>
      )}
    </div>
  );
}
