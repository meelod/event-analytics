import { useState } from "react";

interface Props {
  onSubmit: (question: string) => void;
  isLoading: boolean;
}

export default function QueryBar({ onSubmit, isLoading }: Props) {
  const [question, setQuestion] = useState("");

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (question.trim()) onSubmit(question.trim());
  };

  const examples = [
    "Show daily active users for the last 30 days",
    "What are the top 5 events this week?",
    "Show conversion from signup to purchase by day",
  ];

  return (
    <div className="space-y-3">
      <form onSubmit={handleSubmit} className="flex gap-3">
        <input
          type="text"
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          placeholder="Ask a question about your events..."
          className="flex-1 px-4 py-3 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
          disabled={isLoading}
        />
        <button
          type="submit"
          disabled={isLoading || !question.trim()}
          className="px-6 py-3 bg-indigo-600 text-white text-sm font-medium rounded-lg hover:bg-indigo-700 disabled:opacity-50 transition-colors whitespace-nowrap"
        >
          {isLoading ? "Analyzing..." : "Ask"}
        </button>
      </form>
      <div className="flex flex-wrap gap-2">
        {examples.map((ex) => (
          <button
            key={ex}
            onClick={() => {
              setQuestion(ex);
              onSubmit(ex);
            }}
            disabled={isLoading}
            className="px-3 py-1 text-xs bg-gray-100 text-gray-600 rounded-full hover:bg-gray-200 disabled:opacity-50 transition-colors"
          >
            {ex}
          </button>
        ))}
      </div>
    </div>
  );
}
