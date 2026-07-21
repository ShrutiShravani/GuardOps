{
  "LLM_Response_Node": [
    {
      "metric_key": "quoted_price",
      "strategy": "DATA_OVERRIDE",
      "checks": [
        {
          "condition_type": "UNDER_FLOOR",
          "boundary_limit": 499.0,
          "fallback_value": 499.0,
          "breach_tag": "PRICE_BELOW_FLOOR",
          "parameters": {}
        }
      ]
    },
    {
      "metric_key": "discount_pct",
      "strategy": "DATA_OVERRIDE",
      "checks": [
        {
          "condition_type": "OVER_CEILING",
          "boundary_limit": 20.0,
          "fallback_value": 20.0,
          "breach_tag": "DISCOUNT_OVER_CAP",
          "parameters": {}
        }
      ]
    },
    {
      "metric_key": "reply",
      "strategy": "DATA_OVERRIDE",
      "checks": [
        {
          "condition_type": "CUSTOM_CHECK",
          "boundary_limit": "custom_guards.check_competitor_mention",
          "fallback_value": "custom_guards.recover_competitor_deflection",
          "breach_tag": "COMPETITOR_MENTIONED",
          "parameters": {
            "competitors": ["salesforce", "hubspot", "pipedrive", "zoho", "monday"]
          }
        }
      ]
    },
    {
      "metric_key": "reply",
      "strategy": "SHORT_CIRCUIT",
      "checks": [
        {
          "condition_type": "CUSTOM_CHECK",
          "boundary_limit": "custom_guards.check_unshipped_feature",
          "fallback_value": "I would love to share more details — let me have the right person follow up with you directly on that.",
          "breach_tag": "UNSHIPPED_FEATURE_PROMISED",
          "parameters": {
            "unshipped_phrases": [
              "ships next week",
              "coming soon",
              "launching next month",
              "in beta",
              "on the roadmap"
            ]
          }
        }
      ]
    }
  ]
}
