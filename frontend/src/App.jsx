import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import Auth from './pages/Auth';
import Dashboard from './pages/Dashboard';
import UploadPage from './pages/UploadPage';
import HistoryPage from './pages/HistoryPage';
import Layout from './components/Layout';
import PrivateRoute from './components/PrivateRoute';

function App() {
  return (
    <Router>
      <Routes>
        <Route path="/dashboard" element={
          <Layout>
            <Dashboard />
          </Layout>
        } />

        <Route path="/upload" element={
          <Layout>
            <UploadPage />
          </Layout>
        } />

        <Route path="/history" element={
          <Layout>
            <HistoryPage />
          </Layout>
        } />

        <Route path="/" element={<Navigate to="/upload" replace />} />
        <Route path="*" element={<Navigate to="/upload" replace />} />
      </Routes>
    </Router>
  );
}

export default App;
