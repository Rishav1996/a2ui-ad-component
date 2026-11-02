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
 * A2UI v0.9 Reference Lit Web Component: SponsoredCard
 *
 * Designed for real-time 3-card search ad grids.
 * Implements locked regulatory disclosures, dynamic offer badges, and bubbling A2UI Action dispatch.
 */
@customElement('a2ui-sponsored-card')
export class A2uiSponsoredCard extends LitElement {
  static override styles = css`
    :host {
      display: flex;
      flex-direction: column;
      flex: 1 1 calc(33.333% - 16px);
      min-width: 260px;
      margin: 8px 0;
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
    }

    .card-container {
      display: flex;
      flex-direction: column;
      justify-content: space-between;
      height: 100%;
      border: 1px solid #e2e8f0;
      border-radius: 12px;
      padding: 16px;
      background: #ffffff;
      box-shadow: 0 1px 4px rgba(0, 0, 0, 0.04);
      transition: all 0.2s ease-in-out;
      overflow: hidden;
      box-sizing: border-box;
    }

    .card-container:hover {
      border-color: #3b82f6;
      box-shadow: 0 4px 12px rgba(59, 130, 246, 0.12);
      transform: translateY(-2px);
    }

    .card-header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      margin-bottom: 10px;
      gap: 6px;
    }

    .sponsor-name {
      font-size: 0.78rem;
      font-weight: 700;
      color: #475569;
      text-transform: uppercase;
      letter-spacing: 0.06em;
    }

    .badges-wrapper {
      display: flex;
      align-items: center;
      gap: 6px;
    }

    .pill-badge {
      display: inline-flex;
      align-items: center;
      padding: 2px 7px;
      border-radius: 9999px;
      font-size: 0.7rem;
      font-weight: 600;
      background-color: #eff6ff;
      color: #2563eb;
      border: 1px solid #dbeafe;
    }

    .disclosure-badge {
      display: inline-flex;
      align-items: center;
      padding: 2px 6px;
      border-radius: 9999px;
      font-size: 0.68rem;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.05em;
      background-color: #f1f5f9;
      color: #64748b;
      border: 1px solid #e2e8f0;
      user-select: none;
    }

    .card-body {
      display: flex;
      flex-direction: column;
      gap: 8px;
      margin-bottom: 16px;
    }

    .card-headline {
      font-size: 0.98rem;
      font-weight: 700;
      color: #0f172a;
      line-height: 1.35;
      margin: 0;
    }

    .card-text {
      font-size: 0.84rem;
      color: #475569;
      line-height: 1.45;
      margin: 0;
    }

    .card-footer {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-top: auto;
      padding-top: 10px;
      border-top: 1px solid #f1f5f9;
    }

    .clearing-price {
      font-size: 0.72rem;
      color: #94a3b8;
    }

    .cta-btn {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      padding: 6px 14px;
      background-color: #2563eb;
      color: #ffffff;
      font-size: 0.82rem;
      font-weight: 600;
      border: none;
      border-radius: 6px;
      cursor: pointer;
      transition: background-color 0.15s ease-in-out;
      outline: none;
    }

    .cta-btn:hover,
    .cta-btn:focus-visible {
      background-color: #1d4ed8;
      box-shadow: 0 0 0 2px rgba(37, 99, 235, 0.25);
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

  @property({ type: Object })
  disclosureText: DynamicString = 'Sponsored';

  @property({ type: Object })
  badgeText?: DynamicString;

  @property({ type: Object })
  mediaUrl?: DynamicString;

  @property({ type: Number })
  clearingPrice?: number;

  @property({ type: Object })
  onClickAction?: A2UIAction;

  override willUpdate(changedProperties: PropertyValues<this>) {
    if (changedProperties.has('disclosureText')) {
      const resolved = resolveString(this.disclosureText, '').trim();
      if (!resolved) {
        this.disclosureText = 'Sponsored';
      }
    }
  }

  private handleActionDispatch(e: Event) {
    e.stopPropagation();
    if (!this.onClickAction) return;

    this.dispatchEvent(
      new CustomEvent('a2ui-action', {
        bubbles: true,
        composed: true,
        detail: {
          action: this.onClickAction,
          componentId: this.id || 'sponsored_card',
          timestamp: Date.now(),
        },
      })
    );
  }

  override render() {
    const sponsor = resolveString(this.sponsorName, 'Partner');
    const headline = resolveString(this.headline, '');
    const body = resolveString(this.bodyText, '');
    const cta = resolveString(this.ctaLabel, 'Learn More');
    const disclosure = resolveString(this.disclosureText, 'Sponsored');
    const badge = this.badgeText ? resolveString(this.badgeText, '') : '';

    return html`
      <div class="card-container" role="region" aria-label="Sponsored Ad: ${sponsor}">
        <div>
          <div class="card-header">
            <span class="sponsor-name">${sponsor}</span>
            <div class="badges-wrapper">
              ${badge ? html`<span class="pill-badge">${badge}</span>` : ''}
              <span class="disclosure-badge" aria-label="Advertising disclosure">${disclosure}</span>
            </div>
          </div>

          <div class="card-body">
            <h4 class="card-headline">${headline}</h4>
            ${body ? html`<p class="card-text">${body}</p>` : ''}
          </div>
        </div>

        <div class="card-footer">
          <span class="clearing-price">
            ${this.clearingPrice ? `CPM ₹${this.clearingPrice.toFixed(0)}` : 'Verified Bid'}
          </span>
          <button
            type="button"
            class="cta-btn"
            @click="${this.handleActionDispatch}"
            aria-label="${cta}: ${headline}"
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
    'a2ui-sponsored-card': A2uiSponsoredCard;
  }
}

