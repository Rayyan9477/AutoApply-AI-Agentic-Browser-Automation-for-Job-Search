import { ICON_PATHS, type IconName } from './iconPaths';

export type { IconName };

interface IconProps {
  name: IconName;
  size?: number;
  sw?: number;
  color?: string;
  style?: React.CSSProperties;
}

/** Render a design-system line icon (24×24 viewBox, currentColor stroke, round caps/joins). */
export function Icon({ name, size = 16, sw = 1.75, color, style }: IconProps) {
  const paths = ICON_PATHS[name] ?? [];
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke={color ?? 'currentColor'}
      strokeWidth={sw}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      style={{ display: 'block', ...style }}
    >
      {paths.map((d, i) => (
        <path key={i} d={d} />
      ))}
    </svg>
  );
}

export default Icon;
