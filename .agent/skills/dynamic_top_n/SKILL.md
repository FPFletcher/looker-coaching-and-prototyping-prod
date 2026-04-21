---
name: Dynamic Top N Ranking
description: The most dynamic approach that uses multiple parameters and liquid to derive the Top X ranking of X metrics for X criteria.
---

# Looker Ranking: Top N of X metrics for X criteria

## Context
Your team may often need to represent the top N of their data to the end user. There are a number of different ways to do this depending on the complexity of the task. This document is about the most dynamic approach that uses multiple parameters and liquid to derive the Top X ranking of X metrics for X criteria.

## Solution
It is important to note it is made of 3 types of code:
* The derived table
* Its corresponding dynamic join
* A mapping metric to simplify the code’s join

### DERIVED TABLE

```lookml
view: sdt_top_x_of_x {
  # label: "Title you want - it can be an existing view"
  derived_table: {
    #parameter value specifies which of the rankings from the inner table to use
    sql:
      select {% parameter ranking_metric %} as RankingMetric,
      {% parameter ranking_criteria %} as RankingCriteria
      from
      (
        select {% parameter ranking_metric %},
        --metric to rank over is set by the user's ranking_criteria parameter selection
        rank() over(order by count(*) desc) as RankOrderItemCount,
        rank() over(order by sum(fact_internet_sale.SalesAmount) desc) as RankSalePrice,
        rank() over(order by avg(fact_internet_sale.SalesAmount) desc) as RankAvgSalePrice,
        rank() over(order by count(distinct fact_internet_sale.CustomerKey) desc) as RankDistinctUserCount
        FROM AdventureWorks.Products AS products
        LEFT JOIN AdventureWorks.FactInternetSale AS fact_internet_sale
          ON fact_internet_sale.ProductKey = products.ProductKey
        group by 1
      ) AS ranking_summary
    ;;
  }

  dimension: dimension_ranking_metric {
    hidden: yes
    type: string
    sql: ${TABLE}.RankingMetric ;;
  }

  parameter: ranking_metric {
    label: "Select the Metric you want to investigate 👉"
    description: "Choose a metric you would like to derive a Top X list for"
    type: unquoted
    default_value: "ProductCategory"
    suggest_dimension: products.list_suggestions

    # if you want a free text search then allowed_values are removed but they must be declared in your join's "top_x_ranking_metric_mapped" declared below
    # allowed_value: {
    #   label: "Product Category"
    #   value: "ProductCategory"
    # }
    # allowed_value: {
    #   label: "Product Color"
    #   value: "ProductColor"
    # }
    # allowed_value: {
    #   label: "Product Line"
    #   value: "ProductLine"
    # }
    # allowed_value: {
    #   label: "Product Name"
    #   value: "ProductName"
    # }
  }

  parameter: ranking_criteria {
    label: "Select how it should be ranked 👉"
    description: "Specify based on what criteria your want to rank your metric by"
    type: unquoted
    #Set a default value so that the dynamic ranking still works even if the user doesn't use the parameter.
    #Parameter default values work better without underscores, otherwise they sometimes load as '' when added, rather than with the corresponding label.
    default_value: "RankOrderItemCount"

    allowed_value: {
      label: "Number of order items sold"
      value: "RankOrderItemCount"
    }
    allowed_value: {
      label: "Total sales"
      value: "RankSalePrice"
    }
    allowed_value: {
      label: "Average sale price"
      value: "RankAvgSalePrice"
    }
    allowed_value: {
      label: "Number of distinct customers"
      value: "RankDistinctUserCount"
    }
  }

  parameter: ranking_limit {
    label: "Select Ranking limit 👉"
    type: unquoted
    default_value: "5"

    allowed_value: {
      label: "Top 1"
      value: "1"
    }
    allowed_value: {
      label: "Top 2"
      value: "2"
    }
    allowed_value: {
      label: "Top 5"
      value: "5"
    }
    allowed_value: {
      label: "Top 10"
      value: "10"
    }
    allowed_value: {
      label: "Top 20"
      value: "20"
    }
    allowed_value: {
      label: "Top 50"
      value: "50"
    }
  }

  dimension: ranking_id {
    #Adjust the label that appears in visualization to match the ranking criteria
    label: "Ranking ID"
    type: string
    sql: CASE WHEN ${TABLE}.RankingCriteria<={% parameter ranking_limit %} then cast(${TABLE}.RankingCriteria as STRING)
         else Null
         end ;;
  }

  dimension: top_X_ranking_metric {
    label: "Dynamic Top X metric"
    label_from_parameter: ranking_metric
    primary_key: yes
    type: string
    sql: CASE WHEN ${TABLE}.RankingCriteria<={% parameter ranking_limit %} then ${TABLE}.RankingMetric
         Else NULL
         end ;;
  }

  measure: dynamic_value {
    label: "Dynamic Top X value"
    label_from_parameter: ranking_criteria
    type: number
    sql:
        {% if ranking_criteria._parameter_value == "RankOrderItemCount" %}
        ${fact_internet_sale.count}
        {% elsif ranking_criteria._parameter_value == "RankSalePrice" %}
        ${fact_internet_sale.sum_sales_amount}
        {% elsif ranking_criteria._parameter_value == "RankAvgSalePrice" %}
        ${fact_internet_sale.avg_sales_amount}
        {% elsif ranking_criteria._parameter_value == "RankDistinctUserCount" %}
        ${fact_internet_sale.count_customer_key}
        {% else %} ${fact_internet_sale.sum_sales_amount}
        {% endif %}
        ;;
    html:
        {% if ranking_criteria._parameter_value == "RankOrderItemCount" %}
        {{ fact_internet_sale.count._rendered_value }}
        {% elsif ranking_criteria._parameter_value == "RankSalePrice" %}
        {{ fact_internet_sale.sum_sales_amount._rendered_value }}
        {% elsif ranking_criteria._parameter_value == "RankAvgSalePrice" %}
        {{ fact_internet_sale.avg_sales_amount._rendered_value }}
        {% elsif ranking_criteria._parameter_value == "RankDistinctUserCount" %}
        {{ fact_internet_sale.count_customer_key._rendered_value }}
        {% else %} {{ fact_internet_sale.sum_sales_amount._rendered_value }}
        {% endif %}
        ;;
  }
}
```

### MODEL FILE

```lookml
connection: "poc_2024"

include: "/views/*.view.lkml"

explore: fact_internet_sale {

  persist_with: default_caching_policy
  label: "📊 Investment tool"

  join: products {
    relationship: many_to_one
    sql_on: ${products.product_key} = ${fact_internet_sale.product_key} ;;
  }

  join: sdt_top_x_of_x {
    view_label: "Top X of Any metric"
    type: left_outer
    relationship: many_to_one
    sql_on: ${products.top_x_ranking_metric_mapped} = ${sdt_top_x_of_x.top_x_ranking_metric} ;;
  }
}
```

### VIEW FILE (on which the derived table metrics parameter is based)

```lookml
view: products {
  sql_table_name: `cacib-data-analytics-sbox-2095.AdventureWorks.Products` ;;

  dimension: product_name {
    type: string
    sql: ${TABLE}.ProductName ;;
  }

  dimension: product_category {
    type: string
    sql: ${TABLE}.ProductCategory ;;
  }

  dimension: product_color {
    type: string
    sql: ${TABLE}.ProductColor ;;
  }

  dimension: product_line {
    type: string
    sql: ${TABLE}.ProductLine ;;
  }

  dimension: product_model_name {
    type: string
    sql: ${TABLE}.ProductModelName ;;
  }

  # The metric below should rather refer to a JSON file per client that we could
  # then easily unest based on the user logging in
  dimension: list_suggestions {
    label: "List of Suggestions"
    type: string
    sql: ${sub_category} ;;
    full_suggestions: yes
  }

  # built in flexibility of free text interpretation as this could become handy
  # IF the derived table was as flexible (WIP)
  dimension: top_x_ranking_metric_mapped {
    sql:
        {% assign ranking_metric_lower = sdt_top_x_of_x.ranking_metric._parameter_value | downcase %}

        {% if ranking_metric_lower contains "product name" or ranking_metric_lower contains "productname" %}
        ${product_name}
        {% elsif ranking_metric_lower contains "product category" or ranking_metric_lower contains "productcategory" %}
        ${product_category}
        {% elsif ranking_metric_lower contains "sub category" or ranking_metric_lower contains "sub-category" or ranking_metric_lower contains "subcategory" %}
        ${sub_category}
        {% elsif ranking_metric_lower contains "product color" or ranking_metric_lower contains "productcolor" or ranking_metric_lower contains "color" %}
        ${product_color}
        {% elsif ranking_metric_lower contains "product line" or ranking_metric_lower contains "productline" or ranking_metric_lower contains "line" %}
        ${product_line}
        {% elsif ranking_metric_lower contains "product model name" or ranking_metric_lower contains "productmodelname" or ranking_metric_lower contains "model_name" or ranking_metric_lower contains "model" %}
        ${product_model_name}
        {% else %}
        ${product_name}
        {% endif %}
        ;;
  }
}
```

## Tips to consider
* If you want a free text search for your metric parameter then `allowed_values` must be removed from your derived table parameter
* Set a default value for your criteria parameter so that the dynamic ranking still works even if the user doesn't use the parameter.
* Parameter default values work better without underscores, otherwise they sometimes load as '' when added, rather than with the corresponding label.

## Pitfalls to consider
* Persisting would be counterproductive for such a dynamic Top X as it will be refreshed often
* The `binding_all_filters` parameter may be a reason to prioritize the native derived table approach rather than the SQL derived table
