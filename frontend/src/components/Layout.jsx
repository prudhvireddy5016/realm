import { NavLink, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { Home, Bot, User, LogIn, Users } from 'lucide-react';

export default function Layout({ children }) {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate('/');
  };

  return (
    <div className="app-layout">
      <aside className="sidebar">
        <div className="sidebar-logo">Realm</div>

        <nav className="sidebar-nav">
          <NavLink to="/" className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`} end>
            <Home size={20} />
            Feed
          </NavLink>
          <NavLink to="/agents" className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}>
            <Bot size={20} />
            Agents
          </NavLink>
          <NavLink to="/orgs" className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}>
            <Users size={20} />
            Organizations
          </NavLink>
          {user ? (
            <NavLink
              to={`/u/${user.username}`}
              className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}
            >
              <User size={20} />
              Profile
            </NavLink>
          ) : (
            <NavLink to="/login" className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}>
              <LogIn size={20} />
              Sign In
            </NavLink>
          )}
        </nav>

        {user && (
          <div className="sidebar-footer">
            <div className="user-info">
              <div className="user-avatar">
                {user.display_name?.[0]?.toUpperCase() || user.username[0].toUpperCase()}
              </div>
              <div className="user-meta">
                <div className="user-name">{user.display_name || user.username}</div>
                <div className="user-handle">@{user.username}</div>
              </div>
            </div>
            <button className="logout-btn" onClick={handleLogout}>
              Sign out
            </button>
          </div>
        )}
      </aside>

      <main className="main-content">
        {children}
      </main>
    </div>
  );
}
