# pylint: skip-file
PREVIEW_ORDER_RESPONSE = {
    "PreviewOrderResponse": {
        "orderType": "EQ",
        "totalOrderValue": -293.5349,
        "previewTime": 1582555140615,
        "dstFlag": False,
        "accountId": "45249801",
        "optionLevelCd": 2,
        "marginLevelCd": "MARGIN_TRADING_NOT_ALLOWED",
        "cashBpDetails": {
            "settled": {
                "currentBp": 301.44,
                "currentOor": 0.0,
                "currentNetBp": 301.44,
                "currentOrderImpact": 0.0,
                "netBp": 301.44
            },
            "settledUnsettled": {
                "currentBp": 301.44
            }
        },
        "Order": [
            {
                "orderTerm": "GOOD_FOR_DAY",
                "priceType": "STOP_LIMIT",
                "limitPrice": 0.202,
                "stopPrice": 0.204,
                "marketSession": "REGULAR",
                "allOrNone": False,
                "egQual": "EG_QUAL_NOT_AN_ELIGIBLE_SECURITY",
                "estimatedCommission": 0,
                "estimatedTotalAmount": -293.5349,
                "netPrice": 0,
                "netBid": 0,
                "netAsk": 0,
                "gcd": 0,
                "ratio": "",
                "Instrument": [
                    {
                        "symbolDescription": "TOUGHBUILT INDUSTRIES INC COM",
                        "orderAction": "SELL",
                        "quantityType": "QUANTITY",
                        "quantity": 1454,
                        "cancelQuantity": 0.0,
                        "reserveOrder": True,
                        "reserveQuantity": 0.0,
                        "Product": {
                            "symbol": "TBLT",
                            "securityType": "EQ"
                        }
                    }
                ]
            }
        ],
        "PreviewIds": [
            {
                "previewId": 266606056106
            }
        ],
        "Disclosure": {
            "ehDisclosureFlag": True,
            "ahDisclosureFlag": False,
            "conditionalDisclosureFlag": True,
            "aoDisclosureFlag": False
        }
    }
}
