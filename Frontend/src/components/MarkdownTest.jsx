import React from 'react';
import MarkdownRenderer from './MarkdownRenderer';

const MarkdownTest = () => {
  const sampleContent = `**Current Weather for VZM (Vizianagaram, Andhra Pradesh, India) – September 19 2025**

| Parameter | Value |
|-----------|-------|
| **Condition** | Mostly sunny |
| **Temperature** | 95 °F / 35 °C (high) – 75 °F / 24 °C (low) |
| **Feels Like** | 104 °F / 40 °C |
| **Wind** | 5 mph (≈ 8 km/h) from the north‑east |
| **Humidity** | 57 % |
| **Chance of Precipitation** | 5 % (very low) |
| **UV Index** | 5 (moderate) |
| **Sunrise / Sunset** | 5:44 am / 5:55 pm (local time) |
| **Visibility** | ~2 mi (≈ 3 km) |

*The data is taken from the latest "CustomWeather" report on Time & Date (updated early morning on Sep 19, 2025).*

If you need a more detailed hourly forecast or a longer‑range outlook, let me know and I can pull that up for you!`;

  return (
    <div style={{ padding: '20px', maxWidth: '800px', margin: '0 auto' }}>
      <h2>Markdown Test</h2>
      <div style={{ 
        background: '#f8fafc', 
        border: '1px solid #eef2ff', 
        borderRadius: '12px', 
        padding: '16px',
        margin: '20px 0'
      }}>
        <MarkdownRenderer content={sampleContent} />
      </div>
    </div>
  );
};

export default MarkdownTest;

