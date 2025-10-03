from web3 import Web3
import json
import os
from datetime import datetime

print("🔗 Initializing CloudCred Blockchain Service...")

# LOCAL BLOCKCHAIN CONFIGURATION
BLOCKCHAIN_PROVIDER = "http://127.0.0.1:8545"
CHAIN_ID = 1337

# Hardhat test account (Account #0 - has 10,000 ETH)
PRIVATE_KEY = "0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80"

# Contract ABI - matches our Solidity contract
CONTRACT_ABI = [
    {
        "inputs": [
            {"internalType": "string", "name": "_invoiceId", "type": "string"},
            {"internalType": "address", "name": "_freelancer", "type": "address"},
            {"internalType": "address", "name": "_client", "type": "address"},
            {"internalType": "uint256", "name": "_amount", "type": "uint256"},
            {"internalType": "string", "name": "_description", "type": "string"}
        ],
        "name": "createInvoice",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function"
    },
    {
        "inputs": [
            {"internalType": "string", "name": "_invoiceId", "type": "string"}
        ],
        "name": "approveInvoice",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function"
    },
    {
        "inputs": [
            {"internalType": "string", "name": "_invoiceId", "type": "string"}
        ],
        "name": "getInvoice",
        "outputs": [
            {"internalType": "string", "name": "invoiceId", "type": "string"},
            {"internalType": "address", "name": "freelancer", "type": "address"},
            {"internalType": "address", "name": "client", "type": "address"},
            {"internalType": "uint256", "name": "amount", "type": "uint256"},
            {"internalType": "string", "name": "description", "type": "string"},
            {"internalType": "bool", "name": "approved", "type": "bool"},
            {"internalType": "uint256", "name": "createdAt", "type": "uint256"},
            {"internalType": "uint256", "name": "approvedAt", "type": "uint256"}
        ],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [
            {"internalType": "string", "name": "_invoiceId", "type": "string"}
        ],
        "name": "invoiceExists",
        "outputs": [
            {"internalType": "bool", "name": "", "type": "bool"}
        ],
        "stateMutability": "view",
        "type": "function"
    }
]

# Initialize Web3 connection
try:
    w3 = Web3(Web3.HTTPProvider(BLOCKCHAIN_PROVIDER))
    
    if w3.is_connected():
        print(f"✅ Connected to local blockchain: {BLOCKCHAIN_PROVIDER}")
        
        # Initialize account
        account = w3.eth.account.from_key(PRIVATE_KEY)
        balance = w3.eth.get_balance(account.address)
        print(f"✅ Account: {account.address}")
        print(f"✅ Balance: {w3.from_wei(balance, 'ether')} ETH")
        
        # Load contract address
        try:
            with open('contract_info.json', 'r') as f:
                contract_info = json.load(f)
                CONTRACT_ADDRESS = contract_info['address']
                print(f"✅ Contract loaded: {CONTRACT_ADDRESS}")
        except FileNotFoundError:
            print("❌ Contract not found. Make sure blockchain is running and contract is deployed.")
            CONTRACT_ADDRESS = None
            
    else:
        print("❌ Cannot connect to local blockchain")
        print("💡 Start Hardhat node: npx hardhat node")
        w3 = None
        account = None
        CONTRACT_ADDRESS = None
        
except Exception as e:
    print(f"❌ Blockchain initialization failed: {str(e)}")
    w3 = None
    account = None
    CONTRACT_ADDRESS = None

def get_contract():
    """Get smart contract instance"""
    if not w3 or not CONTRACT_ADDRESS:
        return None
    
    try:
        contract = w3.eth.contract(
            address=Web3.to_checksum_address(CONTRACT_ADDRESS),
            abi=CONTRACT_ABI
        )
        return contract
    except Exception as e:
        print(f"❌ Contract initialization failed: {str(e)}")
        return None

def create_invoice_on_chain(invoice_id, freelancer_email, client_email, amount, description):
    """Create invoice on blockchain - FREE on localhost!"""
    try:
        print(f"🔄 Creating invoice on blockchain...")
        print(f"   Invoice ID: {invoice_id}")
        print(f"   Amount: {amount}")
        print(f"   Freelancer: {freelancer_email}")
        print(f"   Client: {client_email}")
        
        if not w3 or not account:
            print("❌ Blockchain not connected")
            return {"success": False, "error": "Blockchain not connected"}
        
        contract = get_contract()
        if not contract:
            print("❌ Smart contract not available")
            return {"success": False, "error": "Smart contract not available"}
        
        # For demo: Use account address for both freelancer and client
        # In real app, users would have their own wallet addresses
        freelancer_address = account.address
        client_address = account.address
        
        # Convert amount to Wei (smallest unit)
        amount_wei = w3.to_wei(float(amount), 'ether')
        
        # Build transaction
        transaction = contract.functions.createInvoice(
            invoice_id,
            freelancer_address,
            client_address,
            amount_wei,
            description
        ).build_transaction({
            'from': account.address,
            'gas': 500000,
            'gasPrice': w3.to_wei('1', 'gwei'),
            'nonce': w3.eth.get_transaction_count(account.address),
            'chainId': CHAIN_ID
        })
        
        # Sign and send transaction
        signed_txn = w3.eth.account.sign_transaction(transaction, PRIVATE_KEY)
        tx_hash = w3.eth.send_raw_transaction(signed_txn.rawTransaction)
        
        # Wait for confirmation
        receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=60)
        
        print(f"✅ Invoice created on blockchain!")
        print(f"   Transaction: {receipt.transactionHash.hex()}")
        print(f"   Block: {receipt.blockNumber}")
        print(f"   Gas Used: {receipt.gasUsed}")
        
        return {
            "success": True,
            "transaction_hash": receipt.transactionHash.hex(),
            "block_number": receipt.blockNumber,
            "gas_used": receipt.gasUsed,
            "network": "localhost",
            "cost": "FREE! 🎉"
        }
        
    except Exception as e:
        print(f"❌ Blockchain invoice creation failed: {str(e)}")
        return {"success": False, "error": str(e)}

def approve_invoice_on_chain(invoice_id, client_id):
    """Approve invoice on blockchain - REAL IMPLEMENTATION!"""
    try:
        print(f"🔄 Approving invoice on blockchain...")
        print(f"   Invoice ID: {invoice_id}")
        print(f"   Client ID: {client_id}")
        
        if not w3 or not account:
            print("❌ Blockchain not connected")
            return {"success": False, "error": "Blockchain not connected"}
        
        contract = get_contract()
        if not contract:
            print("❌ Smart contract not available") 
            return {"success": False, "error": "Smart contract not available"}
        
        # Check if invoice exists
        try:
            exists = contract.functions.invoiceExists(invoice_id).call()
            if not exists:
                print("❌ Invoice not found on blockchain")
                return {"success": False, "error": "Invoice not found on blockchain"}
            
            # Get invoice details
            invoice_data = contract.functions.getInvoice(invoice_id).call()
            if invoice_data[5]:  # already approved
                print("⚠️ Invoice already approved")
                return {"success": False, "error": "Invoice already approved"}
            
            print(f"✅ Invoice found - Amount: {w3.from_wei(invoice_data[3], 'ether')} ETH")
            
        except Exception as e:
            print(f"❌ Invoice verification failed: {str(e)}")
            return {"success": False, "error": f"Invoice verification failed: {str(e)}"}
        
        # Build approval transaction
        transaction = contract.functions.approveInvoice(invoice_id).build_transaction({
            'from': account.address,
            'gas': 300000,
            'gasPrice': w3.to_wei('1', 'gwei'),
            'nonce': w3.eth.get_transaction_count(account.address),
            'chainId': CHAIN_ID
        })
        
        # Sign and send
        signed_txn = w3.eth.account.sign_transaction(transaction, PRIVATE_KEY)
        tx_hash = w3.eth.send_raw_transaction(signed_txn.rawTransaction)
        
        # Wait for confirmation
        receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=60)
        
        print(f"✅ Invoice approved on blockchain!")
        print(f"   Transaction: {receipt.transactionHash.hex()}")
        print(f"   Block: {receipt.blockNumber}")
        print(f"   Gas Used: {receipt.gasUsed}")
        
        return {
            "success": True,
            "transaction_hash": receipt.transactionHash.hex(),
            "block_number": receipt.blockNumber,
            "gas_used": receipt.gasUsed,
            "network": "localhost",
            "cost": "FREE! 🎉",
            "immutable": True
        }
        
    except Exception as e:
        print(f"❌ Blockchain approval failed: {str(e)}")
        return {"success": False, "error": str(e)}

def get_blockchain_status():
    """Get blockchain connection status"""
    if not w3:
        return {
            "connected": False,
            "error": "Web3 not initialized"
        }
    
    try:
        latest_block = w3.eth.block_number
        balance = w3.eth.get_balance(account.address) if account else 0
        
        return {
            "connected": w3.is_connected(),
            "provider": BLOCKCHAIN_PROVIDER,
            "network": "Hardhat Localhost",
            "chain_id": CHAIN_ID,
            "latest_block": latest_block,
            "account": account.address if account else None,
            "balance": f"{w3.from_wei(balance, 'ether')} ETH",
            "contract_address": CONTRACT_ADDRESS,
            "cost": "FREE! 🎉"
        }
        
    except Exception as e:
        return {
            "connected": False,
            "error": str(e)
        }

# Test connection on import
if __name__ == "__main__":
    print("🧪 Testing blockchain connection...")
    status = get_blockchain_status()
    print(f"Status: {json.dumps(status, indent=2)}")
else:
    # Quick connection test when imported
    if w3 and w3.is_connected():
        print("✅ Blockchain service ready!")
    else:
        print("⚠️ Blockchain not connected - check if hardhat node is running")