import datetime
import etherscan
from web3 import Web3
from os import getenv


def captureBlockTransactions():
    global capturedLastBlockNumber, contractAddress
    with open("capturedTransactionHashes.txt", "a") as captured:
        if (capturedLastBlockNumber != w3.eth.block_number):
            capturedLastBlockNumber = w3.eth.block_number  # This is for buffering purposes
            printDev("Capturing last block of transactions...", end="")
            capturedTransactions = w3.eth.get_block(capturedLastBlockNumber, full_transactions=True).transactions
            if (len(capturedTransactions) > 0):
                printDev(f"Captured {len(capturedTransactions)} transactions [Block {capturedLastBlockNumber}]", newLine=False)
                for tx in capturedTransactions:
                    if (tx.to and tx.to.lower() != contractAddress.lower()):
                        continue
                    if (tx.input[0:4].hex() == "0x7a4e5cd2"):
                        functionName = "BUY"
                    elif (tx.input[0:4].hex() == "0x23f4e1ee"):
                        functionName = "SELL"
                    else:
                        functionName = tx.input[0:4].hex()
                        continue
                        
                    swapLogs = [log for log in client.get_proxy_transaction_receipt(tx.hash.hex())["logs"] if len(log["data"]) == 258]
                    if (len(swapLogs) > 0):
                        printDev(f"\tTransaction {tx.hash.hex()} {len(swapLogs)} swaps were made")
                        for log in swapLogs:
                            #pdb.set_trace()
                            uniswapPair = w3.eth.contract(address=w3.to_checksum_address(log['address']), abi=pairABI)
                            token0 = w3.eth.contract(address=w3.to_checksum_address(uniswapPair.functions.token0().call()), abi=tokenABI)
                            token1 = w3.eth.contract(address=w3.to_checksum_address(uniswapPair.functions.token1().call()), abi=tokenABI)  # token1 es WETH
                            reserves_after = uniswapPair.functions.getReserves().call()
                            if (functionName == "BUY"):
                                processBuyTransactionSwap(captured, tx, log, tokenOut=token0, tokenIn=token1, reserves=reserves_after)
                            else:
                                processSellTransactionSwap(captured, tx, log, tokenOut=token1, tokenIn=token0, reserves=reserves_after)
            else:
                printDev(f"No transactions where captured [Block {capturedLastBlockNumber}]")

def processBuyTransactionSwap(file, tx, log, tokenOut, tokenIn, reserves):
    amount_out = int(log["data"][130:130+64], 16)
    amount_in = int(log["data"][66:130], 16)
    tokenOutSymbol = tokenOut.functions.symbol().call()
    tokenInSymbol = tokenIn.functions.symbol().call()
    if (tokenOutSymbol == "WETH"):
        eth_amount = amount_out / 1e18
    elif (tokenInSymbol == "WETH"):  #deberia ser el caso
        eth_amount = amount_in / 1e18
    else:
        eth_amount = "NotFound"
    multiplier = 10**(tokenOut.functions.decimals().call() - tokenIn.functions.decimals().call())  # ver si esto no es mejor meterlo en los if porque capaz depende del orden
    file.write(f"{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')},BUY,{tx.hash.hex()},{tokenInSymbol},{tokenOutSymbol},{eth_amount/(multiplier*amount_out)},{eth_amount},{tx.gas},{tx.gasPrice},{reserves[:2]}\n")
    printDev("\t########### CAPTURED FILE WRITTEN ###########")

def processSellTransactionSwap(file, tx, log, tokenOut, tokenIn, reserves):
    amount_out = int(log["data"][194:], 16)
    amount_in = int(log["data"][2:66], 16)
    tokenOutSymbol = tokenOut.functions.symbol().call()
    tokenInSymbol = tokenIn.functions.symbol().call()
    if (tokenOutSymbol == "WETH"):  #deberia ser el caso
        eth_amount = amount_out / 1e18
    elif (tokenInSymbol == "WETH"):
        eth_amount = amount_in / 1e18
    else:
        eth_amount = "NotFound"
    multiplier = 10**(tokenOut.functions.decimals().call() - tokenIn.functions.decimals().call())  # ver si esto no es mejor meterlo en los if porque capaz depende del orden
    file.write(f"{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')},SELL,{tx.hash.hex()},{tokenInSymbol},{tokenOutSymbol},{(multiplier*eth_amount)/amount_in},{eth_amount},{tx.gas},{tx.gasPrice},{reserves[:2]}\n")
    printDev("\t########### CAPTURED FILE WRITTEN ###########")

def printDev(message, newLine=True, end="\n"):
    global LOG_TO_FILE, LOG_TO_CONSOLE
    prefix = f"[{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')}] " if newLine else ""
    if LOG_TO_FILE:
        with open("logs.txt", "a") as f:
            f.write(f"{prefix}{message}\n")
    if LOG_TO_CONSOLE:
        print(f"{prefix}{message}", end=end)

def initializeFile(file_name, initial_line):
    try:
        with open(file_name, 'r') as file:
            pass
    except FileNotFoundError:
        with open(file_name, 'w') as file:
            file.write(initial_line + '\n')
            printDev(f"File '{file_name}' created.")

if __name__ == "__main__":
    LOG_TO_CONSOLE = False
    LOG_TO_FILE = True

    initializeFile("capturedTransactionHashes.txt", "time,function,tx_hash,tokenIn,tokenOut,execution_price,eth_amount,gas,gas_price,reserves_after")
    initializeFile("pendingTransactionHashes.txt", "time,tx_hash,tx_to,captured_timestamp,grace_period")

    printDev("Initiating Web3 client...")
    rpc_url = "http://ethereum-node:8545"
    w3 = Web3(Web3.HTTPProvider(rpc_url))

    printDev("Initiating etherscan client...")
    api_key = getenv("ETHERSCAN_API_KEY")
    client = etherscan.Etherscan(api_key=api_key)

    tokenABI = [{"constant": True,"inputs":[],"name":"symbol","outputs":[{"name":"","type":"string"}],"payable": False,"stateMutability":"view","type":"function"},
                {"constant": True,"inputs":[],"name":"decimals","outputs":[{"name":"","type":"uint8"}],"payable": False,"stateMutability":"view","type":"function"}]
    pairABI = [{"constant": True, "inputs": [], "name": "token0", "outputs": [{"internalType": "address", "name": "", "type": "address"}], "payable": False, "stateMutability": "view", "type": "function"},
               {"constant": True, "inputs": [], "name": "token1", "outputs": [{"internalType": "address", "name": "", "type": "address"}], "payable": False, "stateMutability": "view", "type": "function"},
               {"constant": True,"inputs":[],"name":"getReserves","outputs":[{"internalType":"uint112","name":"_reserve0","type":"uint112"},{"internalType":"uint112","name":"_reserve1","type":"uint112"},{"internalType":"uint32","name":"_blockTimestampLast","type":"uint32"}],"payable": False,"stateMutability":"view","type":"function"}]
    UniswapV2Router02 = w3.eth.contract(address=getenv("UNISWAPV2ROUTER_CONTRACT_ADDRESS"), abi=[{"inputs":[{"internalType":"uint256","name":"amountOut","type":"uint256"},{"internalType":"address[]","name":"path","type":"address[]"}],"name":"getAmountsIn","outputs":[{"internalType":"uint256[]","name":"amounts","type":"uint256[]"}],"stateMutability":"view","type":"function"}])
    contractAddress = getenv("ADDRESS_TO_TRACK")
    
    pendingMatchingTransactions = set({})
    pendingBlockNumber = w3.eth.block_number + 1
    capturedLastBlockNumber = 0

    printDev("Scanning has begun!")
    while True:
        try:
            captureBlockTransactions()
        except Exception as e:
            pendingMatchingTransactions = set({})
            pendingBlockNumber = w3.eth.block_number + 1
            capturedLastBlockNumber = 0
            printDev(f"Exception caught: {e}")