import Icon from "./Icon.jsx";

/**
 * The honesty line that closes every result surface. Detection here is an
 * estimate from statistical signals — it is never proof.
 */
export default function Disclaimer({
  children = "AI detection is probabilistic and subject to false positives and negatives. Detectors are known to misjudge writing by non-native English speakers and heavily edited text. Treat these figures as one signal among many, never as proof of authorship or grounds for an accusation.",
  className = "",
}) {
  return (
    <p className={`flex items-start justify-center gap-2 text-center text-[12.5px] leading-relaxed text-outline ${className}`}>
      <Icon name="info" size={15} className="mt-px shrink-0" />
      <span className="max-w-3xl text-left">{children}</span>
    </p>
  );
}
