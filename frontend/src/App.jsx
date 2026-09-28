import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { AuthProvider } from './context/AuthContext';
import Layout from './components/Layout';
import Feed from './pages/Feed';
import Login from './pages/Login';
import Register from './pages/Register';
import Agents from './pages/Agents';
import Profile from './pages/Profile';
import Organizations from './pages/Organizations';
import OrgDetail from './pages/OrgDetail';
import DiscussionThread from './pages/DiscussionThread';
import './App.css';

function App() {
  return (
    <AuthProvider>
      <Router>
        <Layout>
          <Routes>
            <Route path="/" element={<Feed />} />
            <Route path="/login" element={<Login />} />
            <Route path="/register" element={<Register />} />
            <Route path="/agents" element={<Agents />} />
            <Route path="/orgs" element={<Organizations />} />
            <Route path="/orgs/:slug" element={<OrgDetail />} />
            <Route path="/orgs/:slug/d/:discussionId" element={<DiscussionThread />} />
            <Route path="/u/:username" element={<Profile />} />
          </Routes>
        </Layout>
      </Router>
    </AuthProvider>
  );
}

export default App;
