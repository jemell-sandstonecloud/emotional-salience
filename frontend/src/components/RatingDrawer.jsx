import React, { useState, useMemo } from 'react';

const SLIDER_LABELS = {
  attunement: { name: 'Attunement', low: 'Not at all', high: 'Perfectly' },
  contextual_accuracy: { name: 'Contextual Accuracy', low: 'Inaccurate', high: 'Highly accurate' },
  naturalness: { name: 'Naturalness', low: 'Artificial', high: 'Completely natural' },
};

function Slider({ label, lowLabel, highLabel, value, onChange }) {
  return (
    <div className="space-y-1">
      <div className="flex justify-between text-xs text-gray-400">
        <span>{label}</span>
        <span className="text-sand-400 font-medium">{value}</span>
      </div>
      <input
        type="range"
        min={1} max={7} step={1}
        value={value}
        onChange={(e) => onChange(parseInt(e.target.value))}
        className="w-full h-2 rounded-lg appearance-none cursor-pointer slider-track"
      />
      <div className="flex justify-between text-[10px] text-gray-600">
        <span>{lowLabel}</span>
        <span>{highLabel}</span>
      </div>
    </div>
  );
}

export default function RatingDrawer({ visible, onSubmit, onClose }) {
  const [ratings, setRatings] = useState({
    response_a_attunement: 4,
    response_a_contextual_accuracy: 4,
    response_a_naturalness: 4,
    response_b_attunement: 4,
    response_b_contextual_accuracy: 4,
    response_b_naturalness: 4,
  });
  const [preference, setPreference] = useState(null); // 'A' | 'B' | 'none'
  const [touched, setTouched] = useState(new Set());

  const allTouched = useMemo(() => touched.size >= 6 && preference !== null, [touched, preference]);

  const updateRating = (key, val) => {
    setRatings((prev) => ({ ...prev, [key]: val }));
    setTouched((prev) => new Set(prev).add(key));
  };

  const handleSubmit = () => {
    if (!allTouched) return;
    onSubmit({ ...ratings, preference });
    // Reset for next exchange
    setRatings({
      response_a_attunement: 4, response_a_contextual_accuracy: 4, response_a_naturalness: 4,
      response_b_attunement: 4, response_b_contextual_accuracy: 4, response_b_naturalness: 4,
    });
    setPreference(null);
    setTouched(new Set());
  };

  if (!visible) return null;

  return (
    <div className="fixed inset-x-0 bottom-0 bg-gray-900 border-t border-gray-700 rounded-t-2xl shadow-2xl z-50 animate-slide-up max-h-[70vh] overflow-y-auto">
      <div className="p-4 max-w-4xl mx-auto">
        <div className="flex justify-between items-center mb-3">
          <h3 className="text-sm font-semibold text-sand-400">Rate These Responses</h3>
          <button onClick={onClose} className="text-gray-500 hover:text-white text-xs">✕</button>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* Response A ratings */}
          <div className="space-y-3">
            <h4 className="text-xs font-medium text-blue-400 uppercase tracking-wide">Response A</h4>
            {Object.entries(SLIDER_LABELS).map(([key, { name, low, high }]) => (
              <Slider
                key={`a_${key}`}
                label={name}
                lowLabel={low}
                highLabel={high}
                value={ratings[`response_a_${key}`]}
                onChange={(v) => updateRating(`response_a_${key}`, v)}
              />
            ))}
          </div>

          {/* Response B ratings */}
          <div className="space-y-3">
            <h4 className="text-xs font-medium text-emerald-400 uppercase tracking-wide">Response B</h4>
            {Object.entries(SLIDER_LABELS).map(([key, { name, low, high }]) => (
              <Slider
                key={`b_${key}`}
                label={name}
                lowLabel={low}
                highLabel={high}
                value={ratings[`response_b_${key}`]}
                onChange={(v) => updateRating(`response_b_${key}`, v)}
              />
            ))}
          </div>
        </div>

        {/* Preference toggle */}
        <div className="mt-4 text-center">
          <p className="text-xs text-gray-400 mb-2">Which would you prefer to continue talking to?</p>
          <div className="flex justify-center gap-2">
            {['A', 'B', 'none'].map((opt) => (
              <button
                key={opt}
                onClick={() => setPreference(opt)}
                className={`px-4 py-1.5 rounded-lg text-xs font-medium transition ${
                  preference === opt
                    ? 'bg-sand-600 text-white'
                    : 'bg-gray-800 text-gray-400 hover:bg-gray-700'
                }`}
              >
                {opt === 'none' ? 'No preference' : `Response ${opt}`}
              </button>
            ))}
          </div>
        </div>

        {/* Submit */}
        <button
          onClick={handleSubmit}
          disabled={!allTouched}
          className="w-full mt-4 py-2 bg-sand-600 hover:bg-sand-500 text-white rounded-lg text-sm font-medium transition disabled:opacity-30 disabled:cursor-not-allowed"
        >
          Submit Ratings
        </button>
      </div>
    </div>
  );
}
