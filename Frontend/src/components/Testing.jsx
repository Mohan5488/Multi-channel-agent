import React, { useEffect, useState } from "react";

export default function Testing() {
  const token = "f933d26b4c6420a5161c39b47ab7ef9bfe8326a4"; // DRF token
  const [message, setMessage] = useState("");

  // Handle OAuth redirect success
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const status = params.get("status");
    const service = params.get("service");

    if (status === "success" && service) {
      setMessage(`✅ ${service.charAt(0).toUpperCase() + service.slice(1)} connected successfully!`);
    }
  }, []);

  const handleConnectGmail = async () => {
    if (!token) {
      alert("Please login first!");
      return;
    }

    try {
      const response = await fetch("http://127.0.0.1:8000/v1/connect_gmail/", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Token ${token}`,
        },
        body: JSON.stringify({ user_id: 5 }),
      });

      const data = await response.json();
      window.location.href = data.auth_url;
    } catch (err) {
      console.error("Error connecting Gmail:", err);
      alert("Failed to connect Gmail: " + err.message);
    }
  };

  const handleConnectCalendar = async () => {
    if (!token) {
      alert("Please login first!");
      return;
    }

    try {
      const response = await fetch("http://127.0.0.1:8000/v1/connect_calendar/", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Token ${token}`,
        },
        body: JSON.stringify({ user_id: 5 }),
      });

      const data = await response.json();
      window.location.href = data.auth_url;
    } catch (err) {
      console.error("Error connecting Calendar:", err);
      alert("Failed to connect Calendar: " + err.message);
    }
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: "20px", marginTop: "50px" }}>
      {message && <div style={{ backgroundColor: "#d4edda", color: "#155724", padding: "15px 20px", borderRadius: "5px", fontWeight: "bold" }}>{message}</div>}

      <div style={{ display: "flex", gap: "20px" }}>
        <button onClick={handleConnectGmail} style={styles.gmailButton}>Connect Gmail</button>
        <button onClick={handleConnectCalendar} style={styles.calendarButton}>Connect Calendar</button>
        
      </div>
    </div>
  );
}

const styles = {
  gmailButton: {
    backgroundColor: "#4285F4",
    color: "white",
    padding: "12px 24px",
    border: "none",
    borderRadius: "5px",
    fontSize: "16px",
    cursor: "pointer",
  },
  calendarButton: {
    backgroundColor: "#34A853",
    color: "white",
    padding: "12px 24px",
    border: "none",
    borderRadius: "5px",
    fontSize: "16px",
    cursor: "pointer",
  },
};
