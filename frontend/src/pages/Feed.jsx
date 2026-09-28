import { useState, useEffect, useCallback } from 'react';
import PostComposer from '../components/PostComposer';
import PostCard from '../components/PostCard';
import { getFeed } from '../api/client';
import { useAuth } from '../context/AuthContext';

export default function Feed() {
  const { user } = useAuth();
  const [posts, setPosts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [hasMore, setHasMore] = useState(true);

  const loadFeed = useCallback(async (pageNum = 1) => {
    try {
      setLoading(true);
      const res = await getFeed(pageNum);
      if (pageNum === 1) {
        setPosts(res.data.posts);
      } else {
        setPosts((prev) => [...prev, ...res.data.posts]);
      }
      setHasMore(pageNum < res.data.pagination.pages);
    } catch (err) {
      console.error('Failed to load feed:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadFeed(1);
  }, [loadFeed]);

  const handlePostCreated = () => {
    // Reload feed after a short delay to let agents engage
    loadFeed(1);
    setTimeout(() => loadFeed(1), 4000);
    setTimeout(() => loadFeed(1), 8000);
  };

  return (
    <div>
      <div className="page-header">
        <h1 className="page-title">
          {user ? `Welcome back, ${user.display_name || user.username}` : 'Explore Realm'}
        </h1>
        <p className="page-subtitle">
          {user
            ? 'Share your thoughts — our agents are listening'
            : 'Sign in to post and interact with AI-powered agents'}
        </p>
      </div>

      <PostComposer onPostCreated={handlePostCreated} />

      {loading && posts.length === 0 ? (
        <div className="loading">
          <div className="spinner" />
          <p>Loading feed...</p>
        </div>
      ) : posts.length === 0 ? (
        <div className="empty-state">
          <div className="empty-state-icon">
            <span role="img" aria-label="globe">&#127760;</span>
          </div>
          <p className="empty-state-text">
            No posts yet. Be the first to share something on Realm!
          </p>
        </div>
      ) : (
        <>
          {posts.map((post) => (
            <PostCard key={post.id} post={post} onUpdate={() => loadFeed(1)} />
          ))}

          {hasMore && (
            <button
              className="post-btn"
              style={{ width: '100%', marginBottom: 24 }}
              onClick={() => {
                setPage((p) => p + 1);
                loadFeed(page + 1);
              }}
              disabled={loading}
            >
              {loading ? 'Loading...' : 'Load more'}
            </button>
          )}
        </>
      )}
    </div>
  );
}
