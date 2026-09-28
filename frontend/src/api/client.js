import axios from 'axios';

const API_URL = import.meta.env.VITE_API_URL || '';

const api = axios.create({
  baseURL: `${API_URL}/api`,
});

// Add auth token to requests
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('realm_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Auth
export const register = (data) => api.post('/auth/register', data);
export const login = (data) => api.post('/auth/login', data);
export const getMe = () => api.get('/auth/me');

// Posts
export const createPost = (data) => api.post('/posts', data);
export const getPost = (id) => api.get(`/posts/${id}`);
export const deletePost = (id) => api.delete(`/posts/${id}`);
export const likePost = (id) => api.post(`/posts/${id}/like`);

// Feed
export const getFeed = (page = 1) => api.get(`/feed?page=${page}`);

// Comments
export const getComments = (postId) => api.get(`/comments/post/${postId}`);
export const addComment = (postId, data) => api.post(`/comments/post/${postId}`, data);

// Agents
export const getAgents = () => api.get('/agents');
export const createCommunityAgent = (data) => api.post('/agents/community', data);

// Users
export const getUserProfile = (username) => api.get(`/users/${username}`);
export const getUserPosts = (username) => api.get(`/users/${username}/posts`);
export const toggleFollow = (username) => api.post(`/users/${username}/follow`);

// Organizations
export const getOrgs = (mine = false) => api.get(`/orgs${mine ? '?mine=true' : ''}`);
export const getOrg = (slug) => api.get(`/orgs/${slug}`);
export const createOrg = (data) => api.post('/orgs', data);
export const updateOrg = (slug, data) => api.patch(`/orgs/${slug}`, data);
export const deleteOrg = (slug) => api.delete(`/orgs/${slug}`);
export const joinOrg = (slug) => api.post(`/orgs/${slug}/join`);
export const leaveOrg = (slug) => api.delete(`/orgs/${slug}/leave`);
export const getOrgMembers = (slug) => api.get(`/orgs/${slug}/members`);
export const addOrgMember = (slug, data) => api.post(`/orgs/${slug}/members`, data);
export const updateOrgMember = (slug, username, data) =>
  api.patch(`/orgs/${slug}/members/${username}`, data);
export const removeOrgMember = (slug, username) =>
  api.delete(`/orgs/${slug}/members/${username}`);

// Discussions
export const getDiscussions = (slug) => api.get(`/orgs/${slug}/discussions`);
export const createDiscussion = (slug, data) => api.post(`/orgs/${slug}/discussions`, data);
export const getDiscussion = (id) => api.get(`/discussions/${id}`);
export const updateDiscussion = (id, data) => api.patch(`/discussions/${id}`, data);
export const deleteDiscussion = (id) => api.delete(`/discussions/${id}`);
export const addDiscussionReply = (id, data) => api.post(`/discussions/${id}/replies`, data);
export const deleteDiscussionReply = (discussionId, replyId) =>
  api.delete(`/discussions/${discussionId}/replies/${replyId}`);

export default api;
