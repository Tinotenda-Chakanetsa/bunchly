import {
  createContext,
  useContext,
  useMemo,
  useState,
  type ButtonHTMLAttributes,
  type CSSProperties,
  type HTMLAttributes,
  type ReactNode,
} from "react";
import clsx from "clsx";

import { I, type IconName } from "./icons";
import { avFrom, initials } from "@/lib/format";

/* ============================================
 * Button
 * ============================================ */
type ButtonVariant = "primary" | "ghost" | "outline" | "yellow" | "ink" | "danger";
type ButtonSize = "sm" | "md" | "lg" | "icon";

export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
  size?: ButtonSize;
  leftIcon?: ReactNode;
  rightIcon?: ReactNode;
}

export function Button({
  variant = "primary",
  size = "md",
  className,
  leftIcon,
  rightIcon,
  children,
  ...rest
}: ButtonProps) {
  return (
    <button
      className={clsx(
        "btn",
        `btn-${variant}`,
        size === "sm" && "btn-sm",
        size === "lg" && "btn-lg",
        size === "icon" && "btn-icon",
        className,
      )}
      {...rest}
    >
      {leftIcon}
      {children}
      {rightIcon}
    </button>
  );
}

/* ============================================
 * Card
 * ============================================ */
type CardTone = "ink" | "yellow" | "blue" | "sky";

export interface CardProps extends HTMLAttributes<HTMLDivElement> {
  tone?: CardTone;
  padded?: boolean;
  flat?: boolean;
}

export function Card({
  tone,
  padded,
  flat,
  className,
  children,
  ...rest
}: CardProps) {
  return (
    <div
      className={clsx(
        "card",
        tone && `tinted-${tone}`,
        padded && "padded",
        flat && "flat",
        className,
      )}
      {...rest}
    >
      {children}
    </div>
  );
}

export function CardHead({
  title,
  sub,
  action,
  icon,
}: {
  title: ReactNode;
  sub?: ReactNode;
  action?: ReactNode;
  icon?: ReactNode;
}) {
  return (
    <div className="card-head">
      <div className="center">
        {icon}
        <div>
          <h3>{title}</h3>
          {sub && <div className="sub">{sub}</div>}
        </div>
      </div>
      {action}
    </div>
  );
}

export function CardBody({
  children,
  className,
  ...rest
}: HTMLAttributes<HTMLDivElement>) {
  return (
    <div className={clsx("card-body", className)} {...rest}>
      {children}
    </div>
  );
}

export function CardFoot({
  children,
  className,
  ...rest
}: HTMLAttributes<HTMLDivElement>) {
  return (
    <div className={clsx("card-foot", className)} {...rest}>
      {children}
    </div>
  );
}

/* ============================================
 * Badge / StatusBadge
 * ============================================ */
export type BadgeTone =
  | "default"
  | "blue"
  | "yellow"
  | "green"
  | "red"
  | "ink"
  | "outline"
  | "soft";

export function Badge({
  tone = "default",
  dot,
  className,
  children,
  ...rest
}: HTMLAttributes<HTMLSpanElement> & {
  tone?: BadgeTone;
  dot?: boolean;
}) {
  return (
    <span
      className={clsx("badge", tone !== "default" && `badge-${tone}`, className)}
      {...rest}
    >
      {dot && <span className="dot" />}
      {children}
    </span>
  );
}

const STATUS_TONE_MAP: Record<string, { tone: BadgeTone; dot: boolean }> = {
  Active: { tone: "green", dot: true },
  "On Leave": { tone: "yellow", dot: true },
  Inactive: { tone: "default", dot: true },
  Terminated: { tone: "red", dot: true },
  Pending: { tone: "yellow", dot: true },
  "Pending Approval": { tone: "yellow", dot: true },
  "Pending HR": { tone: "yellow", dot: true },
  "Pending Review": { tone: "yellow", dot: true },
  "Pending Payment": { tone: "blue", dot: true },
  Approved: { tone: "green", dot: true },
  Rejected: { tone: "red", dot: true },
  Paid: { tone: "green", dot: true },
  Processing: { tone: "blue", dot: true },
  Open: { tone: "blue", dot: true },
  Draft: { tone: "default", dot: true },
  Offer: { tone: "yellow", dot: true },
  Hired: { tone: "green", dot: true },
  Complete: { tone: "green", dot: true },
  "At Risk": { tone: "red", dot: true },
  "Manager Review": { tone: "blue", dot: true },
  "Self-Assessment": { tone: "yellow", dot: true },
  Calibration: { tone: "blue", dot: true },
  Verified: { tone: "green", dot: true },
  Working: { tone: "green", dot: true },
  Sick: { tone: "red", dot: true },
  "Annual leave": { tone: "yellow", dot: true },
  "In Progress": { tone: "blue", dot: true },
  "Awaiting Employee": { tone: "yellow", dot: true },
  Resolved: { tone: "green", dot: true },
  Screening: { tone: "blue", dot: true },
};

export function StatusBadge({ status }: { status: string }) {
  const { tone, dot } = STATUS_TONE_MAP[status] || { tone: "default", dot: true };
  return (
    <Badge tone={tone} dot={dot}>
      {status}
    </Badge>
  );
}

/* ============================================
 * Avatar
 * ============================================ */
export function Avatar({
  name,
  size = "md",
  av,
  className,
}: {
  name: string;
  size?: "sm" | "md" | "lg" | "xl";
  av?: string;
  className?: string;
}) {
  const cls =
    size === "sm" ? "avatar-sm" : size === "lg" ? "avatar-lg" : size === "xl" ? "avatar-xl" : "";
  const palette = av || avFrom(name);
  return (
    <span className={clsx("avatar", palette, cls, className)} title={name}>
      {initials(name) || "?"}
    </span>
  );
}

export function PersonCell({
  name,
  av,
  sub,
  size,
}: {
  name: string;
  av?: string;
  sub?: ReactNode;
  size?: "sm" | "md" | "lg";
}) {
  return (
    <div className="cell-person">
      <Avatar name={name} av={av} size={size} />
      <div className="meta">
        <div className="name">{name}</div>
        {sub && <div className="sub">{sub}</div>}
      </div>
    </div>
  );
}

/* ============================================
 * Page Header / Section
 * ============================================ */
export function PageHeader({
  eyebrow,
  title,
  lede,
  actions,
  children,
}: {
  eyebrow?: ReactNode;
  title: ReactNode;
  lede?: ReactNode;
  actions?: ReactNode;
  children?: ReactNode;
}) {
  return (
    <>
      <div className="page-head">
        <div style={{ flex: 1, minWidth: 0 }}>
          {eyebrow && <span className="eyebrow">{eyebrow}</span>}
          <h1>{title}</h1>
          {lede && <p className="lede">{lede}</p>}
        </div>
        {actions && <div className="actions">{actions}</div>}
      </div>
      {children}
    </>
  );
}

export function Section({
  title,
  sub,
  action,
  children,
  className,
}: {
  title: ReactNode;
  sub?: ReactNode;
  action?: ReactNode;
  children: ReactNode;
  className?: string;
}) {
  return (
    <section style={{ marginTop: 20 }} className={className}>
      <div className="spread" style={{ marginBottom: 10 }}>
        <div>
          <h2
            style={{
              margin: 0,
              fontSize: 15,
              fontWeight: 600,
              color: "var(--ink-3)",
              letterSpacing: "-0.005em",
            }}
          >
            {title}
          </h2>
          {sub && <div style={{ color: "var(--text-3)", fontSize: 12, marginTop: 1 }}>{sub}</div>}
        </div>
        {action}
      </div>
      {children}
    </section>
  );
}

/* ============================================
 * Stat / KpiStrip / KpiCell
 * ============================================ */
export function Stat({
  label,
  value,
  delta,
  deltaTone = "up",
  sub,
}: {
  label: ReactNode;
  value: ReactNode;
  delta?: ReactNode;
  deltaTone?: "up" | "down" | "flat";
  sub?: ReactNode;
}) {
  return (
    <div className="stat">
      <div className="label">{label}</div>
      <div className="value num">{value}</div>
      <div className="row-bottom">
        {delta && (
          <span className={`delta-pill ${deltaTone}`}>
            <I.arrow
              size={10}
              style={{ transform: deltaTone === "up" ? "rotate(-45deg)" : "rotate(45deg)" }}
            />{" "}
            {delta}
          </span>
        )}
        {sub && !delta && <span className="sub">{sub}</span>}
      </div>
    </div>
  );
}

export function KpiStrip({
  cols,
  children,
  className,
  style,
}: {
  cols?: number;
  children: ReactNode;
  className?: string;
  style?: CSSProperties;
}) {
  const colsCls = cols === 3 ? "cols-3" : "";
  const mergedStyle: CSSProperties =
    cols && cols !== 3 && cols !== 4
      ? { gridTemplateColumns: `repeat(${cols}, 1fr)`, ...style }
      : style ?? {};
  return (
    <div className={clsx("kpi-strip", colsCls, className)} style={mergedStyle}>
      {children}
    </div>
  );
}

export function KpiCell({
  icon,
  label,
  period,
  value,
  valueSuffix,
  delta,
  deltaTone = "up",
  comp,
  meter,
  sub,
}: {
  icon?: ReactNode;
  label: ReactNode;
  period?: ReactNode;
  value: ReactNode;
  valueSuffix?: ReactNode;
  delta?: ReactNode;
  deltaTone?: "up" | "down" | "flat";
  comp?: ReactNode;
  meter?: ReactNode;
  sub?: ReactNode;
}) {
  return (
    <div className="kpi">
      <div className="spread">
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: 6,
            color: "var(--text-3)",
            fontSize: 11.5,
          }}
        >
          {icon}
          <span style={{ fontWeight: 500 }}>{label}</span>
        </div>
        {period && <span style={{ fontSize: 11, color: "var(--text-4)" }}>{period}</span>}
      </div>
      <div style={{ display: "flex", alignItems: "baseline", gap: 8, marginTop: 4 }}>
        <span
          style={{
            fontSize: 26,
            fontWeight: 600,
            color: "var(--ink-3)",
            letterSpacing: "-0.015em",
            fontVariantNumeric: "tabular-nums",
            lineHeight: 1.1,
          }}
        >
          {value}
        </span>
        {valueSuffix && (
          <span style={{ color: "var(--text-3)", fontSize: 12 }}>{valueSuffix}</span>
        )}
        {delta && (
          <span className={`delta-pill ${deltaTone}`}>
            {delta}{" "}
            <I.arrow
              size={10}
              style={{
                transform:
                  deltaTone === "up"
                    ? "rotate(-45deg)"
                    : deltaTone === "down"
                      ? "rotate(45deg)"
                      : "rotate(0deg)",
              }}
            />
          </span>
        )}
      </div>
      {meter && <div style={{ marginTop: 8 }}>{meter}</div>}
      {(comp || sub) && (
        <div style={{ fontSize: 11.5, color: "var(--text-3)", marginTop: 4 }}>{comp || sub}</div>
      )}
    </div>
  );
}

/* ============================================
 * Sparkline / Meter
 * ============================================ */
export function Sparkline({
  values,
  color = "var(--action)",
  height = 32,
  width = 100,
  fill = true,
}: {
  values: number[];
  color?: string;
  height?: number;
  width?: number;
  fill?: boolean;
}) {
  if (!values || values.length === 0) return null;
  const max = Math.max(...values);
  const min = Math.min(...values);
  const range = max - min || 1;
  const step = width / (values.length - 1);
  const pts = values.map(
    (v, i) => [i * step, height - ((v - min) / range) * height * 0.85 - 2] as const,
  );
  const path = pts.map((p, i) => (i === 0 ? `M ${p[0]} ${p[1]}` : `L ${p[0]} ${p[1]}`)).join(" ");
  const area = `${path} L ${width} ${height} L 0 ${height} Z`;
  const id = `g-${color.replace(/[^a-z]/gi, "")}`;
  return (
    <svg width={width} height={height} style={{ display: "block" }}>
      {fill && (
        <>
          <defs>
            <linearGradient id={id} x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor={color} stopOpacity="0.25" />
              <stop offset="100%" stopColor={color} stopOpacity="0" />
            </linearGradient>
          </defs>
          <path d={area} fill={`url(#${id})`} />
        </>
      )}
      <path
        d={path}
        stroke={color}
        strokeWidth="2"
        fill="none"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <circle cx={pts[pts.length - 1][0]} cy={pts[pts.length - 1][1]} r="2.5" fill={color} />
    </svg>
  );
}

export function Meter({
  value,
  max = 100,
  color,
  thin,
}: {
  value: number;
  max?: number;
  color?: string;
  thin?: boolean;
}) {
  const pct = Math.max(0, Math.min(100, (value / max) * 100));
  return (
    <div className={clsx("meter", thin && "thin")}>
      <span style={{ width: `${pct}%`, background: color }} />
    </div>
  );
}

/* ============================================
 * Modal / Drawer
 * ============================================ */
export function Modal({
  open,
  onClose,
  title,
  sub,
  children,
  footer,
  width,
}: {
  open: boolean;
  onClose: () => void;
  title?: ReactNode;
  sub?: ReactNode;
  children: ReactNode;
  footer?: ReactNode;
  width?: number;
}) {
  if (!open) return null;
  return (
    <div className="modal-back" onClick={onClose}>
      <div
        className="modal pop"
        onClick={(e) => e.stopPropagation()}
        style={{ maxWidth: width }}
      >
        {(title || sub) && (
          <div className="modal-head">
            <div className="spread" style={{ alignItems: "flex-start" }}>
              <div>
                {title && <h3>{title}</h3>}
                {sub && <p>{sub}</p>}
              </div>
              <Button variant="ghost" size="icon" onClick={onClose}>
                <I.x size={16} />
              </Button>
            </div>
          </div>
        )}
        <div className="modal-body">{children}</div>
        {footer && <div className="modal-foot">{footer}</div>}
      </div>
    </div>
  );
}

export function Drawer({
  open,
  onClose,
  title,
  sub,
  children,
  footer,
  width = 520,
}: {
  open: boolean;
  onClose: () => void;
  title: ReactNode;
  sub?: ReactNode;
  children: ReactNode;
  footer?: ReactNode;
  width?: number;
}) {
  if (!open) return null;
  return (
    <div className="modal-back" onClick={onClose} style={{ justifyContent: "flex-end", padding: 0 }}>
      <div
        className="pop"
        onClick={(e) => e.stopPropagation()}
        style={{
          background: "var(--card)",
          width,
          maxWidth: "100vw",
          height: "100vh",
          display: "flex",
          flexDirection: "column",
          boxShadow: "var(--shadow-pop)",
        }}
      >
        <div className="modal-head">
          <div className="spread" style={{ alignItems: "flex-start" }}>
            <div>
              <h3>{title}</h3>
              {sub && <p>{sub}</p>}
            </div>
            <Button variant="ghost" size="icon" onClick={onClose}>
              <I.x size={16} />
            </Button>
          </div>
        </div>
        <div className="modal-body" style={{ flex: 1, overflow: "auto" }}>
          {children}
        </div>
        {footer && <div className="modal-foot">{footer}</div>}
      </div>
    </div>
  );
}

/* ============================================
 * Tabs
 * ============================================ */
export interface TabItem {
  value: string;
  label: ReactNode;
  count?: number;
}

export function Tabs({
  items,
  value,
  onChange,
  pill,
}: {
  items: Array<TabItem | string>;
  value: string;
  onChange: (v: string) => void;
  pill?: boolean;
}) {
  return (
    <div className={clsx("tabs", pill && "pill")}>
      {items.map((t) => {
        const item: TabItem = typeof t === "string" ? { value: t, label: t } : t;
        return (
          <button
            key={item.value}
            className={clsx(value === item.value && "active")}
            onClick={() => onChange(item.value)}
          >
            {item.label}
            {item.count != null && (
              <span
                style={{
                  marginLeft: 6,
                  opacity: 0.6,
                  fontVariantNumeric: "tabular-nums",
                }}
              >
                {item.count}
              </span>
            )}
          </button>
        );
      })}
    </div>
  );
}

/* ============================================
 * Empty state
 * ============================================ */
export function Empty({
  icon,
  title,
  lede,
  action,
}: {
  icon?: IconName | ReactNode;
  title: ReactNode;
  lede?: ReactNode;
  action?: ReactNode;
}) {
  let iconNode: ReactNode = null;
  if (typeof icon === "string") {
    /* Unknown icon names would otherwise blow up rendering with React
       error #130 ("got: undefined"). Fall back to a generic info icon
       and warn so the mismatch is visible in dev. */
    const C = (I as Record<string, (p: { size?: number }) => ReactNode>)[icon] ?? I.info;
    if (!I[icon as IconName] && typeof console !== "undefined") {
      console.warn(`<Empty icon="${icon}" />: unknown icon, using fallback`);
    }
    iconNode = <C size={20} />;
  } else {
    iconNode = icon;
  }
  return (
    <div className="empty">
      <div
        style={{
          width: 56,
          height: 56,
          borderRadius: 16,
          background: "var(--mist)",
          display: "inline-grid",
          placeItems: "center",
          color: "var(--text-3)",
        }}
      >
        {iconNode}
      </div>
      <div className="title">{title}</div>
      {lede && <div className="lede">{lede}</div>}
      {action}
    </div>
  );
}

export function EmptyState(props: Parameters<typeof Empty>[0]) {
  return <Empty {...props} />;
}

/* ============================================
 * Approval timeline
 * ============================================ */
export function ApprovalTimeline({
  nodes,
}: {
  nodes: Array<{ who: ReactNode; when: ReactNode; what?: ReactNode; state?: "done" | "active" | "rejected" | "" }>;
}) {
  return (
    <div className="timeline">
      {nodes.map((n, i) => (
        <div key={i} className={clsx("timeline-node", n.state)}>
          <div className="who">{n.who}</div>
          <div className="when">{n.when}</div>
          {n.what && <div className="what">{n.what}</div>}
        </div>
      ))}
    </div>
  );
}

/* ============================================
 * Donut / Bar / Column charts
 * ============================================ */
export function Donut({
  segments,
  size = 120,
  thickness = 14,
  label,
  sub,
}: {
  segments: Array<{ value: number; color: string }>;
  size?: number;
  thickness?: number;
  label?: ReactNode;
  sub?: ReactNode;
}) {
  const total = segments.reduce((a, s) => a + s.value, 0);
  const radius = size / 2 - thickness / 2;
  const circ = 2 * Math.PI * radius;
  let offset = 0;
  return (
    <div style={{ position: "relative", width: size, height: size }}>
      <svg width={size} height={size} style={{ transform: "rotate(-90deg)" }}>
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          stroke="var(--hairline-2)"
          strokeWidth={thickness}
          fill="none"
        />
        {segments.map((s, i) => {
          const len = (s.value / total) * circ;
          const el = (
            <circle
              key={i}
              cx={size / 2}
              cy={size / 2}
              r={radius}
              stroke={s.color}
              strokeWidth={thickness}
              fill="none"
              strokeDasharray={`${len} ${circ}`}
              strokeDashoffset={-offset}
              strokeLinecap="butt"
            />
          );
          offset += len;
          return el;
        })}
      </svg>
      {(label || sub) && (
        <div
          style={{
            position: "absolute",
            inset: 0,
            display: "grid",
            placeItems: "center",
            textAlign: "center",
          }}
        >
          <div>
            <div
              style={{
                fontSize: 26,
                fontWeight: 600,
                lineHeight: 1,
                color: "var(--ink-3)",
                letterSpacing: "-0.02em",
              }}
            >
              {label}
            </div>
            {sub && (
              <div style={{ fontSize: 11, color: "var(--text-3)", marginTop: 4 }}>{sub}</div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

export function BarChart({
  data,
  color = "var(--action)",
  format = (v: number) => v.toString(),
}: {
  data: Array<{ label: string; value: number; color?: string }>;
  color?: string;
  format?: (v: number) => string | number;
}) {
  const max = Math.max(...data.map((d) => d.value));
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
      {data.map((d, i) => (
        <div
          key={i}
          style={{
            display: "grid",
            gridTemplateColumns: "100px 1fr 70px",
            gap: 10,
            alignItems: "center",
          }}
        >
          <div
            style={{
              fontSize: 12.5,
              color: "var(--text-2)",
              whiteSpace: "nowrap",
              overflow: "hidden",
              textOverflow: "ellipsis",
            }}
          >
            {d.label}
          </div>
          <div
            style={{
              background: "var(--hairline-2)",
              height: 22,
              borderRadius: 6,
              overflow: "hidden",
              position: "relative",
            }}
          >
            <div
              style={{
                width: `${(d.value / max) * 100}%`,
                height: "100%",
                background: d.color || color,
                borderRadius: 6,
                transition: "width 0.5s ease",
              }}
            />
          </div>
          <div
            style={{
              fontSize: 12.5,
              fontVariantNumeric: "tabular-nums",
              color: "var(--text)",
              textAlign: "right",
              fontWeight: 600,
            }}
          >
            {format(d.value)}
          </div>
        </div>
      ))}
    </div>
  );
}

export function ColumnChart({
  data,
  color = "var(--action)",
  height = 140,
  format = (v: number) => v.toString(),
}: {
  data: Array<{ label: string; value: number; color?: string }>;
  color?: string;
  height?: number;
  format?: (v: number) => string | number;
}) {
  const max = Math.max(...data.map((d) => d.value));
  return (
    <div style={{ display: "flex", alignItems: "flex-end", gap: 8, height }}>
      {data.map((d, i) => (
        <div
          key={i}
          style={{
            flex: 1,
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            gap: 6,
          }}
        >
          <div style={{ fontSize: 10.5, color: "var(--text-3)", fontVariantNumeric: "tabular-nums" }}>
            {format(d.value)}
          </div>
          <div
            style={{
              width: "100%",
              height: `${(d.value / max) * (height - 36)}px`,
              background: d.color || color,
              borderRadius: "6px 6px 2px 2px",
              transition: "height 0.5s ease",
              minHeight: 4,
            }}
          />
          <div style={{ fontSize: 11, color: "var(--text-3)" }}>{d.label}</div>
        </div>
      ))}
    </div>
  );
}

/* ============================================
 * Stars
 * ============================================ */
export function Stars({ value, max = 5 }: { value: number | null; max?: number }) {
  if (value == null)
    return <span style={{ color: "var(--text-4)", fontSize: 12 }}>—</span>;
  return (
    <span style={{ display: "inline-flex", gap: 1 }}>
      {Array.from({ length: max }).map((_, i) => (
        <span
          key={i}
          style={{
            color: i < Math.round(value) ? "var(--yellow-deep)" : "var(--hairline)",
          }}
        >
          ★
        </span>
      ))}
    </span>
  );
}

/* ============================================
 * FileRow
 * ============================================ */
export function FileRow({
  name,
  sub,
  size,
  action,
  icon,
}: {
  name: ReactNode;
  sub?: ReactNode;
  size?: ReactNode;
  action?: ReactNode;
  icon?: ReactNode;
}) {
  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        gap: 12,
        padding: "10px 12px",
        border: "1px solid var(--hairline-2)",
        borderRadius: 10,
        background: "var(--card)",
      }}
    >
      <div
        style={{
          width: 34,
          height: 38,
          background: "var(--info-soft)",
          color: "var(--action)",
          display: "grid",
          placeItems: "center",
          borderRadius: 6,
        }}
      >
        {icon || <I.document size={16} />}
      </div>
      <div style={{ flex: 1, minWidth: 0 }}>
        <div
          style={{
            fontWeight: 500,
            fontSize: 13.5,
            color: "var(--text)",
            whiteSpace: "nowrap",
            overflow: "hidden",
            textOverflow: "ellipsis",
          }}
        >
          {name}
        </div>
        {sub && <div style={{ fontSize: 12, color: "var(--text-3)" }}>{sub}</div>}
      </div>
      {size && (
        <span
          style={{ fontSize: 12, color: "var(--text-3)", fontVariantNumeric: "tabular-nums" }}
        >
          {size}
        </span>
      )}
      {action}
    </div>
  );
}

/* ============================================
 * Pagination (10 rows per page across the app)
 * ============================================ */
export const DEFAULT_PAGE_SIZE = 10;

export function usePaginated<T>(items: T[], pageSize: number = DEFAULT_PAGE_SIZE) {
  const [page, setPage] = useState(0);
  const total = items.length;
  const pages = Math.max(1, Math.ceil(total / pageSize));
  const safePage = Math.min(page, pages - 1);
  const start = safePage * pageSize;
  const slice = items.slice(start, start + pageSize);
  // Reset to first page whenever the underlying list shrinks below the
  // current page's start index (e.g. user filtered the list).
  if (safePage !== page && page > 0) {
    queueMicrotask(() => setPage(safePage));
  }
  return {
    page: safePage,
    pages,
    pageSize,
    total,
    slice,
    setPage,
    next: () => setPage((p) => Math.min(pages - 1, p + 1)),
    prev: () => setPage((p) => Math.max(0, p - 1)),
    reset: () => setPage(0),
  };
}

export function Pagination({
  page,
  pages,
  pageSize,
  total,
  setPage,
  className,
}: {
  page: number;
  pages: number;
  pageSize: number;
  total: number;
  setPage: (p: number) => void;
  className?: string;
}) {
  if (total === 0) return null;
  const start = page * pageSize + 1;
  const end = Math.min(total, (page + 1) * pageSize);
  return (
    <div
      className={clsx(className)}
      style={{
        display: "flex",
        justifyContent: "space-between",
        alignItems: "center",
        gap: 12,
        padding: "12px 16px",
        borderTop: "1px solid var(--hairline-2)",
        fontSize: 12.5,
        color: "var(--text-3)",
      }}
    >
      <span>
        Showing <strong style={{ color: "var(--ink-3)" }}>{start}</strong>–
        <strong style={{ color: "var(--ink-3)" }}>{end}</strong> of{" "}
        <strong style={{ color: "var(--ink-3)" }}>{total}</strong>
      </span>
      <div style={{ display: "flex", gap: 6, alignItems: "center" }}>
        <Button
          variant="outline"
          size="sm"
          onClick={() => setPage(Math.max(0, page - 1))}
          disabled={page === 0}
        >
          <I.chevron size={12} style={{ transform: "rotate(180deg)" }} /> Previous
        </Button>
        <span style={{ fontVariantNumeric: "tabular-nums", padding: "0 8px" }}>
          Page {page + 1} of {pages}
        </span>
        <Button
          variant="outline"
          size="sm"
          onClick={() => setPage(Math.min(pages - 1, page + 1))}
          disabled={page >= pages - 1}
        >
          Next <I.chevron size={12} />
        </Button>
      </div>
    </div>
  );
}

/* ============================================
 * Skeleton
 * ============================================ */
export function Skeleton({
  height = 16,
  width = "100%",
}: {
  height?: number;
  width?: number | string;
}) {
  return (
    <div
      style={{
        background: "var(--hairline-2)",
        borderRadius: 6,
        height,
        width,
        animation: "pulse 1.2s ease-in-out infinite",
      }}
    />
  );
}

/* ============================================
 * Toast hook (global provider)
 * ============================================ */
interface Toast {
  id: string;
  msg: string;
  tone: "default" | "success" | "error";
}

interface ToastApi {
  push: (msg: string, tone?: Toast["tone"]) => void;
}

const ToastContext = createContext<ToastApi | null>(null);

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);

  const api = useMemo<ToastApi>(
    () => ({
      push: (msg, tone = "default") => {
        const id = Math.random().toString(36).slice(2);
        setToasts((t) => [...t, { id, msg, tone }]);
        setTimeout(() => setToasts((t) => t.filter((x) => x.id !== id)), 3200);
      },
    }),
    [],
  );

  return (
    <ToastContext.Provider value={api}>
      {children}
      <div
        style={{
          position: "fixed",
          bottom: 24,
          right: 24,
          display: "flex",
          flexDirection: "column",
          gap: 8,
          zIndex: 200,
        }}
      >
        {toasts.map((t) => (
          <div
            key={t.id}
            className={`pop${t.tone === "success" ? " toast-success" : ""}`}
            style={{
              background: t.tone === "success" ? undefined : "var(--card)",
              color: t.tone === "success" ? "#fff" : "var(--text)",
              border: "1px solid var(--hairline)",
              borderRadius: 12,
              padding: "10px 16px",
              boxShadow: "var(--shadow-pop)",
              display: "flex",
              alignItems: "center",
              gap: 10,
              minWidth: 260,
              fontSize: 13.5,
              fontWeight: 500,
            }}
          >
            {t.tone === "success" && <I.check size={16} />}
            {t.tone === "error" && <I.warn size={16} />}
            {t.msg}
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
}

export function useToast(): ToastApi {
  const ctx = useContext(ToastContext);
  if (!ctx) throw new Error("useToast must be used within <ToastProvider>");
  return ctx;
}

/* ============================================
 * NavIcon helper
 * ============================================ */
export function NavIcon({ name, size = 16 }: { name: IconName; size?: number }) {
  const C = I[name] ?? I.info;
  return <C size={size} className="nav-icon" />;
}
