import React, { useState } from 'react';
import { consent } from '../api';

export default function Consent({ onConsent }) {
  const [agreed, setAgreed] = useState(false);
  const [loading, setLoading] = useState(false);

  const handleContinue = async () => {
    setLoading(true);
    try {
      await consent();
      onConsent();
    } catch {
      onConsent(); // Continue even if API fails
    }
  };

  return (
    <div className="flex items-center justify-center min-h-screen px-4">
      <div className="w-full max-w-lg bg-gray-900 rounded-xl p-6 border border-gray-800">
        <h2 className="text-xl font-semibold mb-4">Study Information</h2>

        <div className="space-y-3 text-sm text-gray-300 leading-relaxed">
          <p>
            Thank you for participating in this conversation study. You will be chatting
            with two AI systems side by side and providing feedback on each response.
          </p>
          <p>
            <strong className="text-white">What to expect:</strong> You will see two responses
            labeled "Response A" and "Response B" for each message you send. After each exchange,
            you will rate both responses on three dimensions and indicate which you prefer.
          </p>
          <p>
            <strong className="text-white">Duration:</strong> Each session takes approximately
            15–30 minutes. You may participate in multiple sessions over several days.
          </p>
          <p>
            <strong className="text-white">Privacy:</strong> Your conversation data and ratings
            are stored securely and used only for this research study. Your email is used for
            login only and is not shared.
          </p>
          <p>
            <strong className="text-white">Withdrawal:</strong> You may stop participating at
            any time without consequence.
          </p>
        </div>

        <label className="flex items-start gap-3 mt-6 cursor-pointer">
          <input
            type="checkbox"
            checked={agreed}
            onChange={(e) => setAgreed(e.target.checked)}
            className="mt-1 accent-sand-500"
          />
          <span className="text-sm text-gray-400">
            I have read and understand the study information above, and I consent to participate.
          </span>
        </label>

        <button
          onClick={handleContinue}
          disabled={!agreed || loading}
          className="w-full mt-4 py-2 bg-sand-600 hover:bg-sand-500 text-white rounded-lg text-sm font-medium transition disabled:opacity-30 disabled:cursor-not-allowed"
        >
          {loading ? '...' : 'Continue to Study'}
        </button>
      </div>
    </div>
  );
}
