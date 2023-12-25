# Use the official Ethereum Geth image as the base image
FROM ethereum/client-go:latest

# Set the work directory
WORKDIR /ethereum

# Expose RPC port and API
EXPOSE 8545

# Start Geth in light mode with specified RPC settings
CMD ["geth", "--syncmode", "light", "--rpc", "--rpcaddr", "0.0.0.0", "--rpcport", "8545", "--rpcapi", "eth,net,web3"]