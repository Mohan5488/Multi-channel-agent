import React from 'react';
import AgentChat from './AgentChat';
import ThreadList from './ThreadList';

export default function ChatLayout({setLoggedIn}) {
  return (
    <div style={{ height: '100vh', width: '100vw', display: 'flex', overflow: 'hidden' }}>
      <ThreadList />
      <div style={{ flex: 1}}>
        <AgentChat setLoggedIn={setLoggedIn}/>
      </div>
    </div>
  );
}


