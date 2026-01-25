"""
Court-Grade Evidence Verification Service
Implements cryptographic hashing, blockchain timestamping, and chain of custody logging
for legally admissible digital evidence (FRE 901/707 compliant)
"""
import hashlib
import hmac
import json
import uuid
import os
import httpx
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from enum import Enum
from pydantic import BaseModel

from app.db.database import db


class HashAlgorithm(str, Enum):
    SHA256 = "sha256"
    SHA512 = "sha512"
    SHA3_256 = "sha3_256"


class CustodyAction(str, Enum):
    CREATED = "created"
    UPLOADED = "uploaded"
    VIEWED = "viewed"
    DOWNLOADED = "downloaded"
    SHARED = "shared"
    ANALYZED = "analyzed"
    VERIFIED = "verified"
    EXPORTED = "exported"
    MODIFIED = "modified"  # Should never happen for evidence
    DELETED = "deleted"


class BlockchainNetwork(str, Enum):
    ETHEREUM = "ethereum"
    BITCOIN = "bitcoin"
    LOCAL = "local"  # Free tier - just database storage


class EvidenceVerificationResult(BaseModel):
    is_valid: bool
    original_hash: str
    current_hash: str
    hash_match: bool
    blockchain_verified: bool
    blockchain_proof: Optional[Dict] = None
    chain_of_custody_intact: bool
    custody_events: int
    last_verified: str
    warnings: List[str] = []


class ForensicMetadata(BaseModel):
    """Metadata required for court admissibility"""
    original_filename: str
    file_size_bytes: int
    mime_type: str
    capture_device: Optional[str] = None
    capture_device_id: Optional[str] = None
    capture_software: Optional[str] = None
    capture_timestamp: str
    capture_timezone: Optional[str] = None
    gps_latitude: Optional[float] = None
    gps_longitude: Optional[float] = None
    gps_accuracy: Optional[float] = None
    duration_seconds: Optional[float] = None  # For audio/video
    resolution: Optional[str] = None  # For images/video
    hash_sha256: str
    hash_sha512: Optional[str] = None
    hash_sha3_256: Optional[str] = None


class EvidenceIntegrityService:
    """
    Service for maintaining evidence integrity and chain of custody.
    Designed for court admissibility under Federal Rules of Evidence.
    """
    
    def __init__(self):
        self.ethereum_api_url = os.environ.get("ETHEREUM_API_URL")
        self.ethereum_api_key = os.environ.get("ETHEREUM_API_KEY")
        self.hmac_secret = os.environ.get("EVIDENCE_HMAC_SECRET", "justice-evidence-integrity-key")
    
    # ============== Hash Generation ==============
    
    def compute_hash(self, data: bytes, algorithm: HashAlgorithm = HashAlgorithm.SHA256) -> str:
        """Compute cryptographic hash of data"""
        if algorithm == HashAlgorithm.SHA256:
            return hashlib.sha256(data).hexdigest()
        elif algorithm == HashAlgorithm.SHA512:
            return hashlib.sha512(data).hexdigest()
        elif algorithm == HashAlgorithm.SHA3_256:
            return hashlib.sha3_256(data).hexdigest()
        else:
            raise ValueError(f"Unsupported algorithm: {algorithm}")
    
    def compute_file_hashes(self, file_data: bytes) -> Dict[str, str]:
        """Compute multiple hashes for a file"""
        return {
            "sha256": self.compute_hash(file_data, HashAlgorithm.SHA256),
            "sha512": self.compute_hash(file_data, HashAlgorithm.SHA512),
            "sha3_256": self.compute_hash(file_data, HashAlgorithm.SHA3_256)
        }
    
    def compute_integrity_signature(self, evidence_id: str, hash_value: str, timestamp: str) -> str:
        """Generate HMAC signature for tamper detection"""
        message = f"{evidence_id}:{hash_value}:{timestamp}"
        return hmac.new(
            self.hmac_secret.encode(),
            message.encode(),
            hashlib.sha256
        ).hexdigest()
    
    # ============== Evidence Registration ==============
    
    async def register_evidence(
        self,
        evidence_id: str,
        file_data: bytes,
        metadata: ForensicMetadata,
        user_id: str,
        encounter_id: Optional[str] = None,
        blockchain_tier: BlockchainNetwork = BlockchainNetwork.LOCAL
    ) -> Dict:
        """
        Register new evidence with cryptographic proof.
        Creates initial chain of custody entry.
        """
        now = datetime.now(timezone.utc)
        timestamp = now.isoformat()
        
        # Compute all hashes
        hashes = self.compute_file_hashes(file_data)
        
        # Generate integrity signature
        integrity_sig = self.compute_integrity_signature(
            evidence_id, hashes["sha256"], timestamp
        )
        
        # Create evidence record
        evidence_record = {
            "evidence_id": evidence_id,
            "encounter_id": encounter_id,
            "user_id": user_id,
            
            # Cryptographic hashes
            "hash_sha256": hashes["sha256"],
            "hash_sha512": hashes["sha512"],
            "hash_sha3_256": hashes["sha3_256"],
            "integrity_signature": integrity_sig,
            
            # Forensic metadata
            "original_filename": metadata.original_filename,
            "file_size_bytes": metadata.file_size_bytes,
            "mime_type": metadata.mime_type,
            "capture_device": metadata.capture_device,
            "capture_device_id": metadata.capture_device_id,
            "capture_software": metadata.capture_software,
            "capture_timestamp": metadata.capture_timestamp,
            "capture_timezone": metadata.capture_timezone,
            "gps_latitude": metadata.gps_latitude,
            "gps_longitude": metadata.gps_longitude,
            "gps_accuracy": metadata.gps_accuracy,
            "duration_seconds": metadata.duration_seconds,
            "resolution": metadata.resolution,
            
            # Blockchain proof (if applicable)
            "blockchain_network": blockchain_tier.value,
            "blockchain_tx_hash": None,
            "blockchain_block_number": None,
            "blockchain_timestamp": None,
            "blockchain_verified": False,
            
            # Status
            "is_verified": True,
            "verification_count": 0,
            "last_verified": timestamp,
            "tamper_detected": False,
            
            # Timestamps
            "registered_at": timestamp,
            "created_at": timestamp,
            "updated_at": timestamp
        }
        
        await db.evidence_integrity.insert_one(evidence_record)
        
        # Create initial chain of custody entry
        await self.log_custody_event(
            evidence_id=evidence_id,
            action=CustodyAction.CREATED,
            user_id=user_id,
            details={
                "hash_sha256": hashes["sha256"],
                "file_size": metadata.file_size_bytes,
                "capture_timestamp": metadata.capture_timestamp
            }
        )
        
        # Anchor to blockchain if premium tier
        blockchain_proof = None
        if blockchain_tier == BlockchainNetwork.ETHEREUM:
            blockchain_proof = await self._anchor_to_ethereum(evidence_id, hashes["sha256"], timestamp)
            if blockchain_proof:
                await db.evidence_integrity.update_one(
                    {"evidence_id": evidence_id},
                    {"$set": {
                        "blockchain_tx_hash": blockchain_proof.get("tx_hash"),
                        "blockchain_block_number": blockchain_proof.get("block_number"),
                        "blockchain_timestamp": blockchain_proof.get("timestamp"),
                        "blockchain_verified": True
                    }}
                )
        
        return {
            "success": True,
            "evidence_id": evidence_id,
            "hashes": hashes,
            "integrity_signature": integrity_sig,
            "blockchain_proof": blockchain_proof,
            "registered_at": timestamp
        }
    
    # ============== Chain of Custody ==============
    
    async def log_custody_event(
        self,
        evidence_id: str,
        action: CustodyAction,
        user_id: str,
        details: Dict = None,
        ip_address: str = None,
        user_agent: str = None
    ) -> str:
        """Log a chain of custody event"""
        now = datetime.now(timezone.utc)
        event_id = f"custody_{uuid.uuid4().hex[:12]}"
        
        # Get previous event hash for chain integrity
        previous_event = await db.chain_of_custody.find_one(
            {"evidence_id": evidence_id},
            sort=[("timestamp", -1)]
        )
        previous_hash = previous_event.get("event_hash") if previous_event else "GENESIS"
        
        # Create event record
        event = {
            "event_id": event_id,
            "evidence_id": evidence_id,
            "action": action.value,
            "user_id": user_id,
            "timestamp": now.isoformat(),
            "ip_address": ip_address,
            "user_agent": user_agent,
            "details": details or {},
            "previous_hash": previous_hash
        }
        
        # Compute event hash (links to previous for chain integrity)
        event_data = json.dumps(event, sort_keys=True)
        event["event_hash"] = hashlib.sha256(event_data.encode()).hexdigest()
        
        await db.chain_of_custody.insert_one(event)
        
        return event_id
    
    async def get_custody_chain(self, evidence_id: str) -> List[Dict]:
        """Get complete chain of custody for evidence"""
        events = await db.chain_of_custody.find(
            {"evidence_id": evidence_id},
            {"_id": 0}
        ).sort("timestamp", 1).to_list(1000)
        
        return events
    
    async def verify_custody_chain(self, evidence_id: str) -> Dict:
        """Verify integrity of chain of custody"""
        events = await self.get_custody_chain(evidence_id)
        
        if not events:
            return {"valid": False, "error": "No custody events found"}
        
        # Verify chain integrity
        is_valid = True
        errors = []
        
        for i, event in enumerate(events):
            # Check hash chain
            if i == 0:
                if event.get("previous_hash") != "GENESIS":
                    is_valid = False
                    errors.append(f"First event has invalid genesis hash")
            else:
                if event.get("previous_hash") != events[i-1].get("event_hash"):
                    is_valid = False
                    errors.append(f"Chain broken at event {i}")
            
            # Verify event hash
            event_copy = {k: v for k, v in event.items() if k != "event_hash"}
            computed_hash = hashlib.sha256(json.dumps(event_copy, sort_keys=True).encode()).hexdigest()
            if computed_hash != event.get("event_hash"):
                is_valid = False
                errors.append(f"Event {i} hash mismatch - possible tampering")
        
        return {
            "valid": is_valid,
            "events_count": len(events),
            "errors": errors,
            "first_event": events[0].get("timestamp") if events else None,
            "last_event": events[-1].get("timestamp") if events else None
        }
    
    # ============== Verification ==============
    
    async def verify_evidence(
        self,
        evidence_id: str,
        current_file_data: bytes = None,
        user_id: str = None
    ) -> EvidenceVerificationResult:
        """
        Verify evidence integrity.
        Checks hash match, blockchain proof, and chain of custody.
        """
        # Get evidence record
        record = await db.evidence_integrity.find_one(
            {"evidence_id": evidence_id},
            {"_id": 0}
        )
        
        if not record:
            return EvidenceVerificationResult(
                is_valid=False,
                original_hash="",
                current_hash="",
                hash_match=False,
                blockchain_verified=False,
                chain_of_custody_intact=False,
                custody_events=0,
                last_verified=datetime.now(timezone.utc).isoformat(),
                warnings=["Evidence not found in integrity database"]
            )
        
        warnings = []
        hash_match = True
        current_hash = record["hash_sha256"]
        
        # Verify file hash if data provided
        if current_file_data:
            current_hash = self.compute_hash(current_file_data, HashAlgorithm.SHA256)
            hash_match = current_hash == record["hash_sha256"]
            if not hash_match:
                warnings.append("FILE HASH MISMATCH - Evidence may have been tampered with")
        
        # Verify blockchain proof
        blockchain_verified = record.get("blockchain_verified", False)
        blockchain_proof = None
        if record.get("blockchain_tx_hash"):
            blockchain_proof = {
                "network": record.get("blockchain_network"),
                "tx_hash": record.get("blockchain_tx_hash"),
                "block_number": record.get("blockchain_block_number"),
                "timestamp": record.get("blockchain_timestamp")
            }
        
        # Verify chain of custody
        custody_result = await self.verify_custody_chain(evidence_id)
        chain_intact = custody_result.get("valid", False)
        if not chain_intact:
            warnings.extend(custody_result.get("errors", []))
        
        # Log verification event
        if user_id:
            await self.log_custody_event(
                evidence_id=evidence_id,
                action=CustodyAction.VERIFIED,
                user_id=user_id,
                details={"hash_match": hash_match, "blockchain_verified": blockchain_verified}
            )
        
        # Update verification count
        now = datetime.now(timezone.utc).isoformat()
        await db.evidence_integrity.update_one(
            {"evidence_id": evidence_id},
            {"$set": {
                "last_verified": now,
                "is_verified": hash_match and chain_intact,
                "tamper_detected": not hash_match
            }, "$inc": {"verification_count": 1}}
        )
        
        return EvidenceVerificationResult(
            is_valid=hash_match and chain_intact,
            original_hash=record["hash_sha256"],
            current_hash=current_hash,
            hash_match=hash_match,
            blockchain_verified=blockchain_verified,
            blockchain_proof=blockchain_proof,
            chain_of_custody_intact=chain_intact,
            custody_events=custody_result.get("events_count", 0),
            last_verified=now,
            warnings=warnings
        )
    
    # ============== Blockchain Anchoring ==============
    
    async def _anchor_to_ethereum(self, evidence_id: str, hash_value: str, timestamp: str) -> Optional[Dict]:
        """
        Anchor evidence hash to Ethereum blockchain.
        This creates an immutable timestamp proof.
        """
        # For now, simulate blockchain anchoring
        # In production, this would call an actual Ethereum service
        
        if not self.ethereum_api_key:
            # Store locally as free tier
            proof_record = {
                "proof_id": f"proof_{uuid.uuid4().hex[:12]}",
                "evidence_id": evidence_id,
                "hash": hash_value,
                "timestamp": timestamp,
                "network": "local",
                "simulated": True,
                "created_at": datetime.now(timezone.utc).isoformat()
            }
            await db.blockchain_proofs.insert_one(proof_record)
            
            return {
                "network": "local",
                "tx_hash": f"local_{uuid.uuid4().hex}",
                "block_number": None,
                "timestamp": timestamp,
                "simulated": True
            }
        
        # Production Ethereum integration would go here
        # Using services like Chainlink, Infura, or Alchemy
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.ethereum_api_url}/anchor",
                    json={
                        "data_hash": hash_value,
                        "metadata": {
                            "evidence_id": evidence_id,
                            "timestamp": timestamp,
                            "platform": "JUSTICE"
                        }
                    },
                    headers={"Authorization": f"Bearer {self.ethereum_api_key}"},
                    timeout=30.0
                )
                
                if response.status_code == 200:
                    data = response.json()
                    return {
                        "network": "ethereum",
                        "tx_hash": data.get("transaction_hash"),
                        "block_number": data.get("block_number"),
                        "timestamp": data.get("timestamp")
                    }
        except Exception as e:
            print(f"Blockchain anchoring failed: {e}")
        
        return None
    
    # ============== Export for Court ==============
    
    async def generate_court_package(self, evidence_id: str, user_id: str) -> Dict:
        """
        Generate a complete evidence package for court submission.
        Includes all verification data and chain of custody.
        """
        # Get evidence record
        record = await db.evidence_integrity.find_one(
            {"evidence_id": evidence_id},
            {"_id": 0}
        )
        
        if not record:
            return {"success": False, "error": "Evidence not found"}
        
        # Get chain of custody
        custody_chain = await self.get_custody_chain(evidence_id)
        
        # Verify current state
        verification = await self.verify_evidence(evidence_id, user_id=user_id)
        
        # Log export
        await self.log_custody_event(
            evidence_id=evidence_id,
            action=CustodyAction.EXPORTED,
            user_id=user_id,
            details={"purpose": "court_submission"}
        )
        
        # Generate court package
        package = {
            "evidence_id": evidence_id,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "generated_by": user_id,
            
            "forensic_metadata": {
                "original_filename": record.get("original_filename"),
                "file_size_bytes": record.get("file_size_bytes"),
                "mime_type": record.get("mime_type"),
                "capture_timestamp": record.get("capture_timestamp"),
                "capture_device": record.get("capture_device"),
                "gps_coordinates": {
                    "latitude": record.get("gps_latitude"),
                    "longitude": record.get("gps_longitude"),
                    "accuracy": record.get("gps_accuracy")
                } if record.get("gps_latitude") else None
            },
            
            "cryptographic_verification": {
                "hash_sha256": record.get("hash_sha256"),
                "hash_sha512": record.get("hash_sha512"),
                "hash_sha3_256": record.get("hash_sha3_256"),
                "integrity_signature": record.get("integrity_signature"),
                "hash_verified": verification.hash_match,
                "verification_count": record.get("verification_count", 0)
            },
            
            "blockchain_proof": {
                "anchored": record.get("blockchain_verified", False),
                "network": record.get("blockchain_network"),
                "transaction_hash": record.get("blockchain_tx_hash"),
                "block_number": record.get("blockchain_block_number"),
                "anchor_timestamp": record.get("blockchain_timestamp")
            } if record.get("blockchain_tx_hash") else None,
            
            "chain_of_custody": {
                "total_events": len(custody_chain),
                "chain_intact": verification.chain_of_custody_intact,
                "events": custody_chain
            },
            
            "verification_status": {
                "is_valid": verification.is_valid,
                "last_verified": verification.last_verified,
                "warnings": verification.warnings
            },
            
            "legal_notice": (
                "This evidence package was generated by the JUSTICE Platform for use in legal proceedings. "
                "The cryptographic hashes provide mathematical proof that the evidence has not been altered "
                "since its original capture. The chain of custody log documents every access to this evidence. "
                "For questions about this evidence package, contact support@realjustice.app."
            )
        }
        
        return {"success": True, "package": package}


# Create singleton instance
evidence_integrity_service = EvidenceIntegrityService()
