import { BarChart3, BrainCircuit, FileText } from "lucide-react";

// ─── Home Page ───

export const homeFeatures = [
  {
    icon: BarChart3,
    title: "Smart Visualizations",
    desc: "Auto-generated charts",
    color: "text-primary bg-orange-50",
  },
  {
    icon: BrainCircuit,
    title: "AutoML Insights",
    desc: "Machine learning analysis",
    color: "text-secondary bg-yellow-50",
  },
  {
    icon: FileText,
    title: "AI Narratives",
    desc: "Natural language reports",
    color: "text-primary bg-orange-50",
  },
];

// ─── Data Preview Page ───

export const dataPreviewColumns = ["CUSTOMER ID", "AGE", "GENDER", "INCOME", "SPENDING", "CATEGORY"];

export const cleanedData = [
  { id: "C001", age: 34, gender: "Female", income: "$58,400", spending: "$1,240", category: "Electronics" },
  { id: "C002", age: 27, gender: "Male", income: "$42,100", spending: "$890", category: "Sports" },
  { id: "C003", age: 45, gender: "Female", income: "$73,200", spending: "$2,150", category: "Clothing" },
  { id: "C004", age: 31, gender: "Male", income: "$55,800", spending: "$1,050", category: "Electronics" },
  { id: "C005", age: 52, gender: "Female", income: "$91,400", spending: "$3,200", category: "Home & Garden" },
  { id: "C006", age: 29, gender: "Male", income: "$38,600", spending: "$760", category: "Sports" },
  { id: "C007", age: 38, gender: "Male", income: "$67,300", spending: "$1,580", category: "Home & Garden" },
  { id: "C008", age: 44, gender: "Female", income: "$82,100", spending: "$2,650", category: "Electronics" },
  { id: "C009", age: 23, gender: "Male", income: "$31,200", spending: "$490", category: "Clothing" },
];

export const originalData = [
  { id: "C001", age: 34, gender: "Female", income: "$58,400", spending: "$1,240", category: "Electronics" },
  { id: "C002", age: 27, gender: "Male", income: null, spending: "$890", category: "Sports", highlight: true },
  { id: "C003", age: 45, gender: "Female", income: "$73,200", spending: "$2,150", category: "Clothing" },
  { id: "C003", age: 45, gender: "Female", income: "$73,200", spending: "$2,150", category: "Clothing", highlight: true, duplicate: true },
  { id: "C004", age: 31, gender: "Male", income: "$55,800", spending: "$1,050", category: "Electronics" },
  { id: "C005", age: 52, gender: "Female", income: "$450,000", spending: "$3,200", category: "Home & Garden", highlight: true },
  { id: "C006", age: 29, gender: "Male", income: "$38,600", spending: "$760", category: "Sports" },
  { id: "C007", age: 38, gender: "Male", income: "$67,300", spending: "$1,580", category: "Home & Garden" },
  { id: "C008", age: 44, gender: "Female", income: "$82,100", spending: "$2,650", category: "Electronics" },
  { id: "C009", age: 23, gender: "Male", income: "$31,200", spending: "$490", category: "Clothing" },
];

export const preprocessingItems = [
  {
    title: "Missing values handled",
    count: "1 item",
    detail: "Imputed with median",
    expandedText: "Customer C002 had a null Income value. Imputed using the dataset median income.",
    nullVal: "null",
    newVal: "$42,100",
  },
  {
    title: "Duplicates removed",
    count: "1 item",
    detail: "Dropped duplicate row",
    expandedText: "Customer C003 appeared twice in the dataset. The duplicate entry was removed.",
    nullVal: "8,001 rows",
    newVal: "8,000 rows",
  },
  {
    title: "Data types corrected",
    count: "2 columns",
    detail: "Converted to numeric format",
    expandedText: "Income and Spending were stored as text strings. Converted to numeric for analysis.",
    nullVal: "\"58400\" (text)",
    newVal: "58400 (numeric)",
  },
  {
    title: "Outliers detected",
    count: "3 items",
    detail: "Capped at 99th percentile",
    expandedText: "3 Income values exceeded 3 standard deviations above the mean. Capped at the 99th percentile.",
    nullVal: "$450,000",
    newVal: "$195,000",
  },
];

export const dataPreviewMeta = {
  totalRows: 8000,
  pageSize: 7,
  qualityScore: 94,
};

// ─── Visualizations Page ───

export const valueDistribution = [
  { range: "0-20", count: 8 },
  { range: "21-40", count: 15 },
  { range: "41-60", count: 45 },
  { range: "61-80", count: 35 },
  { range: "81-100", count: 12 },
];

export const spreadOutliers = [
  { group: "Group A", min: 15, q1: 30, median: 52, q3: 70, max: 85, avg: 52 },
  { group: "Group B", min: 20, q1: 35, median: 58, q3: 72, max: 88, avg: 58 },
  { group: "Group C", min: 10, q1: 25, median: 45, q3: 75, max: 92, avg: 45 },
];

export const relationshipData = [
  { x: 5, y: 20 }, { x: 12, y: 30 }, { x: 18, y: 35 }, { x: 22, y: 38 },
  { x: 28, y: 42 }, { x: 32, y: 48 }, { x: 35, y: 45 }, { x: 38, y: 50 },
  { x: 42, y: 52 }, { x: 45, y: 55 }, { x: 48, y: 48 }, { x: 52, y: 58 },
  { x: 55, y: 60 }, { x: 58, y: 55 }, { x: 62, y: 65 }, { x: 65, y: 62 },
  { x: 68, y: 70 }, { x: 72, y: 68 }, { x: 75, y: 75 },
];

export const groupComparison = [
  { category: "Electronics", groupA: 4500, groupB: 5800 },
  { category: "Clothing", groupA: 3200, groupB: 3800 },
  { category: "Home", groupA: 3800, groupB: 2800 },
  { category: "Sports", groupA: 2500, groupB: 3200 },
];

export const sequentialPatterns = [
  { month: "Jan", seriesA: 42, seriesB: 38 },
  { month: "Feb", seriesA: 48, seriesB: 44 },
  { month: "Mar", seriesA: 52, seriesB: 50 },
  { month: "Apr", seriesA: 55, seriesB: 56 },
  { month: "May", seriesA: 58, seriesB: 62 },
  { month: "Jun", seriesA: 62, seriesB: 70 },
];

export const fieldConnections = [
  { fields: "Age \u2194 Spending", strength: "Strong" },
  { fields: "Age \u2194 Frequency", strength: "Moderate" },
  { fields: "Spending \u2194 Frequency", strength: "Moderate" },
  { fields: "Age \u2194 Satisfaction", strength: "Weak" },
  { fields: "Spending \u2194 Satisfaction", strength: "Strong" },
  { fields: "Frequency \u2194 Satisfaction", strength: "Moderate" },
];

export const keyTakeaways = [
  {
    title: "Groups behave differently",
    desc: "Group B shows consistently higher values than other groups, especially in the Sports category.",
    type: "insight",
  },
  {
    title: "These fields move together",
    desc: "Age and Spending appear closely connected\u2014when one increases, so does the other.",
    type: "insight",
  },
  {
    title: "Most values cluster in the middle",
    desc: "The majority of records fall within a moderate range, with fewer extremes on either end.",
    type: "insight",
  },
  {
    title: "Some entries stand out",
    desc: "A few records in the 80-100 range are unusually high compared to the rest.",
    type: "warning",
  },
];

// ─── Narrative Page ───

export const narrativeReport = {
  pdfPath: "/sample_report.pdf",
  executiveSummary:
    "This comprehensive analysis of the uploaded dataset reveals significant patterns in customer behavior and revenue distribution across global markets. The data encompasses 1,247 records spanning Q1\u2013Q4 of the fiscal year, providing robust statistical significance for the insights derived.",
  keyFindings: [
    {
      title: "Revenue Performance",
      content:
        "The analysis indicates a strong positive trajectory in revenue generation, with the North American market demonstrating the highest absolute figures ($3.2M aggregate) while the Asia Pacific region shows the most promising growth rate at 15.7% quarter-over-quarter. [See: Group Comparison chart]",
      subtext:
        "The correlation analysis reveals a notable relationship between customer acquisition timing and lifetime value, suggesting that customers acquired during Q2 demonstrate 23% higher retention rates compared to other periods.",
    },
    {
      title: "Customer Segmentation",
      content:
        "Three distinct customer segments emerged from the data: High-Value Customers (23%), Occasional Buyers (45%), and New Customers (32%). [See: Field Connections chart]",
      subtext:
        "High-Value Customers show the strongest engagement, while New Customers represent the fastest-growing segment.",
    },
  ],
  developerSection: {
    bestModel: "Gradient Boosting Regressor",
    metric: "R\u00b2 = 0.874",
    trainingTime: "12.4s",
    featureImportances: [
      { feature: "Income", importance: 0.342 },
      { feature: "Spending", importance: 0.287 },
      { feature: "Age", importance: 0.184 },
      { feature: "Frequency", importance: 0.121 },
      { feature: "Tenure", importance: 0.066 },
    ],
    shapSummary:
      "SHAP analysis confirms Income and Spending as dominant drivers. Interactions between Age and Frequency show non-linear effects above the 60th percentile.",
    stats: [
      { label: "Mean Revenue per Customer", value: "$112,450" },
      { label: "Standard Deviation", value: "$45,200" },
      { label: "Growth Rate Variance", value: "\u00b14.2%" },
      { label: "Confidence Interval", value: "95%" },
    ],
  },
};

// ─── Tournament Leaderboard (AutoML Insights) ───

export const tournamentLeaderboard = [
  {
    rank: 1,
    model: "Gradient Boosting Regressor",
    metric: "R\u00b2",
    score: 0.874,
    trainingTime: "12.4s",
    isWinner: true,
  },
  {
    rank: 2,
    model: "Random Forest Regressor",
    metric: "R\u00b2",
    score: 0.851,
    trainingTime: "8.2s",
    isWinner: false,
  },
  {
    rank: 3,
    model: "Extra Trees Regressor",
    metric: "R\u00b2",
    score: 0.838,
    trainingTime: "6.7s",
    isWinner: false,
  },
];

// ─── Target Column Identification ───

export const targetCandidates = [
  { column: "Spending", score: 0.92, problemType: "Regression" },
  { column: "Satisfaction", score: 0.78, problemType: "Regression" },
  { column: "Category", score: 0.64, problemType: "Classification" },
  { column: "Region", score: 0.41, problemType: "Classification" },
];

export const taskIdentification = {
  target: "Spending",
  problemType: "Regression",
  confidence: "high",
};

// ─── AutoML Insights (Data Insights) Page ───

export const dataStory = [
  "Looking at your data, we found several interesting patterns that help explain what\u2019s happening across different groups, categories, and segments.",
  "The most striking finding is how differently customer groups behave. High-value customers show significantly more activity than other segments, while occasional buyers remain steady. New customers form the fastest-growing segment, suggesting that acquisition efforts are working well.",
  "In terms of product categories, Sports and Electronics stand out as the strongest performers. Meanwhile, Home & Garden appears weaker compared to other categories. These differences suggest that customer preferences vary considerably across product types.",
  "We also noticed that certain fields tend to move together. For example, spending levels and satisfaction scores appear closely connected\u2014customers who spend more tend to report higher satisfaction. Similarly, account age and loyalty seem linked, with longer-term customers showing more consistent behavior.",
];

export const dataStoryHighlight =
  "Overall, the data reveals meaningful differences between groups, strong relationships between certain fields, and a few unusual patterns worth investigating. These insights suggest opportunities to tailor strategies for different customer segments.";

export const keyInfluencingFactors = [
  { name: "Customer Type", desc: "Different customer segments show very different behaviors and outcomes.", level: "high" },
  { name: "Product Category", desc: "Category choice strongly influences overall patterns and results.", level: "high" },
  { name: "Time of Week", desc: "Weekday vs weekend activity shows moderate differences.", level: "medium" },
  { name: "Geographic Region", desc: "Some regions changed more dramatically than others.", level: "medium" },
  { name: "Purchase History", desc: "Past behavior has some influence on future activity.", level: "low" },
];

export const groupsIdentified = [
  { name: "High-Value Customers", pct: "23%", desc: "These customers spend the most and visit frequently. They show the highest engagement levels.", trend: "up" },
  { name: "Occasional Buyers", pct: "45%", desc: "The largest group, these customers buy periodically and show consistent, stable behavior.", trend: "stable" },
  { name: "New Customers", pct: "32%", desc: "Recently acquired customers, representing a growing segment with strong potential.", trend: "up" },
];

export const comparisons = [
  { name: "Electronics", level: "Higher", desc: "Performs significantly above average, driven by mobile devices" },
  { name: "Sports", level: "Highest", desc: "Strongest category overall, especially fitness equipment" },
  { name: "Clothing", level: "Average", desc: "Performs in line with typical values" },
  { name: "Home & Garden", level: "Lower", desc: "Below average performance compared to other categories" },
];

export const anomalies = [
  { title: "Outlier group detected", desc: "A small cluster of records shows values much higher than the rest of the data." },
  { title: "Unusual low-activity entries", desc: "Some records show unexpectedly low engagement compared to similar entries." },
  { title: "Missing value pattern", desc: "Certain fields have gaps that may affect analysis\u2014consider reviewing data quality." },
];

export const nextSteps = [
  { text: "Focus on Sports and Electronics\u2014these categories show the strongest performance.", priority: "high" },
  { text: "Target high-value customers specifically\u2014they display the highest engagement and spending.", priority: "high" },
  { text: "Investigate Home & Garden\u2014it underperforms compared to other categories.", priority: "medium" },
  { text: "Nurture new customers\u2014this growing segment represents strong potential.", priority: "medium" },
  { text: "Review the outlier records\u2014understanding why they differ may reveal opportunities.", priority: "low" },
];

// ─── EDA Section (Data Preview Page) ───

export const edaData = {
  datasetOverview: {
    totalRows: 8000,
    totalColumns: 19,
    duplicateRows: 0,
    totalMissingValues: 0,
  },
  columnTypeSummary: {
    numerical: 14,
    categorical: 5,
    datetime: 0,
  },
  columnDetails: [
    { name: "CustomerID", type: "Numerical", nulls: 0, unique: 8000 },
    { name: "Age", type: "Numerical", nulls: 0, unique: 72 },
    { name: "Gender", type: "Categorical", nulls: 0, unique: 2 },
    { name: "Income", type: "Numerical", nulls: 0, unique: 4523 },
    { name: "Spending", type: "Numerical", nulls: 0, unique: 3891 },
    { name: "Category", type: "Categorical", nulls: 0, unique: 4 },
    { name: "Region", type: "Categorical", nulls: 0, unique: 5 },
    { name: "Satisfaction", type: "Numerical", nulls: 0, unique: 10 },
    { name: "Frequency", type: "Numerical", nulls: 0, unique: 365 },
    { name: "Tenure", type: "Numerical", nulls: 0, unique: 120 },
  ],
  statisticalSummary: [
    { column: "Age",          count: "8,000", mean: "38.4",   std: "12.6",  min: "18",     max: "75",      median: "37",     skewness: "0.21",  kurtosis: "-0.44" },
    { column: "Income",       count: "8,000", mean: "58,420", std: "24,310",min: "15,000", max: "195,000", median: "55,800", skewness: "1.32",  kurtosis: "2.87"  },
    { column: "Spending",     count: "8,000", mean: "1,247",  std: "892",   min: "50",     max: "9,800",   median: "1,050",  skewness: "2.14",  kurtosis: "6.51"  },
    { column: "Satisfaction", count: "8,000", mean: "7.2",    std: "1.8",   min: "1",      max: "10",      median: "7",      skewness: "-0.63", kurtosis: "0.12"  },
    { column: "Frequency",    count: "8,000", mean: "24.6",   std: "18.3",  min: "1",      max: "365",     median: "20",     skewness: "3.07",  kurtosis: "14.2"  },
  ],
  outlierDetection: [
    { column: "Age",          method: "IQR", outliers: 12,  lowerBound: "8.5",      upperBound: "68.5"    },
    { column: "Income",       method: "IQR", outliers: 148, lowerBound: "-$17,865", upperBound: "$133,065"},
    { column: "Spending",     method: "IQR", outliers: 203, lowerBound: "-$1,682",  upperBound: "$3,782"  },
    { column: "Satisfaction", method: "IQR", outliers: 0,   lowerBound: "3.25",     upperBound: "11.75"   },
    { column: "Frequency",    method: "IQR", outliers: 87,  lowerBound: "-24.5",    upperBound: "76.5"    },
  ],
  categoricalAnalysis: [
    {
      column: "Gender",
      topValues: [
        { value: "Female", count: 4127, pct: "51.6%" },
        { value: "Male",   count: 3873, pct: "48.4%" },
      ],
    },
    {
      column: "Category",
      topValues: [
        { value: "Electronics",  count: 2480, pct: "31.0%" },
        { value: "Sports",       count: 2104, pct: "26.3%" },
        { value: "Clothing",     count: 1856, pct: "23.2%" },
        { value: "Home & Garden",count: 1560, pct: "19.5%" },
      ],
    },
    {
      column: "Region",
      topValues: [
        { value: "North America", count: 2240, pct: "28.0%" },
        { value: "Europe",        count: 1920, pct: "24.0%" },
        { value: "Asia Pacific",  count: 1760, pct: "22.0%" },
        { value: "Latin America", count: 1200, pct: "15.0%" },
        { value: "Middle East",   count: 880,  pct: "11.0%" },
      ],
    },
  ],
};

