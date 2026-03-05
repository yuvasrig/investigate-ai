
# InvestiGate - Multi-Agent AI Investment Advisor

## Overview
A sophisticated, Bloomberg-meets-Stripe investment analysis app with three pages: Input Form → Loading State → Results Dashboard. All data will be mock/hardcoded to demonstrate the full UI flow.

## Color & Design System
- Update CSS variables to match the specified palette: slate blue primary, soft indigo accent, forest green/terracotta/navy for agent themes
- Clean white cards with subtle shadows, thin colored borders, generous spacing
- Inter font via Google Fonts

## Page 1 — Landing / Input Form
- Minimal header: "InvestiGate" logo in slate blue with gray tagline
- Hero: "Should You Invest?" heading + subtitle
- White card form with: Stock Ticker, Investment Amount ($), Portfolio Value ($), Risk Tolerance dropdown, Time Horizon pill selector
- Solid indigo "Analyze Investment" button
- 3 feature preview cards below (Bull, Bear, Portfolio Fit) with matching icons and colors

## Page 2 — Loading State
- Centered indigo spinner + "Analyzing Investment..." text
- 3 agent status cards with colored left borders, animated progress bars filling sequentially
- Auto-transitions to results after ~4 seconds

## Page 3 — Results Dashboard
- Header with ticker name + "New Analysis" link
- 3-column grid of agent cards:
  - **Bull Analyst**: green-bordered card with 8/10 score, best case target, key advantages list with green checkmarks, growth catalysts
  - **Bear Analyst**: red-bordered card with 7/10 risk score, worst case target, key risks with warning icons, valuation concerns
  - **Portfolio Strategist**: blue-bordered card with exposure analysis, concentration risk badge, recommended allocation
- **Confidence Chart**: horizontal bar chart using Recharts with muted indigo bars
- **Final Recommendation**: indigo-bordered card with 75% confidence, 4-metric grid (Action/Amount/Entry/Risk), key decision factors, confidence breakdown bars

## Routing & State
- React Router: `/` (input), `/loading` (loading), `/results` (results)
- Form state passed via React context or URL params
- Mock data for all analysis results (NVIDIA as example stock)

## Animations
- Subtle fade-in on page transitions
- Progress bar fills on loading page
- Hover effects on cards and buttons
