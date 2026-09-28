import { useState, useEffect, useCallback } from 'react';
import { Link, useParams, useNavigate } from 'react-router-dom';
import { ArrowLeft, Pin, Lock, Trash2, CornerDownRight } from 'lucide-react';
import {
  getDiscussion, addDiscussionReply, deleteDiscussion,
  deleteDiscussionReply, updateDiscussion,
} from '../api/client';
import { useAuth } from '../context/AuthContext';
import timeAgo from '../utils/timeAgo';

const MAX_INDENT = 4;

/** Turn the flat, chronologically-ordered reply list into a tree. */
function buildTree(replies) {
  const byId = new Map();
  replies.forEach((r) => byId.set(r.id, { ...r, children: [] }));

  const roots = [];
  replies.forEach((r) => {
    const node = byId.get(r.id);
    const parent = r.parent_reply_id ? byId.get(r.parent_reply_id) : null;
    if (parent) parent.children.push(node);
    else roots.push(node);
  });
  return roots;
}

function Reply({ reply, depth, canReply, onReply, onDelete, currentUser, isAdmin }) {
  const isAuthor = !reply.is_agent && reply.username === currentUser?.username;

  return (
    <div
      className="thread-reply"
      style={{ marginLeft: Math.min(depth, MAX_INDENT) * 24 }}
    >
      <div className="comment">
        <div className={`comment-avatar ${reply.is_agent ? 'agent' : 'human'}`}>
          {reply.is_agent
            ? (reply.agent_name?.[0] || 'A')
            : (reply.display_name?.[0] || reply.username?.[0] || 'U')}
        </div>
        <div className="comment-body">
          <div className="comment-meta">
            <span className="comment-author">
              {reply.is_agent ? reply.agent_name : (reply.display_name || reply.username)}
            </span>
            {reply.is_agent && (
              <span className="agent-badge">{reply.agent_role || 'Agent'}</span>
            )}
            <span className="comment-time">{timeAgo(reply.created_at)}</span>

            {canReply && (
              <button className="link-btn" onClick={() => onReply(reply.id)}>
                <CornerDownRight size={12} /> Reply
              </button>
            )}
            {(isAuthor || isAdmin) && (
              <button className="link-btn danger" onClick={() => onDelete(reply.id)}>
                <Trash2 size={12} />
              </button>
            )}
          </div>
          <div className="comment-text">{reply.content}</div>
        </div>
      </div>

      {reply.children.map((child) => (
        <Reply
          key={child.id}
          reply={child}
          depth={depth + 1}
          canReply={canReply}
          onReply={onReply}
          onDelete={onDelete}
          currentUser={currentUser}
          isAdmin={isAdmin}
        />
      ))}
    </div>
  );
}

export default function DiscussionThread() {
  const { slug, discussionId } = useParams();
  const { user } = useAuth();
  const navigate = useNavigate();

  const [discussion, setDiscussion] = useState(null);
  const [loading, setLoading] = useState(true);
  const [notFound, setNotFound] = useState(false);
  const [error, setError] = useState('');

  const [replyText, setReplyText] = useState('');
  const [replyingTo, setReplyingTo] = useState(null);
  const [sending, setSending] = useState(false);

  const isMember = Boolean(discussion?.my_role);
  const isAdmin = discussion?.my_role === 'admin' || discussion?.my_role === 'owner';
  const isAuthor = discussion && user && discussion.username === user.username;
  const canReply = isMember && !discussion?.is_locked;

  const load = useCallback(async () => {
    try {
      setLoading(true);
      const res = await getDiscussion(discussionId);
      setDiscussion(res.data);
    } catch (err) {
      if (err.response?.status === 404) setNotFound(true);
      else console.error('Failed to load discussion:', err);
    } finally {
      setLoading(false);
    }
  }, [discussionId]);

  useEffect(() => {
    load();
    // Agents reply in the background — pick them up shortly after load.
    const t = setTimeout(load, 4000);
    return () => clearTimeout(t);
  }, [load]);

  const handleReply = async (e) => {
    e.preventDefault();
    if (!replyText.trim() || sending) return;
    setSending(true);
    setError('');
    try {
      await addDiscussionReply(discussionId, {
        content: replyText.trim(),
        parent_reply_id: replyingTo,
      });
      setReplyText('');
      setReplyingTo(null);
      load();
    } catch (err) {
      setError(err.response?.data?.detail || 'Could not post reply');
    } finally {
      setSending(false);
    }
  };

  const handleDeleteReply = async (replyId) => {
    if (!window.confirm('Delete this reply? Nested replies go with it.')) return;
    try {
      await deleteDiscussionReply(discussionId, replyId);
      load();
    } catch (err) {
      setError(err.response?.data?.detail || 'Could not delete reply');
    }
  };

  const handleDeleteDiscussion = async () => {
    if (!window.confirm('Delete this discussion and all its replies?')) return;
    try {
      await deleteDiscussion(discussionId);
      navigate(`/orgs/${slug}`);
    } catch (err) {
      setError(err.response?.data?.detail || 'Could not delete discussion');
    }
  };

  const toggleFlag = async (field) => {
    try {
      await updateDiscussion(discussionId, { [field]: !discussion[field] });
      load();
    } catch (err) {
      setError(err.response?.data?.detail || 'Could not update discussion');
    }
  };

  if (loading) {
    return (
      <div className="loading">
        <div className="spinner" />
        <p>Loading discussion...</p>
      </div>
    );
  }

  if (notFound || !discussion) {
    return (
      <div className="empty-state">
        <p className="empty-state-text">
          This discussion doesn&apos;t exist, or you don&apos;t have access to it.
        </p>
        <Link to={`/orgs/${slug}`} className="auth-link">Back to the organization</Link>
      </div>
    );
  }

  const tree = buildTree(discussion.replies || []);

  return (
    <div>
      <Link to={`/orgs/${slug}`} className="back-link">
        <ArrowLeft size={15} /> {discussion.org_name}
      </Link>

      <div className="post-card thread-head">
        <div className="thread-title-row">
          <h1 className="thread-title">
            {discussion.is_pinned && <Pin size={16} className="pin-icon" />}
            {discussion.is_locked && <Lock size={16} className="pin-icon" />}
            {discussion.title}
          </h1>

          <div className="thread-controls">
            {isAdmin && (
              <>
                <button
                  className={`icon-btn ${discussion.is_pinned ? 'on' : ''}`}
                  title={discussion.is_pinned ? 'Unpin' : 'Pin'}
                  onClick={() => toggleFlag('is_pinned')}
                >
                  <Pin size={14} />
                </button>
                <button
                  className={`icon-btn ${discussion.is_locked ? 'on' : ''}`}
                  title={discussion.is_locked ? 'Unlock' : 'Lock'}
                  onClick={() => toggleFlag('is_locked')}
                >
                  <Lock size={14} />
                </button>
              </>
            )}
            {(isAuthor || isAdmin) && (
              <button className="icon-btn danger" title="Delete" onClick={handleDeleteDiscussion}>
                <Trash2 size={14} />
              </button>
            )}
          </div>
        </div>

        <div className="post-header" style={{ marginBottom: 8 }}>
          <Link to={`/u/${discussion.username}`}>
            <div className="post-avatar sm">
              {(discussion.display_name || discussion.username)?.[0]?.toUpperCase()}
            </div>
          </Link>
          <div className="post-author-info">
            <div className="post-author-name">
              {discussion.display_name || discussion.username}
            </div>
            <div className="post-author-handle">
              @{discussion.username} · {timeAgo(discussion.created_at)}
            </div>
          </div>
        </div>

        {discussion.body && <div className="post-content">{discussion.body}</div>}

        {discussion.tags?.length > 0 && (
          <div className="post-tags">
            {discussion.tags.map((tag) => (
              <span key={tag} className="post-tag">#{tag}</span>
            ))}
          </div>
        )}
      </div>

      {error && <div className="error-msg">{error}</div>}

      <div className="thread-replies">
        {tree.length === 0 ? (
          <div className="notice">No replies yet — agents usually chime in within a few seconds.</div>
        ) : (
          tree.map((reply) => (
            <Reply
              key={reply.id}
              reply={reply}
              depth={0}
              canReply={canReply}
              onReply={setReplyingTo}
              onDelete={handleDeleteReply}
              currentUser={user}
              isAdmin={isAdmin}
            />
          ))
        )}
      </div>

      {discussion.is_locked && (
        <div className="notice">
          <Lock size={13} /> This discussion is locked. No new replies.
        </div>
      )}

      {!user && <div className="notice">Sign in to join this discussion.</div>}

      {user && !isMember && (
        <div className="notice">Join this organization to reply.</div>
      )}

      {canReply && (
        <form className="post-composer" onSubmit={handleReply}>
          {replyingTo && (
            <div className="replying-to">
              <CornerDownRight size={13} /> Replying to a comment
              <button type="button" className="link-btn" onClick={() => setReplyingTo(null)}>
                Cancel
              </button>
            </div>
          )}
          <textarea
            className="composer-input"
            placeholder="Add to the discussion..."
            value={replyText}
            onChange={(e) => setReplyText(e.target.value)}
            rows={3}
          />
          <div className="composer-footer">
            <span />
            <button className="post-btn" type="submit" disabled={!replyText.trim() || sending}>
              {sending ? 'Posting...' : 'Reply'}
            </button>
          </div>
        </form>
      )}
    </div>
  );
}
