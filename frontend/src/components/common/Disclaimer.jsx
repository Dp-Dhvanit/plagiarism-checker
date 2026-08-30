import Icon from "./Icon.jsx";

/**
 * The honesty line that closes every result surface. Detection here is an
 * estimate from statistical signals — it is never proof.
 */
export default function Disclaimer({
  children = "AI detection is probabilistic and subject to false positives and negatives. Treat these figures as one signal among many, not as definitive proof of authorship.",
  className = "",
}) {
  return (
    <p
      className={`flex items-start justify-center gap-2 text-center font-mono text-[11px] leading-relaxed text-outline ${className}`}
    >
      <Icon name="info" size={14} className="mt-px shrink-0" />
      <span className="max-w-3xl text-left">{children}</span>
    </p>
  );
}
