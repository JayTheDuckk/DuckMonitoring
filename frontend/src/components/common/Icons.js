import React from 'react';

const Svg = ({ children, size = 16, ...props }) => (
  <svg
    width={size}
    height={size}
    viewBox="0 0 16 16"
    fill="none"
    stroke="currentColor"
    strokeWidth="1.6"
    strokeLinecap="square"
    strokeLinejoin="miter"
    aria-hidden="true"
    {...props}
  >
    {children}
  </svg>
);

export const RefreshIcon = (props) => (
  <Svg {...props}>
    <path d="M13.2 8A5.2 5.2 0 1 1 11.6 4.4" />
    <path d="M13.2 2.4V5.6H10" />
  </Svg>
);

export const PlusIcon = (props) => (
  <Svg {...props}>
    <path d="M8 3v10M3 8h10" />
  </Svg>
);

export const ChevronIcon = ({ expanded, ...props }) => (
  <Svg {...props} style={{ transform: expanded ? 'rotate(180deg)' : 'none', transition: 'transform 0.15s' }}>
    <path d="M3.5 6.2L8 10.8l4.5-4.6" />
  </Svg>
);

export const EditIcon = (props) => (
  <Svg {...props}>
    <path d="M9.2 3.6l3.2 3.2-7.6 7.6H1.6v-3.2L9.2 3.6z" />
    <path d="M7.8 5l3.2 3.2" />
  </Svg>
);

export const CloseIcon = (props) => (
  <Svg {...props}>
    <path d="M4 4l8 8M12 4l-8 8" />
  </Svg>
);

export const AgentIcon = (props) => (
  <Svg {...props}>
    <rect x="2.5" y="4" width="11" height="8" />
    <path d="M5 12.5V14M11 12.5V14M6.5 7h3" />
  </Svg>
);

export const SearchIcon = (props) => (
  <Svg {...props}>
    <circle cx="7" cy="7" r="3.4" />
    <path d="M9.6 9.6L13 13" />
  </Svg>
);

export const SunIcon = (props) => (
  <Svg {...props}>
    <circle cx="8" cy="8" r="2.4" />
    <path d="M8 2.4v1.6M8 12v1.6M2.4 8h1.6M12 8h1.6M4 4l1.1 1.1M10.9 10.9L12 12M12 4l-1.1 1.1M5.1 10.9L4 12" />
  </Svg>
);

export const MoonIcon = (props) => (
  <Svg {...props}>
    <path d="M11.4 10.2A5 5 0 0 1 6 3.4 5.2 5.2 0 1 0 11.4 10.2z" />
  </Svg>
);

export const UsersIcon = (props) => (
  <Svg {...props}>
    <circle cx="6" cy="5.5" r="2" />
    <path d="M2.6 12.4c.4-2.2 1.8-3.4 3.4-3.4s3 1.2 3.4 3.4" />
    <circle cx="11" cy="6" r="1.6" />
    <path d="M10.4 9.2c1.3.2 2.4 1.2 2.8 3.2" />
  </Svg>
);

export const ShieldIcon = (props) => (
  <Svg {...props}>
    <path d="M8 2.4l5.2 2v4.2c0 3.2-2.2 5.2-5.2 6.2-3-1-5.2-3-5.2-6.2V4.4L8 2.4z" />
  </Svg>
);

export const GridIcon = (props) => (
  <Svg {...props}>
    <rect x="2.4" y="2.4" width="4.6" height="4.6" />
    <rect x="9" y="2.4" width="4.6" height="4.6" />
    <rect x="2.4" y="9" width="4.6" height="4.6" />
    <rect x="9" y="9" width="4.6" height="4.6" />
  </Svg>
);

export const ListIcon = (props) => (
  <Svg {...props}>
    <path d="M3 4h10M3 8h10M3 12h10" />
  </Svg>
);

export const ScanIcon = (props) => (
  <Svg {...props}>
    <path d="M3 5.2V3h2.2M10.8 3H13v2.2M13 10.8V13h-2.2M5.2 13H3v-2.2" />
    <path d="M5.2 6.4h5.6M5.2 8h3.8M5.2 9.6h4.6" />
  </Svg>
);

export const CheckIcon = (props) => (
  <Svg {...props}>
    <path d="M3 8.2l3.2 3.2L13 4.6" />
  </Svg>
);

export const WarnIcon = (props) => (
  <Svg {...props}>
    <path d="M8 3.2L14.4 14H1.6L8 3.2z" />
    <path d="M8 7v3.2M8 12.2v.2" />
  </Svg>
);

export const DuckMark = ({ size = 22 }) => (
  <svg width={size} height={size} viewBox="0 0 22 22" aria-hidden="true">
    <circle cx="9" cy="12.5" r="6" fill="currentColor" />
    <path d="M14.2 10.2L20 12.5l-5.8 2.3z" fill="currentColor" />
    <circle cx="7.4" cy="11" r="1.1" fill="var(--bg-primary)" />
  </svg>
);
