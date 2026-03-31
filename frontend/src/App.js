import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { AnimatePresence } from 'framer-motion';
import Navbar from './components/Navbar/Navbar';
import LandingPage from './components/LandingPage/LandingPage';
import Dashboard from './components/Dashboard/Dashboard';
import ModelUpload from './components/ModelUpload/ModelUpload';
import CameraManager from './components/CameraManager/CameraManager';
import VideoStream from './components/VideoStream/VideoStream';
import DetectionHistory from './components/DetectionHistory/DetectionHistory';
import './App.css';

function App() {
  return (
    <Router>
      <div className="app">
        <Routes>
          <Route path="/" element={<LandingPage />} />
          <Route
            path="/*"
            element={
              <>
                <Navbar />
                <main className="app-main">
                  <AnimatePresence mode="wait">
                    <Routes>
                      <Route path="/dashboard" element={<Dashboard />} />
                      <Route path="/models" element={<ModelUpload />} />
                      <Route path="/cameras" element={<CameraManager />} />
                      <Route path="/stream" element={<VideoStream />} />
                      <Route path="/detections" element={<DetectionHistory />} />
                    </Routes>
                  </AnimatePresence>
                </main>
              </>
            }
          />
        </Routes>
      </div>
    </Router>
  );
}

export default App;
