# Design Rationale

## Why Conversational Interface?

Traditional recycling facility operators are not data entry specialists. They work on the floor, handling materials and operating machinery. 

**Problem with forms:**
- Multi-field forms are time-consuming
- Requires training to understand field mappings
- Prone to errors (wrong field, typos)
- Disrupts workflow

**Solution with chat:**
- Single text input
- Natural language matches how people think
- AI extracts structure automatically
- Faster, fewer errors

Example: "Purchased 300kg PET from Vendor A yesterday" vs filling 5 form fields.

---

## Why Sankey Diagrams?

Sankey diagrams are the single most intuitive visualization for material flow:

1. **Width = Quantity**: Immediately shows relative volumes
2. **Flow direction**: Left to right = source to destination
3. **Loss visualization**: Gaps show material lost
4. **Multi-path**: Handles splits and merges naturally

A regulator can understand the entire batch journey in seconds.

---

## Why Confidence Scoring?

**Problem**: Data you can't trust is worse than no data.

**Solution**: Show a 61% confidence badge next to batch records.

This:
- Signals data quality to stakeholders
- Encourages complete data entry
- Turns uncertainty into a feature (not a bug)
- Helps auditors know when to request more info

---

## Color Coding System

| Color | Meaning | Usage |
|-------|---------|-------|
| Green | Approved/Good | Completed stages, high yield |
| Yellow | Warning | Medium loss, pending verification |
| Red | Critical/Rejected | High loss, failed QC |
| Blue | Information | In-progress, neutral status |
| Purple | Insights | AI-generated recommendations |

---

## Dashboard Layout

### Summary Cards (Top Row)
- Instant overview of key metrics
- Total batches, input, yield, loss

### Material Breakdown (Pie Chart)
- Shows distribution of material types
- Helps identify most processed materials

### Loss by Stage (Bar Chart)
- Identifies loss hotspots
- Guides process improvement

### Stage Flow Table
- Detailed breakdown per stage
- Numeric precision for analysis

---

## Responsive Design

The dashboard is designed for:
- Desktop monitors (primary - operations center)
- Tablets (secondary - floor supervisors)
- Mobile phones (tertiary - quick checks)

---

## Accessibility Considerations

- High contrast colors (WCAG AA compliant)
- Clear labels on all charts
- Keyboard navigation support
- Screen reader compatible (planned)
