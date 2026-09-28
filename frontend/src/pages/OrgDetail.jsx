import { useState, useEffect, useCallback } from 'react';
import { Link, useParams, useNavigate } from 'react-router-dom';
import {
  Users, Lock, Globe, MessageSquare, Plus, Pin, Trash2, UserPlus, ArrowLeft,
} from 'lucide-react';
import {
  getOrg, getDiscussions, createDiscussion, joinOrg, leaveOrg, deleteOrg,
  getOrgMembers, addOrgMember, removeOrgMember, updateOrgMember,
} from '../api/client';
import { useAuth } from '../context/AuthContext';
import timeAgo from '../utils/timeAgo';

const QUICK_TAGS = ['technology', 'AI', 'news', 'sports', 'art', 'health', 'music', 'politics'];

function DiscussionRow({ discussion, slug }) {
  return (
    <Link to={`/orgs/${slug}/d/${discussion.id}`} className="discussion-row">
      <div className="discussion-main">
        <div className="discussion-title">
          {discussion.is_pinned && <Pin size={13} className="pin-icon" />}
          {discussion.is_locked && <Lock size={13} className="pin-icon" />}
          {discussion.title}
        </div>
        {discussion.body && <p className="discussion-preview">{discussion.body}</p>}
        <div className="discussion-meta">
          <span>{discussion.display_name || discussion.username}</span>
          <span>·</span>
          <span>{timeAgo(discussion.created_at)}</span>
          {discussion.tags?.length > 0 && (
            <>
              <span>·</span>
              <span>{discussion.tags.map((t) => `#${t}`).join(' ')}</span>
            </>
          )}
        </div>
      </div>
      <div className="discussion-count">
        <MessageSquare size={14} />
        {discussion.reply_count}
      </div>
    </Link>
  );
}

export default function OrgDetail() {
  const { slug } = useParams();
  const { user } = useAuth();
  const navigate = useNavigate();

  const [org, setOrg] = useState(null);
  const [discussions, setDiscussions] = useState([]);
  const [members, setMembers] = useState([]);
  const [tab, setTab] = useState('discussions');
  const [loading, setLoading] = useState(true);
  const [notFound, setNotFound] = useState(false);
  const [error, setError] = useState('');

  const [showCompose, setShowCompose] = useState(false);
  const [title, setTitle] = useState('');
  const [body, setBody] = useState('');
  const [tags, setTags] = useState([]);
  const [posting, setPosting] = useState(false);

  const [inviteName, setInviteName] = useState('');

  const isMember = Boolean(org?.my_role);
  const isAdmin = org?.my_role === 'admin' || org?.my_role === 'owner';
  const isOwner = org?.my_role === 'owner';

  const load = useCallback(async () => {
    try {
      setLoading(true);
      const orgRes = await getOrg(slug);
      setOrg(orgRes.data);

      const [discussionRes, memberRes] = await Promise.all([
        getDiscussions(slug),
        getOrgMembers(slug),
      ]);
      setDiscussions(discussionRes.data);
      setMembers(memberRes.data);
    } catch (err) {
      if (err.response?.status === 404) setNotFound(true);
      else console.error('Failed to load organization:', err);
    } finally {
      setLoading(false);
    }
  }, [slug]);

  useEffect(() => {
    load();
  }, [load]);

  const handleJoin = async () => {
    try {
      await joinOrg(slug);
      load();
    } catch (err) {
      setError(err.response?.data?.detail || 'Could not join');
    }
  };

  const handleLeave = async () => {
    try {
      await leaveOrg(slug);
      load();
    } catch (err) {
      setError(err.response?.data?.detail || 'Could not leave');
    }
  };

  const handleDeleteOrg = async () => {
    if (!window.confirm(`Delete "${org.name}"? This removes all its discussions.`)) return;
    try {
      await deleteOrg(slug);
      navigate('/orgs');
    } catch (err) {
      setError(err.response?.data?.detail || 'Could not delete');
    }
  };

  const handleCreateDiscussion = async (e) => {
    e.preventDefault();
    if (!title.trim() || posting) return;
    setPosting(true);
    setError('');
    try {
      await createDiscussion(slug, { title: title.trim(), body: body.trim(), tags });
      setTitle('');
      setBody('');
      setTags([]);
      setShowCompose(false);
      // Reload now, then again once background agents have replied.
      load();
      setTimeout(load, 4000);
    } catch (err) {
      setError(err.response?.data?.detail || 'Could not start discussion');
    } finally {
      setPosting(false);
    }
  };

  const handleInvite = async (e) => {
    e.preventDefault();
    if (!inviteName.trim()) return;
    setError('');
    try {
      await addOrgMember(slug, { username: inviteName.trim(), role: 'member' });
      setInviteName('');
      load();
    } catch (err) {
      setError(err.response?.data?.detail || 'Could not add member');
    }
  };

  const handleRemoveMember = async (username) => {
    if (!window.confirm(`Remove @${username} from ${org.name}?`)) return;
    try {
      await removeOrgMember(slug, username);
      load();
    } catch (err) {
      setError(err.response?.data?.detail || 'Could not remove member');
    }
  };

  const handleRoleChange = async (username, role) => {
    try {
      await updateOrgMember(slug, username, { role });
      load();
    } catch (err) {
      setError(err.response?.data?.detail || 'Could not update role');
    }
  };

  const toggleTag = (tag) =>
    setTags((prev) => (prev.includes(tag) ? prev.filter((t) => t !== tag) : [...prev, tag]));

  if (loading) {
    return (
      <div className="loading">
        <div className="spinner" />
        <p>Loading organization...</p>
      </div>
    );
  }

  if (notFound || !org) {
    return (
      <div className="empty-state">
        <Lock size={48} style={{ opacity: 0.3, marginBottom: 12 }} />
        <p className="empty-state-text">
          This organization doesn&apos;t exist, or it&apos;s private and you&apos;re not a member.
        </p>
        <Link to="/orgs" className="auth-link">Back to organizations</Link>
      </div>
    );
  }

  return (
    <div>
      <Link to="/orgs" className="back-link">
        <ArrowLeft size={15} /> Organizations
      </Link>

      <div className="org-header">
        <div className="org-avatar lg">{org.name[0]?.toUpperCase()}</div>
        <div className="org-header-body">
          <div className="org-header-top">
            <h1 className="profile-name">{org.name}</h1>
            <span className={`org-visibility ${org.visibility}`}>
              {org.visibility === 'private' ? <Lock size={11} /> : <Globe size={11} />}
              {org.visibility}
            </span>
          </div>
          <div className="profile-handle">@{org.slug}</div>
          {org.description && <p className="profile-bio">{org.description}</p>}

          <div className="profile-stats">
            <div className="stat">
              <div className="stat-value">{org.member_count}</div>
              <div className="stat-label">Members</div>
            </div>
            <div className="stat">
              <div className="stat-value">{org.discussion_count ?? discussions.length}</div>
              <div className="stat-label">Discussions</div>
            </div>
          </div>
        </div>

        {user && (
          <div className="org-header-actions">
            {!isMember && org.visibility === 'public' && (
              <button className="post-btn" onClick={handleJoin}>Join</button>
            )}
            {isMember && !isOwner && (
              <button className="ghost-btn" onClick={handleLeave}>Leave</button>
            )}
            {isOwner && (
              <button className="danger-btn" onClick={handleDeleteOrg}>
                <Trash2 size={14} /> Delete
              </button>
            )}
          </div>
        )}
      </div>

      {error && <div className="error-msg">{error}</div>}

      <div className="tab-bar">
        <button
          className={`tab ${tab === 'discussions' ? 'active' : ''}`}
          onClick={() => setTab('discussions')}
        >
          Discussions
        </button>
        <button
          className={`tab ${tab === 'members' ? 'active' : ''}`}
          onClick={() => setTab('members')}
        >
          Members
        </button>
      </div>

      {tab === 'discussions' && (
        <>
          {isMember && !showCompose && (
            <button className="new-discussion-btn" onClick={() => setShowCompose(true)}>
              <Plus size={16} /> Start a discussion
            </button>
          )}

          {isMember && showCompose && (
            <form className="post-composer" onSubmit={handleCreateDiscussion}>
              <input
                className="form-input"
                placeholder="Discussion title"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                maxLength={200}
              />
              <textarea
                className="composer-input"
                placeholder="Add some context..."
                value={body}
                onChange={(e) => setBody(e.target.value)}
                rows={3}
              />
              <div className="composer-footer">
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
                <div className="composer-actions">
                  <button type="button" className="ghost-btn" onClick={() => setShowCompose(false)}>
                    Cancel
                  </button>
                  <button className="post-btn" type="submit" disabled={!title.trim() || posting}>
                    {posting ? 'Posting...' : 'Start'}
                  </button>
                </div>
              </div>
            </form>
          )}

          {!isMember && (
            <div className="notice">
              {org.visibility === 'public'
                ? 'Join this organization to start discussions and reply.'
                : 'You are viewing as a guest.'}
            </div>
          )}

          {discussions.length === 0 ? (
            <div className="empty-state">
              <MessageSquare size={48} style={{ opacity: 0.3, marginBottom: 12 }} />
              <p className="empty-state-text">No discussions yet.</p>
            </div>
          ) : (
            <div className="discussion-list">
              {discussions.map((d) => (
                <DiscussionRow key={d.id} discussion={d} slug={slug} />
              ))}
            </div>
          )}
        </>
      )}

      {tab === 'members' && (
        <>
          {isAdmin && (
            <form className="invite-row" onSubmit={handleInvite}>
              <input
                className="form-input"
                placeholder="Add a member by username"
                value={inviteName}
                onChange={(e) => setInviteName(e.target.value)}
              />
              <button className="post-btn" type="submit" disabled={!inviteName.trim()}>
                <UserPlus size={15} /> Add
              </button>
            </form>
          )}

          <div className="member-list">
            {members.map((m) => (
              <div key={m.username} className="member-row">
                <div className="post-avatar sm">
                  {(m.display_name || m.username)[0]?.toUpperCase()}
                </div>
                <div className="member-info">
                  <Link to={`/u/${m.username}`} className="member-name">
                    {m.display_name || m.username}
                  </Link>
                  <div className="post-author-handle">@{m.username}</div>
                </div>

                <span className={`role-badge ${m.role}`}>{m.role}</span>

                {isOwner && m.role !== 'owner' && (
                  <select
                    className="role-select"
                    value={m.role}
                    onChange={(e) => handleRoleChange(m.username, e.target.value)}
                  >
                    <option value="member">member</option>
                    <option value="admin">admin</option>
                  </select>
                )}

                {isAdmin && m.role !== 'owner' && (
                  <button
                    className="icon-btn"
                    title={`Remove @${m.username}`}
                    onClick={() => handleRemoveMember(m.username)}
                  >
                    <Trash2 size={14} />
                  </button>
                )}
              </div>
            ))}
          </div>

          {members.length === 0 && (
            <div className="empty-state">
              <Users size={48} style={{ opacity: 0.3, marginBottom: 12 }} />
              <p className="empty-state-text">No members yet.</p>
            </div>
          )}
        </>
      )}
    </div>
  );
}
