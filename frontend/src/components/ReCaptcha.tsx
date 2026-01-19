import React, { useRef } from 'react';
import ReCAPTCHA from 'react-google-recaptcha';

interface ReCaptchaProps {
  onChange: (token: string | null) => void;
}

const ReCaptcha: React.FC<ReCaptchaProps> = ({ onChange }) => {
  const recaptchaRef = useRef<ReCAPTCHA>(null);
  const siteKey = import.meta.env.VITE_RECAPTCHA_SITE_KEY;

  // If key is missing - show error
  if (!siteKey) {
    return (
      <div style={{ 
        color: 'red', 
        padding: '10px', 
        border: '1px solid red',
        borderRadius: '4px',
        margin: '20px 0'
      }}>
        reCAPTCHA is not configured
      </div>
    );
  }

  return (
    <ReCAPTCHA
      ref={recaptchaRef}
      sitekey={siteKey}
      onChange={onChange}
      size="normal"
      theme="light"
    />
  );
};

export default ReCaptcha;