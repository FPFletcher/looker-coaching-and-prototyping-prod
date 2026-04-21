---
name: Period over Period Analysis
description: Dynamic implementation of Period-over-Period (PoP) comparison using conditional markers, dynamic parameters, and liquid.
---

# LookML Code Example: Period-over-Period (PoP) Analysis

## 1. Parameters & Filters

```lookml
#### This parameter will allow a user to select a Top N ranking limit for bucketing the brands, almost like parameterizing the Row Limit in the UI
parameter: filter_quantity_or_revenue {
  # group_label: "Analyse dynamique"
  label: "Filter - Quantity/ Revenue"
  view_label: "01 - Dynamic analysis"
  type: unquoted
  default_value: "1"
  allowed_value: {
    label: "Revenue"
    value: "1"
  }
  allowed_value: {
    label: "Quantity"
    value: "2"
  }
}

#### PoP Analysis ####

filter: comparison_range {
  label: "Comparison Range"
  view_label: "02 - PoP Comparison"
  type: date
}

parameter: comparison_type {
  label: "Comparison Type"
  view_label: "02 - PoP Comparison"
  type: unquoted
  default_value: "year"
  allowed_value: {
    label: "Year"
    value: "year"
  }
  allowed_value: {
    label: "Quarter"
    value: "quarter"
  }
  allowed_value: {
    label: "Month"
    value: "month"
  }
  allowed_value: {
    label: "Week"
    value: "week"
  }
}
```

## 2. Dimensions & Markers

```lookml
# Dimensions and Measures
#####################################

dimension: pop_comparison_marker_this_period {
  # hidden: yes
  label: "PoP Comparison flag - Period analyzed"
  view_label: "02 - PoP Comparison"
  type: string
  sql:
    CASE
      WHEN {% condition comparison_range %} ${order_date_raw} {% endcondition %} THEN 'Period analyzed'
      ELSE 'Outside PoP Comparison'
    END
  ;;
}

dimension: pop_comparison_marker_previous_period {
  # hidden: yes
  label: "PoP Comparison flag - Previous Period"
  view_label: "02 - PoP Comparison"
  type: string
  sql:
    {% if comparison_type._parameter_value == 'week' %}
    CASE
      WHEN ${order_date_raw} >= TIMESTAMP(DATE_ADD(CAST({% date_start comparison_range %} AS DATE), INTERVAL -1 WEEK)) AND ${order_date_raw} < TIMESTAMP(DATE_ADD(CAST({% date_end comparison_range %} AS DATE), INTERVAL -1 WEEK)) THEN 'Same period - Prior Week'
      ELSE 'Outside PoP Comparison'
    END
    {% elsif comparison_type._parameter_value == 'month' %}
    CASE
      WHEN ${order_date_raw} >= TIMESTAMP(DATE_ADD(CAST({% date_start comparison_range %} AS DATE), INTERVAL -1 MONTH)) AND ${order_date_raw} < TIMESTAMP(DATE_ADD(CAST({% date_end comparison_range %} AS DATE), INTERVAL -1 MONTH)) THEN 'Same period - Prior Month'
      ELSE 'Outside PoP Comparison'
    END
    {% elsif comparison_type._parameter_value == 'quarter' %}
    CASE
      WHEN ${order_date_raw} >= TIMESTAMP(DATE_ADD(CAST({% date_start comparison_range %} AS DATE), INTERVAL -1 QUARTER)) AND ${order_date_raw} < TIMESTAMP(DATE_ADD(CAST({% date_end comparison_range %} AS DATE), INTERVAL -1 QUARTER)) THEN 'Same period - Prior Quarter'
      ELSE 'Outside PoP Comparison'
    END
    {% elsif comparison_type._parameter_value == 'year' %}
    CASE
      WHEN ${order_date_raw} >= TIMESTAMP(DATE_ADD(CAST({% date_start comparison_range %} AS DATE), INTERVAL -1 YEAR)) AND ${order_date_raw} < TIMESTAMP(DATE_ADD(CAST({% date_end comparison_range %} AS DATE), INTERVAL -1 YEAR)) THEN 'Same period - Prior Year'
      ELSE 'Outside PoP Comparison'
    END
    {% endif %}
  ;;
}

dimension: pop_comparison_marker {
  label: "PoP Comparison flag"
  view_label: "02 - PoP Comparison"
  type: string
  sql: CASE WHEN CONCAT (${pop_comparison_marker_this_period}, ' ', ${pop_comparison_marker_previous_period}) LIKE 'Period analyzed%'
         THEN 'Period analyzed'
         WHEN CONCAT (${pop_comparison_marker_this_period}, ' ', ${pop_comparison_marker_previous_period}) LIKE '%Same period%' OR CONCAT (${pop_comparison_marker_this_period}, ' ', ${pop_comparison_marker_previous_period}) LIKE 'Outside PoP Comparison Same period%'
         THEN 'Previous period'
         ELSE CONCAT (${pop_comparison_marker_this_period}, ' ', ${pop_comparison_marker_previous_period})
       END
  ;;
}
```

## 3. Measures & Final Dynamic Implementation

```lookml
#### This Period ####

measure: comparison_this_period_sum_total_price_with_taxes {
  label: "Comparison Global Revenue (This Period)"
  view_label: "02 - PoP Comparison"
  value_format: "[>=1000000]€#\,##0.0\,,\"M\";[>=1000]€#\,##0,\"k\";€#\,##0"
  filters: [pop_comparison_marker_this_period: "Period analyzed"]
  type: sum
  sql: ${total_price_with_taxes} ;;
}

measure: comparison_this_period_sum_quantity {
  label: "Comparison Ordered Quantity (This Period)"
  view_label: "02 - PoP Comparison"
  value_format: "[>=1000000]#\,##0.0\,,\"M\";[>=1000]#\,##0,\"k\";#\,##0"
  type: sum
  filters: [pop_comparison_marker_this_period: "Period analyzed"]
  sql: ${quantity} ;;
}

#### Prior Period ####

measure: comparison_prior_period_sum_total_price_with_taxes {
  label: "Comparison Total Sale Price (Prior Period)"
  view_label: "02 - PoP Comparison"
  value_format: "[>=1000000]€#\,##0.0\,,\"M\";[>=1000]€#\,##0,\"k\";€#\,##0"
  type: number
  sql: SUM(
         CASE
           WHEN ${pop_comparison_marker_previous_period} LIKE '%Prior%'
           THEN ${total_price_with_taxes}
           ELSE NULL END) ;;
}

measure: comparison_prior_period_sum_quantity {
  label: "Comparison Total Quantity (Prior Period)"
  view_label: "02 - PoP Comparison"
  value_format: "[>=1000000]#\,##0.0\,,\"M\";[>=1000]#\,##0,\"k\";#\,##0"
  type: number
  sql: SUM(
         CASE
           WHEN ${pop_comparison_marker_previous_period} LIKE '%Prior%'
           THEN ${quantity}
           ELSE NULL END) ;;
}

#### % change PoP ####

measure: comparison_sum_total_price_with_taxes {
  label: "PoP Comparison Total Sale Price With Taxes"
  view_label: "02 - PoP Comparison"
  value_format_name: percent_0
  type: number
  sql: SAFE_DIVIDE(${comparison_this_period_sum_total_price_with_taxes}, ${comparison_prior_period_sum_total_price_with_taxes}) - 1 ;;
}

measure: comparison_sum_quantity {
  label: "PoP Comparison Total Quantity"
  view_label: "02 - PoP Comparison"
  value_format_name: percent_0
  type: number
  sql: SAFE_DIVIDE(${comparison_this_period_sum_quantity}, ${comparison_prior_period_sum_quantity}) - 1 ;;
}

#### Making it dynamic ####

measure: dynamic_globalPoP_thisPeriod_field {
  label: "Dynamic Total - Global PoP Revenue or Quantity (This Period)"
  view_label: "01 - Dynamic analysis"
  label_from_parameter: filter_quantity_or_revenue
  type: number
  sql:
    {% if filter_quantity_or_revenue._parameter_value == "'1'" %} ${comparison_this_period_sum_total_price_with_taxes}
    {% elsif filter_quantity_or_revenue._parameter_value == "'2'" %} ${comparison_this_period_sum_quantity}
    {% else %} ${comparison_this_period_sum_total_price_with_taxes}
    {% endif %}
  ;;
  html:
    {% if filter_quantity_or_revenue._parameter_value == "'1'" %} {{ comparison_this_period_sum_total_price_with_taxes._rendered_value }}
    {% elsif filter_quantity_or_revenue._parameter_value == "'2'" %} {{ comparison_this_period_sum_quantity._rendered_value }}
    {% else %} {{ comparison_this_period_sum_total_price_with_taxes._rendered_value }}
    {% endif %}
  ;;
}

measure: dynamic_globalPoP_priorPeriod_field {
  label: "Dynamic Total - Global PoP Revenue or Quantity (Prior Period)"
  view_label: "01 - Dynamic analysis"
  label_from_parameter: filter_quantity_or_revenue
  type: number
  sql:
    {% if filter_quantity_or_revenue._parameter_value == "'1'" %} ${comparison_prior_period_sum_total_price_with_taxes}
    {% elsif filter_quantity_or_revenue._parameter_value == "'2'" %} ${comparison_prior_period_sum_quantity}
    {% else %} ${comparison_prior_period_sum_total_price_with_taxes}
    {% endif %}
  ;;
  html:
    {% if filter_quantity_or_revenue._parameter_value == "'1'" %} {{ comparison_prior_period_sum_total_price_with_taxes._rendered_value }}
    {% elsif filter_quantity_or_revenue._parameter_value == "'2'" %} {{ comparison_prior_period_sum_quantity._rendered_value }}
    {% else %} {{ comparison_prior_period_sum_total_price_with_taxes._rendered_value }}
    {% endif %}
  ;;
}

measure: dynamic_globalPoP_comparison_field {
  label: "Dynamic Total - Global PoP comparison Revenue or Quantity"
  view_label: "01 - Dynamic analysis"
  label_from_parameter: filter_quantity_or_revenue
  type: number
  sql:
    {% if filter_quantity_or_revenue._parameter_value == "'1'" %} ${comparison_sum_total_price_with_taxes}
    {% elsif filter_quantity_or_revenue._parameter_value == "'2'" %} ${comparison_sum_quantity}
    {% else %} ${comparison_sum_total_price_with_taxes}
    {% endif %}
  ;;
  html:
    {% if filter_quantity_or_revenue._parameter_value == "'1'" %} {{ comparison_sum_total_price_with_taxes._rendered_value }}
    {% elsif filter_quantity_or_revenue._parameter_value == "'2'" %} {{ comparison_sum_quantity._rendered_value }}
    {% else %} {{ comparison_sum_total_price_with_taxes._rendered_value }}
    {% endif %}
  ;;
}
```

## 4. Dashboard Integration (CRITICAL)

When creating a Dashboard that utilizes this PoP logic, you **MUST** configure the Dashboard Filters using the parameter fields, NOT the standard date dimensions.

- ❌ **WRONG:** Filtering the dashboard using the raw Date dimension. This overrides the PoP SQL logic and returns incorrect or empty data.
- ✅ **CORRECT:** Call `create_dashboard_filter` mapping to the `comparison_range` filter AND the `comparison_type` parameter (or their equivalents like `current_period_filter` and `previous_period_filter`).

**MANDATORY:** Always explicitly remind the user in chat to manually map these filters to the corresponding parameter fields in the "Tiles To Update" tab within the Looker UI, as the AI tool cannot do this step.
