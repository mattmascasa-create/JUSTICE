"""
Blockchain Anchoring Service (STUBBED)

This service provides a stubbed interface for blockchain anchoring.
Real blockchain functionality requires web3 dependencies which are not
available in the deployment environment.

To enable real blockchain anchoring:
1. Install web3 and eth-account packages locally
2. Configure POLYGON_RPC_URL and POLYGON_PRIVATE_KEY environment variables
3. Replace this stub with the full implementation
"""

import os
import hashlib
from datetime import datetime, timezone
from typing import Optional, Dict, Any


class BlockchainAnchoringService:
    """
    Stubbed Blockchain Anchoring Service
    
    This is a placeholder that simulates blockchain anchoring responses.
    Real blockchain anchoring is not available in the current deployment.
    """
    
    def __init__(self):
        self.initialized = False
        self.stub_mode = True
    
    def is_available(self) -> bool:
        """Check if blockchain anchoring is available"""
        return False
    
    def get_status(self) -> Dict[str, Any]:
        """Get service status"""
        return {
            "available": False,
            "mode": "stubbed",
            "message": "Blockchain anchoring is not configured. Contact support to enable.",
            "network": "none"
        }
    
    def anchor_hash(self, evidence_hash: str, metadata: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Stub for anchoring a hash to the blockchain.
        Returns a simulated response.
        """
        # Generate a fake transaction hash for demo purposes
        fake_tx_hash = hashlib.sha256(
            f"{evidence_hash}{datetime.now(timezone.utc).isoformat()}".encode()
        ).hexdigest()
        
        return {
            "success": False,
            "stubbed": True,
            "message": "Blockchain anchoring is not available in this deployment",
            "simulated_tx_hash": f"0x{fake_tx_hash}",
            "evidence_hash": evidence_hash,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "note": "This is a simulated response. Enable blockchain support for real anchoring."
        }
    
    def verify_hash(self, tx_hash: str) -> Dict[str, Any]:
        """
        Stub for verifying a hash on the blockchain.
        """
        return {
            "success": False,
            "stubbed": True,
            "message": "Blockchain verification is not available in this deployment",
            "tx_hash": tx_hash
        }
    
    def get_transaction(self, tx_hash: str) -> Optional[Dict[str, Any]]:
        """
        Stub for getting transaction details.
        """
        return None
    
    def estimate_gas(self, data_size: int = 32) -> Dict[str, Any]:
        """
        Stub for estimating gas costs.
        """
        return {
            "available": False,
            "message": "Gas estimation not available - blockchain not configured"
        }


# Singleton instance
blockchain_service = BlockchainAnchoringService()


def get_blockchain_service() -> BlockchainAnchoringService:
    """Get the blockchain anchoring service instance"""
    return blockchain_service
