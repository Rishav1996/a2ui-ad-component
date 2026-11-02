import matplotlib.pyplot as plt
import matplotlib.patches as patches

def generate_traditional_search_diagram():
    fig, ax = plt.subplots(figsize=(13, 5), dpi=300)
    ax.set_facecolor('#0b0f19')
    fig.patch.set_facecolor('#0b0f19')

    # Header
    ax.text(0.5, 0.91, 'Traditional Search Engine Paradigm (Web 1.0 & 2.0)', 
            fontsize=15, fontweight='bold', color='#f8fafc', ha='center', transform=ax.transAxes)
    ax.text(0.5, 0.82, 'The "10 Blue Links" Model: Query-Driven Cost-Per-Click (CPC) Revenue Engine', 
            fontsize=10, color='#94a3b8', ha='center', transform=ax.transAxes)

    # Stages
    boxes = [
        {
            'x': 0.04, 'y': 0.32, 'w': 0.19, 'h': 0.40,
            'tag': 'STEP 1', 'tag_col': '#38bdf8',
            'title': 'User Search Query',
            'lines': ['Intent-rich keywords', 'e.g. "best luxury watch"', 'or "cloud database"'],
            'border': '#0284c7'
        },
        {
            'x': 0.28, 'y': 0.32, 'w': 0.22, 'h': 0.40,
            'tag': 'STEP 2', 'tag_col': '#a855f7',
            'title': 'SERP Results Page',
            'lines': ['Top Sponsored Text Ads', '10 Blue Links (Organic)', 'Publisher snippets'],
            'border': '#7c3aed'
        },
        {
            'x': 0.54, 'y': 0.32, 'w': 0.19, 'h': 0.40,
            'tag': 'STEP 3', 'tag_col': '#f59e0b',
            'title': 'User Clicks Out',
            'lines': ['Leaves search engine', 'Visits merchant or publisher', 'High CTR on top ad slots'],
            'border': '#d97706'
        },
        {
            'x': 0.77, 'y': 0.32, 'w': 0.19, 'h': 0.40,
            'tag': 'STEP 4', 'tag_col': '#10b981',
            'title': 'Economic Flywheel',
            'lines': ['$316B+ Global Ad Spend', 'CPC search ad revenues', 'Publisher display traffic'],
            'border': '#059669'
        },
    ]

    for b in boxes:
        # Box background
        rect = patches.FancyBboxPatch((b['x'], b['y']), b['w'], b['h'],
                                      boxstyle='round,pad=0.015,rounding_size=0.03',
                                      facecolor='#111827', edgecolor=b['border'], linewidth=1.8,
                                      transform=ax.transAxes)
        ax.add_patch(rect)
        
        # Tag pill
        ax.text(b['x'] + b['w']/2, b['y'] + b['h'] - 0.05, b['tag'],
                color=b['tag_col'], fontsize=8.5, fontweight='bold', ha='center', transform=ax.transAxes)
        # Title
        ax.text(b['x'] + b['w']/2, b['y'] + b['h'] - 0.13, b['title'],
                color='#ffffff', fontsize=11, fontweight='bold', ha='center', transform=ax.transAxes)
        # Description
        y_text = b['y'] + b['h'] - 0.22
        for line in b['lines']:
            ax.text(b['x'] + b['w']/2, y_text, line,
                    color='#cbd5e1', fontsize=9, ha='center', transform=ax.transAxes)
            y_text -= 0.06

    # Arrows
    arrows = [(0.23, 0.52, 0.28, 0.52), (0.50, 0.52, 0.54, 0.52), (0.73, 0.52, 0.77, 0.52)]
    for x1, y1, x2, y2 in arrows:
        ax.annotate('', xy=(x2, y2), xytext=(x1, y1), xycoords='axes fraction', textcoords='axes fraction',
                    arrowprops=dict(arrowstyle='->,head_width=0.4,head_length=0.5', color='#38bdf8', lw=2.2))

    # Bottom Callout: The Failure Mode in Generative AI
    warn_rect = patches.FancyBboxPatch((0.04, 0.06), 0.92, 0.17,
                                       boxstyle='round,pad=0.012,rounding_size=0.02',
                                       facecolor='#1e1b4b', edgecolor='#6366f1', linewidth=1.2,
                                       transform=ax.transAxes)
    ax.add_patch(warn_rect)
    ax.text(0.5, 0.16, '⚡ The Generative AI Bottleneck (Zero-Click Crisis)',
            color='#a5b4fc', fontsize=10, fontweight='bold', ha='center', transform=ax.transAxes)
    ax.text(0.5, 0.095, 'In conversational AI, users get instant direct synthesis without visiting SERP pages. Ad views and CTR collapse, leaving AI chats with high compute costs but zero ad monetization.',
            color='#e0e7ff', fontsize=8.8, ha='center', transform=ax.transAxes)

    ax.axis('off')
    plt.subplots_adjust(left=0, right=1, top=1, bottom=0)
    plt.savefig('docs/images/paradigm_traditional_search.png', dpi=300, facecolor=fig.get_facecolor(), edgecolor='none')
    plt.close()
    print("Created docs/images/paradigm_traditional_search.png")


def generate_conversational_a2ui_diagram():
    fig, ax = plt.subplots(figsize=(14, 8), dpi=300)
    ax.set_facecolor('#0b0f19')
    fig.patch.set_facecolor('#0b0f19')

    # Header
    ax.text(0.5, 0.95, 'Conversational A2UI Paradigm: Native Monetization Architecture', 
            fontsize=16, fontweight='bold', color='#f8fafc', ha='center', transform=ax.transAxes)
    ax.text(0.5, 0.90, 'Decoupled Reasoning, Real-Time Vickrey Second-Price Auction & Zero-Ad Educational Gating', 
            fontsize=10.5, color='#94a3b8', ha='center', transform=ax.transAxes)

    # 1. User Query (Top Center)
    rect_query = patches.FancyBboxPatch((0.32, 0.77), 0.36, 0.09,
                                        boxstyle='round,pad=0.015,rounding_size=0.025',
                                        facecolor='#1e293b', edgecolor='#38bdf8', linewidth=2,
                                        transform=ax.transAxes)
    ax.add_patch(rect_query)
    ax.text(0.5, 0.83, 'User Conversational Query', color='#ffffff', fontsize=12, fontweight='bold', ha='center', transform=ax.transAxes)
    ax.text(0.5, 0.79, 'Natural Multi-Turn Chat (Commercial or Educational)', color='#94a3b8', fontsize=9, ha='center', transform=ax.transAxes)

    # Split Arrows from Query to Agents
    ax.annotate('', xy=(0.24, 0.69), xytext=(0.42, 0.77), xycoords='axes fraction', textcoords='axes fraction',
                arrowprops=dict(arrowstyle='->,head_width=0.35,head_length=0.45', color='#38bdf8', lw=2))
    ax.annotate('', xy=(0.76, 0.69), xytext=(0.58, 0.77), xycoords='axes fraction', textcoords='axes fraction',
                arrowprops=dict(arrowstyle='->,head_width=0.35,head_length=0.45', color='#a855f7', lw=2))

    # 2. Organic Search Agent (Left Branch)
    rect_organic = patches.FancyBboxPatch((0.07, 0.49), 0.35, 0.20,
                                          boxstyle='round,pad=0.015,rounding_size=0.025',
                                          facecolor='#111827', edgecolor='#0284c7', linewidth=1.8,
                                          transform=ax.transAxes)
    ax.add_patch(rect_organic)
    ax.text(0.245, 0.63, 'Organic Synthesis Agent', color='#38bdf8', fontsize=12, fontweight='bold', ha='center', transform=ax.transAxes)
    ax.text(0.245, 0.55, '• 100% Focused on Neutral Synthesis\n• Real-Time Web Research & Citations\n• Live SSE Token Streaming', 
            color='#cbd5e1', fontsize=9.2, ha='center', transform=ax.transAxes)

    # 3. Contextual Ad Agent & Intent Gate (Right Branch)
    rect_ad = patches.FancyBboxPatch((0.58, 0.49), 0.35, 0.20,
                                     boxstyle='round,pad=0.015,rounding_size=0.025',
                                     facecolor='#111827', edgecolor='#9333ea', linewidth=1.8,
                                     transform=ax.transAxes)
    ax.add_patch(rect_ad)
    ax.text(0.755, 0.63, 'Contextual Ad Agent & Gate', color='#c084fc', fontsize=12, fontweight='bold', ha='center', transform=ax.transAxes)
    ax.text(0.755, 0.55, '• Content-Grounded Intent Classifier\n• Evaluates Commercial vs Academic\n• Deterministic Lifecycle Hook', 
            color='#cbd5e1', fontsize=9.2, ha='center', transform=ax.transAxes)

    # Decision Split from Contextual Ad Agent
    # Left split: Commercial -> Vickrey Auction
    # Right split: Educational -> Zero-ad gating
    ax.annotate('', xy=(0.65, 0.44), xytext=(0.72, 0.51), xycoords='axes fraction', textcoords='axes fraction',
                arrowprops=dict(arrowstyle='->,head_width=0.35,head_length=0.45', color='#10b981', lw=2))
    ax.text(0.65, 0.47, 'Commercial Intent', color='#34d399', fontsize=8.5, fontweight='bold', ha='right', transform=ax.transAxes)

    ax.annotate('', xy=(0.87, 0.44), xytext=(0.80, 0.51), xycoords='axes fraction', textcoords='axes fraction',
                arrowprops=dict(arrowstyle='->,head_width=0.35,head_length=0.45', color='#f59e0b', lw=2))
    ax.text(0.87, 0.47, 'Educational / Casual', color='#fbbf24', fontsize=8.5, fontweight='bold', ha='left', transform=ax.transAxes)

    # Commercial Auction Box
    rect_auction = patches.FancyBboxPatch((0.53, 0.30), 0.22, 0.14,
                                          boxstyle='round,pad=0.012,rounding_size=0.02',
                                          facecolor='#064e3b', edgecolor='#10b981', linewidth=1.5,
                                          transform=ax.transAxes)
    ax.add_patch(rect_auction)
    ax.text(0.64, 0.40, 'Vickrey Second-Price RTB', color='#a7f3d0', fontsize=10, fontweight='bold', ha='center', transform=ax.transAxes)
    ax.text(0.64, 0.34, '• Live Google / SerpApi Ads\n• Fair clearing price\n• Rich SponsoredCard UI', color='#d1fae5', fontsize=8.5, ha='center', transform=ax.transAxes)

    # Educational Gating Box
    rect_gating = patches.FancyBboxPatch((0.77, 0.30), 0.17, 0.14,
                                         boxstyle='round,pad=0.012,rounding_size=0.02',
                                         facecolor='#451a03', edgecolor='#f59e0b', linewidth=1.5,
                                         transform=ax.transAxes)
    ax.add_patch(rect_gating)
    ax.text(0.855, 0.40, 'Zero-Ad Gating', color='#fde68a', fontsize=10, fontweight='bold', ha='center', transform=ax.transAxes)
    ax.text(0.855, 0.34, '• 0 Ads Served\n• Containers Hidden\n• 100% Pure Answer', color='#fef3c7', fontsize=8.5, ha='center', transform=ax.transAxes)

    # Convergence into A2UI Standard Surface
    ax.annotate('', xy=(0.35, 0.22), xytext=(0.24, 0.51), xycoords='axes fraction', textcoords='axes fraction',
                arrowprops=dict(arrowstyle='->,head_width=0.35,head_length=0.45', color='#38bdf8', lw=2))
    ax.annotate('', xy=(0.58, 0.22), xytext=(0.64, 0.30), xycoords='axes fraction', textcoords='axes fraction',
                arrowprops=dict(arrowstyle='->,head_width=0.35,head_length=0.45', color='#10b981', lw=2))
    ax.annotate('', xy=(0.68, 0.22), xytext=(0.85, 0.30), xycoords='axes fraction', textcoords='axes fraction',
                arrowprops=dict(arrowstyle='->,head_width=0.35,head_length=0.45', color='#f59e0b', lw=2))

    # 4. Standardized A2UI Surface (Adjacency List)
    rect_surface = patches.FancyBboxPatch((0.20, 0.13), 0.60, 0.09,
                                          boxstyle='round,pad=0.015,rounding_size=0.025',
                                          facecolor='#1e1b4b', edgecolor='#6366f1', linewidth=2,
                                          transform=ax.transAxes)
    ax.add_patch(rect_surface)
    ax.text(0.5, 0.185, 'Standardized A2UI v0.9 Surface Payload (Adjacency List JSON)', 
            color='#ffffff', fontsize=11.5, fontweight='bold', ha='center', transform=ax.transAxes)
    ax.text(0.5, 0.15, 'Organic Markdown Summary + Key Highlights + Verified Sponsored Cards (If Commercial)', 
            color='#c7d2fe', fontsize=9, ha='center', transform=ax.transAxes)

    # Final Arrow down to Any Chat Platform
    ax.annotate('', xy=(0.5, 0.09), xytext=(0.5, 0.13), xycoords='axes fraction', textcoords='axes fraction',
                arrowprops=dict(arrowstyle='->,head_width=0.35,head_length=0.45', color='#818cf8', lw=2.2))

    # 5. Universal Platform Support Box
    rect_platform = patches.FancyBboxPatch((0.12, 0.015), 0.76, 0.07,
                                           boxstyle='round,pad=0.01,rounding_size=0.02',
                                           facecolor='#0f172a', edgecolor='#38bdf8', linewidth=1.5,
                                           transform=ax.transAxes)
    ax.add_patch(rect_platform)
    ax.text(0.5, 0.05, 'Universal Interoperability: Direct Client-Side Rendering with Zero Backend Changes', 
            color='#38bdf8', fontsize=10.5, fontweight='bold', ha='center', transform=ax.transAxes)
    ax.text(0.5, 0.025, 'Claude • Gemini • ChatGPT • Grok • Custom Web Chat Applications (React / Lit / Web Components)', 
            color='#cbd5e1', fontsize=9, ha='center', transform=ax.transAxes)

    ax.axis('off')
    plt.subplots_adjust(left=0, right=1, top=1, bottom=0)
    plt.savefig('docs/images/paradigm_conversational_a2ui.png', dpi=300, facecolor=fig.get_facecolor(), edgecolor='none')
    plt.close()
    print("Created docs/images/paradigm_conversational_a2ui.png")

if __name__ == '__main__':
    generate_traditional_search_diagram()
    generate_conversational_a2ui_diagram()
