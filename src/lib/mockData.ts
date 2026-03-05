export const mockResults = {
  ticker: "NVDA",
  companyName: "NVIDIA Corporation",
  currentPrice: 875,
  bull: {
    score: 8,
    bestCaseTarget: 2000,
    timeframe: "5 years",
    advantages: [
      "80% AI chip market share dominance",
      "CUDA moat with 15-year ecosystem lock-in",
      "Pricing power with 40% YoY revenue growth",
      "Data center revenue up 409% year-over-year",
      "Strategic partnerships with every major cloud provider",
    ],
    catalysts: [
      "Blackwell GPU architecture launch driving next upgrade cycle",
      "Sovereign AI investments creating new demand verticals",
      "Automotive and robotics TAM expansion to $300B by 2030",
    ],
  },
  bear: {
    score: 7,
    worstCaseTarget: 250,
    timeframe: "2 years",
    risks: [
      "Customer concentration — top 4 clients = 40% revenue",
      "AMD MI300X gaining traction in inference workloads",
      "Custom silicon (Google TPU, Amazon Trainium) reducing dependency",
      "Export restrictions to China cutting $8B+ annual revenue",
      "Cyclical semiconductor demand post-AI investment peak",
    ],
    valuationConcerns:
      "Trading at 65x forward earnings vs. semiconductor average of 20x. Revenue growth deceleration from 122% to projected 55% could trigger multiple compression. Historical precedent: Cisco in 2000 traded at 70x before losing 80% of value.",
  },
  strategist: {
    currentExposure: "15%",
    concentrationRisk: "HIGH",
    recommendedAllocation: 25000,
    maxAllocation: "20%",
    reasoning:
      "Given your moderate risk tolerance and 5-year horizon, a position size of $25,000 represents a meaningful but not excessive allocation. Dollar-cost averaging over 3 months reduces timing risk while maintaining upside exposure to AI secular trend.",
  },
  confidence: {
    marketPosition: 92,
    financialHealth: 88,
    growthPotential: 85,
    riskAssessment: 72,
    portfolioFit: 78,
  },
  recommendation: {
    overallConfidence: 75,
    action: "BUY",
    amount: "$25,000",
    entry: "DCA over 3 months",
    risk: "Stop-loss at $350",
    reasoning:
      "NVIDIA presents a compelling but not risk-free opportunity. The company's dominant position in AI infrastructure is offset by elevated valuation and increasing competitive threats. A measured entry via dollar-cost averaging balances conviction with prudence.",
    factors: [
      "AI infrastructure spending shows no signs of slowing through 2026",
      "Competitive moat from CUDA ecosystem is durable but not impenetrable",
      "Valuation premium is justified by growth but leaves limited margin of safety",
      "Portfolio concentration risk requires disciplined position sizing",
    ],
    confidenceBreakdown: {
      "Technical Analysis": 82,
      "Fundamental Value": 70,
      "Market Sentiment": 85,
      "Risk/Reward": 68,
    },
  },
};
