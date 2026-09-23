/* Thin parallel line-art sweeps. Color comes from CSS `color`. */
const range = (n) => Array.from({ length: n }, (_, i) => i);

export default function Waves({ className }) {
  return (
    <svg className={className} viewBox="0 0 1440 880" preserveAspectRatio="xMidYMid slice" aria-hidden="true">
      <g fill="none" stroke="currentColor" strokeWidth="1">
        {range(26).map((i) => (
          <path key={`a${i}`} d={`M${-160 + i * 11} -20 C ${160 + i * 9} ${260 + i * 5}, ${380 + i * 7} ${560 - i * 2}, ${860 + i * 6} 920`} />
        ))}
        {range(26).map((i) => (
          <path key={`b${i}`} d={`M1600 ${140 + i * 10} C ${1260 - i * 4} ${300 + i * 8}, ${1120 - i * 6} ${640 + i * 3}, ${760 - i * 9} 940`} />
        ))}
      </g>
    </svg>
  );
}
