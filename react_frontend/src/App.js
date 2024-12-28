import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate, useParams, useLocation } from 'react-router-dom';
import Login from './pages/Login';
import Register from './pages/Register';
import StudyDashboard from './pages/StudyDashboard';
import PingTemplateDashboard from './pages/PingTemplateDashboard';
import StudyEnroll from './pages/StudyEnroll';
import PingDashboard from './pages/PingDashboard';
import EnrollmentDashboard from './pages/EnrollmentDashboard';
import ViewStudy from './pages/ViewStudy';
import PrivateRoute from './components/PrivateRoute';
import NavBar from './components/NavBar';
import { StudyProvider } from './context/StudyContext';

function StudyWrapper({ children }) {
  const { studyId } = useParams();
  return <StudyProvider studyId={studyId}>{children}</StudyProvider>;
}

function Layout() {
  const location = useLocation();

  // List of routes where the navbar should be hidden
  const hideNavBarRoutes = ['/enroll'];

  // Check if the current route matches any of the hideNavBarRoutes
  const shouldHideNavBar = hideNavBarRoutes.some((route) =>
    location.pathname.startsWith(route)
  );

  return (
    <div>
      {/* Conditionally render NavBar */}
      {!shouldHideNavBar && <NavBar />}
      <main>
        <Routes>
          {/* Public routes */}
          <Route path="/login" element={<Login />} />
          <Route path="/register" element={<Register />} />
          <Route path="/enroll/:signup_code" element={<StudyEnroll />} />

          {/* Protected routes */}
          <Route
            path="/studies"
            element={
              <PrivateRoute>
                <StudyDashboard />
              </PrivateRoute>
            }
          />

          {/* Wrap the child route in StudyWrapper */}
          <Route
            path="/studies/:studyId"
            element={
              <PrivateRoute>
                <StudyWrapper>
                  <ViewStudy />
                </StudyWrapper>
              </PrivateRoute>
            }
          />
          <Route
            path="/studies/:studyId/ping_templates"
            element={
              <PrivateRoute>
                <StudyWrapper>
                  <PingTemplateDashboard />
                </StudyWrapper>
              </PrivateRoute>
            }
          />
          <Route
            path="/studies/:studyId/pings"
            element={
              <PrivateRoute>
                <StudyWrapper>
                  <PingDashboard />
                </StudyWrapper>
              </PrivateRoute>
            }
          />
          <Route
            path="/studies/:studyId/participants"
            element={
              <PrivateRoute>
                <StudyWrapper>
                  <EnrollmentDashboard />
                </StudyWrapper>
              </PrivateRoute>
            }
          />

          {/* Catch-all route */}
          <Route path="*" element={<Navigate to="/studies" />} />
        </Routes>
      </main>
    </div>
  );
}

function App() {
  return (
    <Router>
      <Layout />
    </Router>
  );
}

export default App;