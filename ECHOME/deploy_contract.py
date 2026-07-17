import json
import os
from web3 import Web3
from solcx import compile_standard, install_solc
from django.conf import settings

# --------------------------
# Django setup
# --------------------------

# os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ECHOME.settings')

# Load credentials from Django settings

PRIVATE_KEY = settings.PRIVATE_KEY
WALLET_ADDRESS = settings.WALLET_ADDRESS
ENDPOINT = settings.RPC_ENDPOINT

if not PRIVATE_KEY:
    raise ValueError("No PRIVATE_KEY found in Django settings")
if not WALLET_ADDRESS:
    raise ValueError("No WALLET_ADDRESS found in Django settings")

# --------------------------
# Solidity compiler
# --------------------------
# Install the latest stable 0.8.x compiler
install_solc("0.8.0")

# --------------------------
# Web3 setup
# --------------------------
w3 = Web3(Web3.HTTPProvider(ENDPOINT))
if not w3.is_connected():
    raise ConnectionError("Failed to connect to SKALE network")

print(f"Connected to chain ID: {w3.eth.chain_id}")

# --------------------------
# Load contract source
# --------------------------
current_dir = os.path.dirname(os.path.abspath(__file__))
file_path = os.path.join(current_dir, "contract.sol")

with open(file_path, "r", encoding="utf-8") as f:
    contract_source_code = f.read()

# --------------------------
# Compile contract
# --------------------------
compiled_sol = compile_standard(
    {
        "language": "Solidity",
        "sources": {
            SOURCE_FILE: {"content": contract_source_code}
        },
        "settings": {
            "outputSelection": {
                "*": {
                    "*": ["abi", "metadata", "evm.bytecode", "evm.sourceMap"]
                }
            }
        },
    },
    solc_version="0.8.20",
)

# Access contract data
contract_name = "ExpirableStorage"  # <--- update if you rename the contract
contract_data = compiled_sol["contracts"][SOURCE_FILE][contract_name]

bytecode = contract_data["evm"]["bytecode"]["object"]
abi = contract_data["abi"]

# --------------------------
# Deploy contract
# --------------------------
Contract = w3.eth.contract(abi=abi, bytecode=bytecode)

nonce = w3.eth.get_transaction_count(WALLET_ADDRESS)

print("Estimating gas...")
gas_estimate = Contract.constructor().estimate_gas({"from": WALLET_ADDRESS})
print(f"Gas estimate: {gas_estimate}")
gas_price = w3.eth.gas_price
print(f"Using gas price: {gas_price}")

transaction = Contract.constructor().build_transaction({
    "chainId": w3.eth.chain_id,
    "gas": gas_estimate + 500000,   # add buffer
    "gasPrice": gas_price,                  # SKALE gas is free
    "nonce": nonce,
    "from": WALLET_ADDRESS,
})

# Sign & send
signed_txn = w3.eth.account.sign_transaction(transaction, private_key=PRIVATE_KEY)
tx_hash = w3.eth.send_raw_transaction(signed_txn.rawTransaction)

print(f"Transaction hash: {tx_hash.hex()}")
print("Waiting for confirmation...")

tx_receipt = w3.eth.wait_for_transaction_receipt(tx_hash)

if tx_receipt["status"] == 1:
    print(f"Contract deployed successfully at: {tx_receipt.contractAddress}")
else:
    print(" Contract deployment failed")

# --------------------------
# Save contract info
# --------------------------
contract_info = {
    "contract_address": tx_receipt.contractAddress,
    "abi": abi
}

with open("contract_info.json", "w") as f:
    json.dump(contract_info, f, indent=4)

print("Contract info saved to contract_info.json")
