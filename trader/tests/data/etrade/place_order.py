# pylint: skip-file
PLACE_ORDER_RESPONSE = {
    "PlaceOrderResponse": {
        "orderType": "EQ",
        "dstFlag": False,
        "optionLevelCd": 2,
        "marginLevelCd": "MARGIN_TRADING_NOT_ALLOWED",
        "placedTime": 1582555141165,
        "accountId": "45249801",
        "Order": [
            {
                "orderTerm": "GOOD_FOR_DAY",
                "priceType": "STOP_LIMIT",
                "limitPrice": 0.202,
                "stopPrice": 0.204,
                "marketSession": "REGULAR",
                "allOrNone": False,
                "messages": {
                    "Message": [
                        {
                            "description": "200|Your order was successfully entered during market hours.",
                            "code": 1026,
                            "type": "WARNING"
                        }
                    ]
                },
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
        "OrderIds": [
            {
                "orderId": 673
            }
        ]
    }
}
