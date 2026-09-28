import { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import { getUserProfile, getUserPosts } from '../api/client';
import PostCard from '../components/PostCard';

export default function Profile() {
  const { username } = useParams();
  const [profile, setProfile] = useState(null);
  const [posts, setPosts] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    Promise.all([getUserProfile(username), getUserPosts(username)])
      .then(([profileRes, postsRes]) => {
        setProfile(profileRes.data);
        setPosts(postsRes.data);
      })
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [username]);

  if (loading) {
    return (
      <div className="loading">
        <div className="spinner" />
        <p>Loading profile...</p>
      </div>
    );
  }

  if (!profile) {
    return (
      <div className="empty-state">
        <p className="empty-state-text">User not found.</p>
      </div>
    );
  }

  return (
    <div>
      <div className="profile-header">
        <div className="profile-avatar">
          {(profile.display_name || profile.username)?.[0]?.toUpperCase()}
        </div>
        <h1 className="profile-name">{profile.display_name || profile.username}</h1>
        <p className="profile-handle">@{profile.username}</p>
        {profile.bio && <p className="profile-bio">{profile.bio}</p>}

        <div className="profile-stats">
          <div className="stat">
            <div className="stat-value">{profile.post_count}</div>
            <div className="stat-label">Posts</div>
          </div>
          <div className="stat">
            <div className="stat-value">{profile.follower_count}</div>
            <div className="stat-label">Followers</div>
          </div>
          <div className="stat">
            <div className="stat-value">{profile.following_count}</div>
            <div className="stat-label">Following</div>
          </div>
        </div>
      </div>

      {posts.length > 0 ? (
        posts.map((post) => <PostCard key={post.id} post={post} />)
      ) : (
        <div className="empty-state">
          <p className="empty-state-text">No posts yet.</p>
        </div>
      )}
    </div>
  );
}
