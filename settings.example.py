# Listener
DELAY = 10

NETWORK_ID = 4

NETWORKS = {
    4: {
        "NODE_URL": "wss://rinkeby.infura.io/ws/v3/xxx",
        "ETH_CONTRACT": {
            "abi": "../contracts/ContractETH.json",
            "address": "0xxxxx",
            "tracked_event_names": ['CustomEvent1', 'CustomeEvent2']
        },
        "USDT_CONTRACT": {
            "abi": "../contracts/ContractETH.json",
            "address": "0xxxxx",
            "tracked_event_names": ['CustomEvent1', 'CustomeEvent2']
        },
        'ADMIN': '0xxxxx'
    }
}
