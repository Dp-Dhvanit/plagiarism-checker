/**
 * Material Symbols Outlined glyph. The font is loaded with `display=block`
 * in index.html so the ligature name never flashes as raw text.
 */
export default function Icon({ name, size = 20, fill = false, className = "", style, ...rest }) {
  return (
    <span
      aria-hidden="true"
      className={`ms${fill ? " ms-fill" : ""} ${className}`}
      style={{ fontSize: size, width: size, height: size, ...style }}
      {...rest}
    >
      {name}
    </span>
  );
}
