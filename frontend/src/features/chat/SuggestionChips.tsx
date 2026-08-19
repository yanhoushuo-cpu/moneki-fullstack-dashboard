interface SuggestionChipsProps {
  suggestions: string[];
  disabled?: boolean;
  onSelect: (suggestion: string) => void;
}

export function SuggestionChips({ suggestions, disabled, onSelect }: SuggestionChipsProps) {
  return (
    <div className="suggestion-list" aria-label="推荐问题">
      {suggestions.map((suggestion) => (
        <button key={suggestion} type="button" disabled={disabled} onClick={() => onSelect(suggestion)}>
          {suggestion}
        </button>
      ))}
    </div>
  );
}
