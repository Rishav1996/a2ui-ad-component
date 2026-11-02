import { LitElement, html, css, PropertyValues } from 'lit';
import { customElement, property } from 'lit/decorators.js';

export interface A2UIAction {
  name: string;
  context?: Record<string, unknown>;
}

export interface DynamicValue<T> {
  literalString?: T;
  literalBoolean?: boolean;
  path?: string;
}

export type DynamicString = string | DynamicValue<string>;

function resolveString(val?: DynamicString, fallback: string = ''): string {
  if (!val) return fallback;
  if (typeof val === 'string') return val;
  if (typeof val === 'object' && 'literalString' in val && typeof val.literalString === 'string') {
    return val.literalString;
  }
  return fallback;
}

/**
 * A2UI v0.9 Reference Lit Web Component: AdBanner
 *
 * Implements a compliant sponsored banner component with locked disclosure badge,
 * sanitized HTTPS image rendering, and deterministic A2UI Action dispatch.
 */
@customElement('a2ui-ad-banner')
export class A2uiAdBanner extends LitElement {
  static override styles = css`
    :host {
      display: block;
      margin: 1rem 0;
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
    }

    .ad-card {
      position: relative;
      border: 1px solid #e2e8f0;
      border-radius: 12px;
      padding: 16px 20px;
      background: linear-gradient(135deg, #f8fafc 0%, #ffffff 100%);
      box-shadow: 0 2px 6px rgba(0, 0, 0, 0.04);
      transition: all 0.2s ease-in-out;
      display: flex;
      flex-direction: column;
      gap: 12px;
      overflow: hidden;
    }

    .ad-card:hover {
      border-color: #cbd5e1;
      box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
    }

    .ad-header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 8px;
    }

    .sponsor-wrapper {
      display: flex;
      align-items: center;
      gap: 8px;
    }

    .sponsor-name {
      font-size: 0.85rem;
      font-weight: 600;
      color: #475569;
      text-transform: uppercase;
      letter-spacing: 0.05em;
    }

    .disclosure-badge {
      display: inline-flex;
      align-items: center;
      padding: 2px 8px;
      border-radius: 9999px;
      font-size: 0.72rem;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.06em;
      background-color: #f1f5f9;
      color: #64748b;
      border: 1px solid #e2e8f0;
      user-select: none;
    }

    .ad-content-layout {
      display: flex;
      gap: 16px;
      align-items: center;
    }

    .ad-text-block {
      flex: 1;
      display: flex;
      flex-direction: column;
      gap: 6px;
    }

    .ad-headline {
      font-size: 1.15rem;
      font-weight: 700;
      color: #0f172a;
      line-height: 1.35;
      margin: 0;
    }

    .ad-body {
      font-size: 0.92rem;
      color: #334155;
      line-height: 1.5;
      margin: 0;
    }

    .ad-media {
      width: 80px;
      height: 80px;
      object-fit: cover;
      border-radius: 8px;
      border: 1px solid #e2e8f0;
      flex-shrink: 0;
    }

    .ad-footer {
      display: flex;
      justify-content: flex-end;
      align-items: center;
      margin-top: 4px;
    }

    .ad-cta-button {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      padding: 8px 18px;
      background-color: #2563eb;
      color: #ffffff;
      font-size: 0.875rem;
      font-weight: 600;
      border: none;
      border-radius: 8px;
      cursor: pointer;
      transition: background-color 0.15s ease-in-out;
      outline: none;
    }

    .ad-cta-button:hover,
    .ad-cta-button:focus-visible {
      background-color: #1d4ed8;
      box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.3);
    }
  `;

  @property({ type: Object })
  sponsorName: DynamicString = 'Sponsor';

  @property({ type: Object })
  headline: DynamicString = '';

  @property({ type: Object })
  bodyText: DynamicString = '';

  @property({ type: Object })
  ctaLabel: DynamicString = 'Learn More';

  /**
   * Locked disclosure text. Defaults strictly to 'Sponsored'.
   * Cannot be suppressed to prevent deceptive advertising patterns.
   */
  @property({ type: Object })
  disclosureText: DynamicString = 'Sponsored';

  @property({ type: Object })
  mediaUrl?: DynamicString;

  @property({ type: Object })
  onClickAction?: A2UIAction;

  @property({ type: String })
  badgeColor?: string;

  override willUpdate(changedProperties: PropertyValues<this>) {
    // Enforce disclosure text guardrail
    if (changedProperties.has('disclosureText')) {
      const resolved = resolveString(this.disclosureText, '').trim();
      if (!resolved) {
        this.disclosureText = 'Sponsored';
      }
    }
  }

  private handleActionDispatch(e: Event) {
    e.stopPropagation();
    if (!this.onClickAction) {
      return;
    }

    // Dispatch native A2UI action event bubbling up to surface host
    this.dispatchEvent(
      new CustomEvent('a2ui-action', {
        bubbles: true,
        composed: true,
        detail: {
          action: this.onClickAction,
          componentId: this.id || 'ad_banner',
          timestamp: Date.now(),
        },
      })
    );
  }

  override render() {
    const sponsor = resolveString(this.sponsorName, 'Partner');
    const head = resolveString(this.headline, '');
    const body = resolveString(this.bodyText, '');
    const cta = resolveString(this.ctaLabel, 'Learn More');
    const disclosure = resolveString(this.disclosureText, 'Sponsored');
    const media = this.mediaUrl ? resolveString(this.mediaUrl, '') : undefined;

    // Security check: Only render HTTPS media URLs
    const safeMediaUrl = media && media.startsWith('https://') ? media : null;

    return html`
      <div class="ad-card" role="region" aria-label="Sponsored Content from ${sponsor}">
        <div class="ad-header">
          <div class="sponsor-wrapper">
            <span class="sponsor-name">${sponsor}</span>
          </div>
          <span
            class="disclosure-badge"
            style="${this.badgeColor ? `background-color: ${this.badgeColor}; color: #fff;` : ''}"
            aria-label="Advertising disclosure"
          >
            ${disclosure}
          </span>
        </div>

        <div class="ad-content-layout">
          <div class="ad-text-block">
            <h3 class="ad-headline">${head}</h3>
            ${body ? html`<p class="ad-body">${body}</p>` : ''}
          </div>
          ${safeMediaUrl
            ? html`<img class="ad-media" src="${safeMediaUrl}" alt="${sponsor} banner" loading="lazy" />`
            : ''}
        </div>

        <div class="ad-footer">
          <button
            type="button"
            class="ad-cta-button"
            @click="${this.handleActionDispatch}"
            aria-label="${cta}: ${head}"
          >
            ${cta}
          </button>
        </div>
      </div>
    `;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    'a2ui-ad-banner': A2uiAdBanner;
  }
}

