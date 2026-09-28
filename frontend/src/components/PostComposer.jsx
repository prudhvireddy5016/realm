import { useState } from 'react';
import { createPost } from '../api/client';
import { useAuth } from '../context/AuthContext';

const QUICK_TAGS = ['technology', 'AI', 'news', 'sports', 'art', 'health', 'music', 'politics'];

export default function PostComposer({ onPostCreated }) {
  const { user } = useAuth();
  const [content, setContent] = useState('');
  const [selectedTags, setSelectedTags] = useState([]);
  const [posting, setPosting] = useState(false);

  if (!user) return null;

  const toggleTag = (tag) => {
    setSelectedTags((prev) =>
      prev.includes(tag) ? prev.filter((t) => t !== tag) : [...prev, tag]
    );
  };

  const handleSubmit = async () => {
    if (!content.trim() || posting) return;
    setPosting(true);
    try {
      await createPost({ content: content.trim(), tags: selectedTags });
      setContent('');
      setSelectedTags([]);
      onPostCreated?.();
    } catch (err) {
      console.error('Post failed:', err);
    } finally {
      setPosting(false);
    }
  };

  return (
    <div className="post-composer">
      <textarea
        className="composer-input"
        placeholder="What's on your mind? Share with Realm..."
        value={content}
        onChange={(e) => setContent(e.target.value)}
        rows={3}
      />
      <div className="composer-footer">
        <div className="composer-tags">
          {QUICK_TAGS.map((tag) => (
            <button
              key={tag}
              className={`tag-chip ${selectedTags.includes(tag) ? 'active' : ''}`}
              onClick={() => toggleTag(tag)}
              type="button"
            >
              #{tag}
            </button>
          ))}
        </div>
        <button
          className="post-btn"
          onClick={handleSubmit}
          disabled={!content.trim() || posting}
        >
          {posting ? 'Posting...' : 'Post'}
        </button>
      </div>
    </div>
  );
}
