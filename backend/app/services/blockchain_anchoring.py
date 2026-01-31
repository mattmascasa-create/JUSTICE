"""
Blockchain Anchoring Service
Submits evidence hash roots to Polygon blockchain for permanent, tamper-proof verification.
"""
import os
import json
import hashlib
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from web3 import Web3
from eth_account import Account

# Polygon RPC endpoints
POLYGON_MAINNET_RPC = "https://polygon-rpc.com"
POLYGON_MUMBAI_RPC = "https://rpc-mumbai.maticvigil.com"

# Use testnet by default, switch to mainnet for production
POLYGON_RPC = os.environ.get("POLYGON_RPC_URL", POLYGON_MUMBAI_RPC)
POLYGON_PRIVATE_KEY = os.environ.get("POLYGON_PRIVATE_KEY", "")
POLYGON_NETWORK = os.environ.get("POLYGON_NETWORK", "mumbai")  # 'mumbai' or 'mainnet'

# Chain IDs
CHAIN_IDS = {
    "mumbai": 80001,
    "mainnet": 137
}


class BlockchainAnchoringService:
    """Service for anchoring evidence hashes to Polygon blockchain"""
    
    def __init__(self):
        self.web3 = None
        self.account = None
        self.initialized = False
        self._initialize()
    
    def _initialize(self):
        """Initialize Web3 connection"""
        try:
            self.web3 = Web3(Web3.HTTPProvider(POLYGON_RPC))
            
            if not self.web3.is_connected():
                print("BlockchainAnchor: Failed to connect to Polygon RPC")
                return
            
            if POLYGON_PRIVATE_KEY:
                self.account = Account.from_key(POLYGON_PRIVATE_KEY)
                print(f"BlockchainAnchor: Initialized with address {self.account.address}")
            else:
                print("BlockchainAnchor: No private key configured - anchoring disabled")
            
            self.initialized = True
            print(f"BlockchainAnchor: Connected to Polygon {POLYGON_NETWORK}")
            
        except Exception as e:
            print(f"BlockchainAnchor: Initialization error: {e}")
    
    def is_available(self) -> bool:
        """Check if blockchain anchoring is available"""
        return self.initialized and self.account is not None
    
    def get_balance(self) -> float:
        """Get MATIC balance of the anchoring wallet"""
        if not self.is_available():
            return 0.0
        
        try:
            balance_wei = self.web3.eth.get_balance(self.account.address)
            return float(self.web3.from_wei(balance_wei, 'ether'))
        except Exception as e:
            print(f"BlockchainAnchor: Error getting balance: {e}")
            return 0.0
    
    def create_merkle_root(self, hashes: list) -> str:
        """
        Create a Merkle root from a list of evidence hashes.
        This allows anchoring multiple evidence items in a single transaction.
        """
        if not hashes:
            return ""
        
        # Sort hashes for deterministic ordering
        sorted_hashes = sorted(hashes)
        
        # Build Merkle tree
        current_level = [h.encode() if isinstance(h, str) else h for h in sorted_hashes]
        
        while len(current_level) > 1:
            next_level = []
            for i in range(0, len(current_level), 2):
                left = current_level[i]
                right = current_level[i + 1] if i + 1 < len(current_level) else left
                combined = hashlib.sha256(left + right).digest()
                next_level.append(combined)
            current_level = next_level
        
        return current_level[0].hex() if current_level else ""
    
    async def anchor_evidence(
        self,
        encounter_id: str,
        evidence_hashes: list,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Anchor evidence hashes to Polygon blockchain.
        
        Args:
            encounter_id: The encounter ID
            evidence_hashes: List of SHA-256 hashes to anchor
            metadata: Optional metadata to include
            
        Returns:
            Dict with transaction details and proof
        """
        if not self.is_available():
            return {
                "success": False,
                "error": "Blockchain anchoring not configured",
                "fallback": True
            }
        
        try:
            # Create Merkle root of all evidence hashes
            merkle_root = self.create_merkle_root(evidence_hashes)
            
            # Create the data payload
            anchor_data = {
                "type": "JUSTICE_EVIDENCE_ANCHOR",
                "version": "1.0",
                "encounter_id": encounter_id,
                "merkle_root": merkle_root,
                "hash_count": len(evidence_hashes),
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "network": POLYGON_NETWORK
            }
            
            if metadata:
                anchor_data["metadata"] = metadata
            
            # Convert to hex for transaction data
            data_json = json.dumps(anchor_data, separators=(',', ':'))
            data_hex = '0x' + data_json.encode().hex()
            
            # Build transaction (self-transfer with data)
            nonce = self.web3.eth.get_transaction_count(self.account.address)
            gas_price = self.web3.eth.gas_price
            
            # Estimate gas (data transactions are cheap)
            estimated_gas = 21000 + (len(data_hex) // 2 * 16)  # Base + data cost
            
            tx = {
                'nonce': nonce,
                'to': self.account.address,  # Self-transfer
                'value': 0,
                'gas': estimated_gas + 10000,  # Buffer
                'gasPrice': gas_price,
                'data': data_hex,
                'chainId': CHAIN_IDS.get(POLYGON_NETWORK, 80001)
            }
            
            # Sign and send transaction
            signed_tx = self.web3.eth.account.sign_transaction(tx, POLYGON_PRIVATE_KEY)
            tx_hash = self.web3.eth.send_raw_transaction(signed_tx.rawTransaction)
            tx_hash_hex = tx_hash.hex()
            
            # Wait for confirmation (with timeout)
            try:
                receipt = self.web3.eth.wait_for_transaction_receipt(tx_hash, timeout=60)
                confirmed = receipt.status == 1
                block_number = receipt.blockNumber
            except Exception as e:
                print(f"BlockchainAnchor: Receipt timeout: {e}")
                confirmed = False
                block_number = None
            
            # Build explorer URL
            if POLYGON_NETWORK == "mainnet":
                explorer_url = f"https://polygonscan.com/tx/{tx_hash_hex}"
            else:
                explorer_url = f"https://mumbai.polygonscan.com/tx/{tx_hash_hex}"
            
            return {
                "success": True,
                "transaction_hash": tx_hash_hex,
                "merkle_root": merkle_root,
                "block_number": block_number,
                "confirmed": confirmed,
                "network": POLYGON_NETWORK,
                "explorer_url": explorer_url,
                "gas_used": receipt.gasUsed if confirmed else None,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "anchor_data": anchor_data
            }
            
        except Exception as e:
            print(f"BlockchainAnchor: Anchoring error: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def verify_anchor(self, tx_hash: str) -> Dict[str, Any]:
        """
        Verify an existing blockchain anchor by retrieving the transaction.
        
        Args:
            tx_hash: The transaction hash to verify
            
        Returns:
            Dict with verification details
        """
        if not self.web3 or not self.web3.is_connected():
            return {"success": False, "error": "Not connected to blockchain"}
        
        try:
            # Get transaction
            tx = self.web3.eth.get_transaction(tx_hash)
            if not tx:
                return {"success": False, "error": "Transaction not found"}
            
            # Get receipt for confirmation status
            receipt = self.web3.eth.get_transaction_receipt(tx_hash)
            
            # Decode data
            data_hex = tx.input
            if data_hex and data_hex != '0x':
                try:
                    data_bytes = bytes.fromhex(data_hex[2:])
                    anchor_data = json.loads(data_bytes.decode())
                except:
                    anchor_data = {"raw": data_hex}
            else:
                anchor_data = None
            
            # Get block info
            block = self.web3.eth.get_block(tx.blockNumber)
            block_timestamp = datetime.fromtimestamp(block.timestamp, tz=timezone.utc)
            
            return {
                "success": True,
                "verified": True,
                "transaction_hash": tx_hash,
                "block_number": tx.blockNumber,
                "block_timestamp": block_timestamp.isoformat(),
                "confirmed": receipt.status == 1,
                "confirmations": self.web3.eth.block_number - tx.blockNumber,
                "anchor_data": anchor_data,
                "from_address": tx['from'],
                "network": POLYGON_NETWORK
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}


# Singleton instance
blockchain_service = BlockchainAnchoringService()


# Helper functions for router use
async def anchor_encounter_evidence(encounter_id: str, hashes: list, metadata: dict = None):
    """Anchor encounter evidence to blockchain"""
    return await blockchain_service.anchor_evidence(encounter_id, hashes, metadata)


def verify_blockchain_anchor(tx_hash: str):
    """Verify a blockchain anchor"""
    return blockchain_service.verify_anchor(tx_hash)


def is_blockchain_available():
    """Check if blockchain service is available"""
    return blockchain_service.is_available()


def get_wallet_balance():
    """Get anchoring wallet balance"""
    return blockchain_service.get_balance()
