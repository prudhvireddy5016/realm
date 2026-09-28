import { useState } from 'react';
import { Link } from 'react-router-dom';
import { Heart, MessageCircle, Share2, Shield, ShieldAlert, ShieldCheck } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { likePost, addComment } from '../api/client';
import timeAgo from '../utils/timeAgo';

function VerificationBadge({ status }) {
  if (!status || status === 'pending') return null;

  const config = {
    verified: { icon: ShieldCheck, label: 'Verified', cls: 'verified' },
    flagged: { icon: ShieldAlert, label: 'Flagged', cls: 'flagged' },
    fake: { icon: ShieldAlert, label: 'Disputed', cls: 'flagged' },
    mixed: { icon: Shield, label: 'Unconfirmed', cls: 'pending' },
  };

  const c = config[status] || config.mixed;
  const Icon = c.icon;

  return (
    <span className={`verification-badge ${c.cls}`}>
      <Icon size={12} /> {c.label}
    </span>
  );
}

export default function PostCard({ post, onUpdate }) {
  const { user } = useAuth();
  const [liked, setLiked] = useState(post.liked_by_me || false);
  const [likeCount, setLikeCount] = useState(post.like_count || 0);
  const [showComments, setShowComments] = useState(false);
  const [commentText, setCommentText] = useState('');
  const [comments, setComments] = useState(post.comments || []);

  const handleLike = async () => {
    if (!user) return;
    try {
      const res = await likePost(post.id);
      setLiked(res.data.liked);
      setLikeCount((c) => (res.data.liked ? c + 1 : c - 1));
    } catch (err) {
      console.error('Like failed:', err);
    }
  };

  const handleComment = async (e) => {
    e.preventDefault();
    if (!commentText.trim() || !user) return;
    try {
      const res = await addComment(post.id, { content: commentText });
      setComments([...comments, res.data]);
      setCommentText('');
    } catch (err) {
      console.error('Comment failed:', err);
    }
  };

  return (
    <div className="post-card">
      <div className="post-header">
        <Link to={`/u/${post.username}`}>
          <div className="post-avatar">
            {(post.display_name || post.username)?.[0]?.toUpperCase()}
          </div>
        </Link>
        <div className="post-author-info">
          <Link to={`/u/${post.username}`} style={{ textDecoration: 'none' }}>
            <div className="post-author-name">{post.display_name || post.username}</div>
          </Link>
          <div className="post-author-handle">@{post.username}</div>
        </div>
        <span className="post-time">{timeAgo(post.created_at)}</span>
      </div>

      <div className="post-content">{post.content}</div>

      {post.tags && post.tags.length > 0 && (
        <div className="post-tags">
          {post.tags.map((tag) => (
            <span key={tag} className="post-tag">#{tag}</span>
          ))}
        </div>
      )}

      <VerificationBadge status={post.verification_status} />

      <div className="post-actions">
        <button
          className={`action-btn ${liked ? 'liked' : ''}`}
          onClick={handleLike}
        >
          <Heart size={16} fill={liked ? 'currentColor' : 'none'} />
          {likeCount > 0 && likeCount}
        </button>
        <button
          className="action-btn"
          onClick={() => setShowComments(!showComments)}
        >
          <MessageCircle size={16} />
          {comments.length > 0 && comments.length}
        </button>
        <button className="action-btn">
          <Share2 size={16} />
        </button>
      </div>

      {/* Comments section - always show agent comments, toggle for full view */}
      {(showComments || comments.some((c) => c.is_agent)) && (
        <div className="comments-section">
          {comments.map((comment) => (
            <div key={comment.id} className="comment">
              <div className={`comment-avatar ${comment.is_agent ? 'agent' : 'human'}`}>
                {comment.is_agent
                  ? (comment.agent_name?.[0] || 'A')
                  : (comment.display_name?.[0] || comment.username?.[0] || 'U')}
              </div>
              <div className="comment-body">
                <div className="comment-meta">
                  <span className="comment-author">
                    {comment.is_agent ? comment.agent_name : (comment.display_name || comment.username)}
                  </span>
                  {comment.is_agent && (
                    <span className="agent-badge">
                      {comment.agent_role || 'Agent'}
                    </span>
                  )}
                  <span className="comment-time">{timeAgo(comment.created_at)}</span>
                </div>
                <div className="comment-text">{comment.content}</div>
              </div>
            </div>
          ))}

          {user && showComments && (
            <form className="comment-input-row" onSubmit={handleComment}>
              <input
                className="comment-input"
                placeholder="Write a comment..."
                value={commentText}
                onChange={(e) => setCommentText(e.target.value)}
              />
              <button className="comment-submit" type="submit" disabled={!commentText.trim()}>
                Reply
              </button>
            </form>
          )}
        </div>
      )}
    </div>
  );
}
