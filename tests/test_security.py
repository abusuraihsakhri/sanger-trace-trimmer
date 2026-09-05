"""
Tests for security, PHI guard, and audit trail.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from agents.base import (
    PHIGuard,
    AuditTrail,
    AuditLogger,
    SecurityException,
    assert_no_phi,
)


class TestPHIGuard:
    def test_mrn_blocked(self):
        with pytest.raises(SecurityException):
            PHIGuard.assert_no_phi("Patient MRN-994827 blood culture")

    def test_ssn_blocked(self):
        with pytest.raises(SecurityException):
            PHIGuard.assert_no_phi("SSN: 123-45-6789")

    def test_phone_blocked(self):
        with pytest.raises(SecurityException):
            PHIGuard.assert_no_phi("Call 555-123-4567")

    def test_email_blocked(self):
        with pytest.raises(SecurityException):
            PHIGuard.assert_no_phi("Email: patient@example.com")

    def test_clean_text_passes(self):
        PHIGuard.assert_no_phi("Analytical assay specimen KEY-001 optimal")

    def test_empty_text_passes(self):
        PHIGuard.assert_no_phi("")

    def test_none_text_passes(self):
        PHIGuard.assert_no_phi(None)

    def test_redact_phi(self):
        result = PHIGuard.redact_phi("Contact patient@example.com for MRN-12345")
        assert "[REDACTED_IDENTIFIER]" in result
        assert "patient@example.com" not in result
        assert "MRN-12345" not in result


class TestAuditTrail:
    def test_log_creates_entry(self):
        trail = AuditTrail(secret_key="test-key")
        entry = trail.log("actor1", "tier1", "TEST_EVENT", {"key": "value"})
        assert "audit_id" in entry
        assert "current_hash" in entry
        assert entry["prev_hash"] == "GENESIS_BLOCK_0000000000000000"

    def test_chain_integrity(self):
        trail = AuditTrail(secret_key="test-key")
        trail.log("a", "t", "E1", {"x": 1})
        trail.log("b", "t", "E2", {"y": 2})
        trail.log("c", "t", "E3", {"z": 3})
        assert trail.verify_integrity() is True

    def test_tamper_detection(self):
        trail = AuditTrail(secret_key="test-key")
        trail.log("a", "t", "E1", {"x": 1})
        trail.log("b", "t", "E2", {"y": 2})
        # Tamper with the chain
        trail.logs[0]["current_hash"] = "TAMPERED"
        assert trail.verify_integrity() is False

    def test_phi_in_audit_blocked(self):
        trail = AuditTrail(secret_key="test-key")
        with pytest.raises(SecurityException):
            trail.log("actor", "tier", "EVENT", {"data": "MRN-12345"})

    def test_random_key_generation(self):
        """When no key is provided, a random one should be generated."""
        trail = AuditTrail()
        assert len(trail.secret_key) > 0

    def test_get_trail(self):
        trail = AuditTrail(secret_key="test-key")
        trail.log("a", "t", "E1", {"x": 1})
        assert len(trail.get_trail()) == 1
