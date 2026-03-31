import React, { useRef, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion, useAnimation, useInView } from 'framer-motion';
import './LandingPage.css';

const features = [
  {
    icon: '⬡',
    title: 'Upload YOLO Weights',
    desc: 'Support for .pt, .engine and .onnx model files. Upload once, run anywhere.',
  },
  {
    icon: '◎',
    title: 'Multi-Camera Support',
    desc: 'Connect unlimited RTSP cameras simultaneously. Each stream runs in isolation.',
  },
  {
    icon: '▶',
    title: 'Real-Time Inference',
    desc: 'Low-latency YOLO inference streamed live to your browser via WebSocket.',
  },
  {
    icon: '◈',
    title: 'PostgreSQL Storage',
    desc: 'Every detection is logged with timestamp, confidence, bbox and snapshot.',
  },
];

function AnimatedSection({ children, delay = 0 }) {
  const ref = useRef(null);
  const inView = useInView(ref, { once: true, margin: '-80px' });
  return (
    <motion.div
      ref={ref}
      initial={{ opacity: 0, y: 40 }}
      animate={inView ? { opacity: 1, y: 0 } : {}}
      transition={{ duration: 0.6, delay, ease: 'easeOut' }}
    >
      {children}
    </motion.div>
  );
}

export default function LandingPage() {
  const navigate = useNavigate();

  return (
    <div className="landing">
      {/* Animated background grid */}
      <div className="landing__bg-grid" />
      <div className="landing__bg-glow landing__bg-glow--1" />
      <div className="landing__bg-glow landing__bg-glow--2" />

      {/* Hero */}
      <section className="landing__hero">
        <motion.div
          className="landing__hero-badge"
          initial={{ opacity: 0, scale: 0.8 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.5 }}
        >
          <span className="badge-dot" />
          <span>Powered by Ultralytics YOLO</span>
        </motion.div>

        <motion.h1
          className="landing__hero-title"
          initial={{ opacity: 0, y: 30 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.7, delay: 0.1 }}
        >
          Real-Time
          <br />
          <span className="hero-gradient">AI Inference</span>
          <br />
          on Any Camera
        </motion.h1>

        <motion.p
          className="landing__hero-subtitle"
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.7, delay: 0.25 }}
        >
          Upload your YOLO model weights, connect RTSP camera streams,
          and watch detections happen in real time — stored automatically.
        </motion.p>

        <motion.div
          className="landing__hero-actions"
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.7, delay: 0.4 }}
        >
          <motion.button
            className="btn btn--primary"
            onClick={() => navigate('/dashboard')}
            whileHover={{ scale: 1.04, boxShadow: '0 0 30px rgba(99,102,241,0.5)' }}
            whileTap={{ scale: 0.97 }}
          >
            Get Started →
          </motion.button>
          <motion.button
            className="btn btn--ghost"
            onClick={() => navigate('/models')}
            whileHover={{ scale: 1.04 }}
            whileTap={{ scale: 0.97 }}
          >
            Upload Model
          </motion.button>
        </motion.div>

        {/* Hero visual */}
        <motion.div
          className="landing__hero-visual"
          initial={{ opacity: 0, y: 40 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.9, delay: 0.55 }}
        >
          <div className="hero-window">
            <div className="hero-window__bar">
              <span className="window-dot dot--red" />
              <span className="window-dot dot--yellow" />
              <span className="window-dot dot--green" />
              <span className="window-label">Live Feed · Camera 01</span>
            </div>
            <div className="hero-window__body">
              <div className="hero-mock-stream">
                <div className="hero-mock-bbox hero-mock-bbox--1">
                  <span className="mock-label">Person 0.94</span>
                </div>
                <div className="hero-mock-bbox hero-mock-bbox--2">
                  <span className="mock-label">Helmet 0.87</span>
                </div>
                <div className="hero-scan-line" />
              </div>
              <div className="hero-window__stats">
                <div className="stat-chip stat-chip--green">
                  <span className="stat-dot" />
                  <span>LIVE</span>
                </div>
                <span className="stat-fps">47 FPS</span>
                <span className="stat-count">12 detections</span>
              </div>
            </div>
          </div>
        </motion.div>
      </section>

      {/* Features */}
      <section className="landing__features">
        <AnimatedSection>
          <h2 className="landing__section-title">Everything you need</h2>
          <p className="landing__section-sub">
            One platform to manage models, cameras, streams, and results.
          </p>
        </AnimatedSection>

        <div className="landing__features-grid">
          {features.map((f, i) => (
            <AnimatedSection key={f.title} delay={i * 0.1}>
              <motion.div
                className="feature-card"
                whileHover={{ y: -6, borderColor: 'rgba(99,102,241,0.5)' }}
                transition={{ duration: 0.2 }}
              >
                <div className="feature-card__icon">{f.icon}</div>
                <h3 className="feature-card__title">{f.title}</h3>
                <p className="feature-card__desc">{f.desc}</p>
              </motion.div>
            </AnimatedSection>
          ))}
        </div>
      </section>

      {/* Steps */}
      <section className="landing__steps">
        <AnimatedSection>
          <h2 className="landing__section-title">Up and running in 3 steps</h2>
        </AnimatedSection>
        <div className="steps-list">
          {[
            { n: '01', title: 'Upload Weights', desc: 'Drop your .pt file — any YOLO model.' },
            { n: '02', title: 'Add Cameras', desc: 'Paste RTSP URLs for each camera.' },
            { n: '03', title: 'Start Inferencing', desc: 'Hit Start and watch it run live.' },
          ].map((s, i) => (
            <AnimatedSection key={s.n} delay={i * 0.15}>
              <div className="step">
                <div className="step__number">{s.n}</div>
                <div className="step__content">
                  <h4 className="step__title">{s.title}</h4>
                  <p className="step__desc">{s.desc}</p>
                </div>
              </div>
            </AnimatedSection>
          ))}
        </div>
      </section>

      {/* CTA */}
      <section className="landing__cta">
        <AnimatedSection>
          <div className="cta-box">
            <h2 className="cta-box__title">Ready to start detecting?</h2>
            <p className="cta-box__sub">Open the dashboard and set up your first inference pipeline.</p>
            <motion.button
              className="btn btn--primary btn--lg"
              onClick={() => navigate('/dashboard')}
              whileHover={{ scale: 1.05, boxShadow: '0 0 40px rgba(99,102,241,0.5)' }}
              whileTap={{ scale: 0.97 }}
            >
              Open Dashboard →
            </motion.button>
          </div>
        </AnimatedSection>
      </section>

      <footer className="landing__footer">
        <p>Model Inference Platform · Built with FastAPI + React + YOLO</p>
      </footer>
    </div>
  );
}
