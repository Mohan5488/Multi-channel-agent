import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import './login.css';

const Login = ({ setLoggedIn }) => {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState('');
  const [userMessage, setUserMessage] = useState('');
  const [passwordMessage, setPasswordMessage] = useState("");
  const [generalMessage, setGeneralMessage] = useState("");
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);

  const handleLogin = async (e) => {
    e.preventDefault();
    setLoading(true);
    setUserMessage("");
    setPasswordMessage("");
    setGeneralMessage("");

    try {
      const response = await fetch('http://127.0.0.1:8000/v1/login/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password }),
      });

      const data = await response.json();
      console.log(data)

      if (response.ok) {
        localStorage.setItem('token', data.token);
        localStorage.setItem('username', data.username);
        localStorage.setItem('user_id', String(data.user_id));

        setGeneralMessage(data.message || "Login successful");

        setTimeout(() => {
          setUsername('');
          setPassword('');

          setLoggedIn(true);
          navigate('/');
        }, 800);
      }
    } catch (error) {
      console.error('Error during login:', error);
      setGeneralMessage('An error occurred. Please try again later.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="container-width login-page">
      <div className='login-box'>
        <div>
          <h1>Login</h1>
          <form onSubmit={handleLogin}>
            <label>Username:</label>
            <input
              type="text"
              value={username}
              required
              onChange={e => setUsername(e.target.value)}
            />

            <label>Password:</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
            />

            <button type="submit" disabled={loading}>
              {loading ? "Logging in..." : "Login"}
            </button>
          </form>

          {userMessage && <p className="error">{userMessage}</p>}
          {passwordMessage && <p className="error">{passwordMessage}</p>}
          <p className={generalMessage === 'Login successful' ? 'success' : ''}>{generalMessage}</p>

          {loading && <p>Loading...</p>}
        </div>

        <div>
          <img src="/assets/login.jpeg" alt="inventory image" />
        </div>
      </div>
    </div>
  );
};

export default Login;
