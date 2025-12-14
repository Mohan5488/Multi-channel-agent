import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import ChatLayout from './components/ChatLayout';
import Testing from './components/Testing';
import Login from './components/Login';
import { useState, useEffect } from 'react';
import HomePage from './components/HomePage';

function App() {
  const [isLoggedIn, setLoggedIn] = useState(!!localStorage.getItem('token')); // Ensure it reads from storage

  useEffect(() => {
    const token = localStorage.getItem('token');
    if (token) {
      setLoggedIn(true);
    }
  }, []);

  return (
    <>
      {isLoggedIn ? (
        <Routes>
          <Route path="/" element={<Navigate to="/chat" replace />} />
          <Route path="/chat" element={<ChatLayout setLoggedIn={setLoggedIn} />} />
          <Route path="/chat/:id" element={<ChatLayout setLoggedIn={setLoggedIn} />} />
          <Route path="/test" element={<Testing />} />
          <Route path="*" element={<Navigate to="/chat"/>} />
        </Routes>
      ) : (
        <Routes>
          <Route index element={<HomePage />} />
          <Route path="/login" element={<Login setLoggedIn={setLoggedIn} />} />
          <Route path="*" element={<Navigate to="/login"/>} />
        </Routes>
      )}
    </> 
  );
}

export default App;
